# McStas Contiguous Subdivided Volume Detector

A McStas component that implements a contiguous 3D array of detector volumes (cubes), useful for simulating multi-grid detectors or any pixelated volumetric detector system.

## Overview

`Detector_cubes` creates a rectangular detector volume subdivided into Nx × Ny × Nz individual detection cubes. When a neutron enters the volume, it is randomly absorbed at some point along its path through the detector, and the corresponding cube indices are recorded.

## Installation

1. Clone this repository into your McStas working directory or a location accessible to your instrument.

2. For programmatic instrument generation, install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Component Parameters

| Parameter                | Type   | Default | Description                                         |
|--------------------------|--------|---------|-----------------------------------------------------|
| `width`                  | double | 0       | Detector dimension in x (perpendicular to beam) [m] |
| `height`                 | double | 0       | Detector dimension in y (perpendicular to beam) [m] |
| `depth`                  | double | 0       | Detector dimension in z (along beam direction) [m]  |
| `Nx`                     | int    | 1       | Number of cubes along x dimension                   |
| `Ny`                     | int    | 1       | Number of cubes along y dimension                   |
| `Nz`                     | int    | 1       | Number of cubes along z dimension                   |
| `index_x`                | string | -       | Name of USERVAR to store x cube index               |
| `index_y`                | string | -       | Name of USERVAR to store y cube index               |
| `index_z`                | string | -       | Name of USERVAR to store z cube index               |
| `detection_time`         | string | -       | Name of USERVAR to store detection time             |
| `filename`               | string | 0       | Output filename (3D output not yet supported)       |
| `projection_xy_filename` | string | 0       | Filename for XY projection histogram                |
| `projection_yz_filename` | string | 0       | Filename for YZ projection histogram                |
| `projection_zx_filename` | string | 0       | Filename for ZX projection histogram                |
| `restore_neutron`        | int    | 0       | If set, detector does not absorb neutrons           |

## Basic Usage

### Minimal Example

```c
COMPONENT detector = Detector_cubes(
  width=0.2,       // 20 cm wide
  height=2.2,      // 2.2 m tall  
  depth=0.5,       // 50 cm deep
  Nx=6,            // 6 cubes in x
  Ny=88,           // 88 cubes in y
  Nz=20,           // 20 cubes in z
  index_x="ROW",
  index_y="GRID", 
  index_z="LAYER",
  detection_time="event_time",
  projection_xy_filename="detector_xy"
)
AT (0, 0, 3) RELATIVE Origin
```

### Required USERVARS

To use the index output features, you must declare corresponding user variables in your instrument:

```c
USERVARS %{
  int ROW;         // x cube index
  int GRID;        // y cube index
  int LAYER;       // z cube index
  double event_time;
%}
```

## Example: Multi-Grid Detector Array

The following example shows how to create an array of detector modules (as used in the T-REX secondary spectrometer simulation):

### Python/mccode-antlr Approach

For complex detector geometries, you can use the `mccode-antlr` Python package to programmatically generate instruments:

```python
from mccode_antlr import Flavor
from mccode_antlr.assembler import Assembler
from mccode_antlr.reader.registry import LocalRegistry
from math import atan, pi, sin, cos

# Create instrument assembler
ts = Assembler('detector_array', flavor=Flavor.MCSTAS, registries=[LocalRegistry('local', '.')])
ts.parameter('int dummy/"s"=0')

# Declare user variables for cube indices
ts.user_vars("""
    int ROW;
    int GRID;
    int LAYER;
    double event_time;
    int COLUMN;
    int BOX;
""")

# Common detector parameters
common_mg_pars = {
    'index_x': '"ROW"',
    'index_y': '"GRID"',
    'index_z': '"LAYER"',
    'detection_time': '"event_time"',
    'width': 0.2,     # m
    'height': 2.2,    # m
    'depth': 0.5,     # m
    'Nx': 6,          # rows per module
    'Ny': 88,         # grids per module
    'Nz': 20,         # layers per module
}

# Create source
origin = ts.component("origin", "Progress_bar")
source = ts.component("source", "Source_simple", parameters={
    "yheight": 0.1, "xwidth": 1., "dist": 2,
    'focus_xw': 6 * common_mg_pars['width'] * 4,
    'focus_yh': common_mg_pars['height'],
    'lambda0': 1.5, 'dlambda': 0.1
}, at=[(0, 0, 0), origin])

# Create detector array in an arc
r = 3.5  # radius
delta = atan(3 * common_mg_pars['width'] / r)

for box in range(10):
    theta = (1 + 2 * (7 - box)) * delta
    ref = ts.component(
        f'box{box}_ref', 'Arm',
        at=[(r * sin(theta), 0, r * cos(theta)), origin],
        rotate=[(0, theta / pi * 180, 0), origin]
    )
    for column in range(6):
        pars = {f'projection_{k}_filename': f'"g{box}{column}{k}"'
                for k in ('xy', 'yz', 'zx')}
        pars.update(common_mg_pars)
        local_x = (column - 2.5) * common_mg_pars['width']
        local_y = common_mg_pars['depth'] / 2
        col = ts.component(
            f'mg_box{box}_col{column}', 'Detector_cubes',
            parameters=pars, at=([local_x, 0, local_y], ref)
        )
        col.GROUP('MultiGrid')
        col.EXTEND(f"""
            if (SCATTERED) {{
              BOX={box};
              COLUMN={column};
            }}
        """)

# Finalize and write instrument
ts.instrument.determine_groups()
with open('detector_array.instr', 'w') as f:
    ts.instrument.to_file(f)
```

## Using GROUP for Multiple Detectors

When placing multiple `Detector_cubes` components, use the `GROUP` keyword to ensure a neutron is only detected once:

```c
COMPONENT detector1 = Detector_cubes(...)
AT (0, 0, 3) RELATIVE Origin
GROUP MultiGrid

COMPONENT detector2 = Detector_cubes(...)
AT (0.2, 0, 3) RELATIVE Origin
GROUP MultiGrid
```

Neutrons that scatter (are detected) in one component of the group will skip the remaining components in that group.

## Output

The component produces 2D projection histograms when the corresponding filename parameters are set:
- `projection_xy_filename`: X-Y projection (integrates over Z)
- `projection_yz_filename`: Y-Z projection (integrates over X)
- `projection_zx_filename`: Z-X projection (integrates over Y)

Note: Full 3D histogram output is not currently supported.

### Runtime information
The location at which a neutron ray is absorbed is set _inside the Detector_cubes_
component, producing a 3-D index to identify the subvolume.
With multiple grouped detectors, these identifiers can be combined with an
index or indices identifying the whole component to uniquely identify the voxel
within the detector array.

By using a component like the [`mcstas-readout-master`](https://github.com/mcdotstar/mcstas-readout-master)
these identifiers plus the weight and absorption time can be used to construct
one or more events for use in testing further parts of the ESS data acquisition pipeline.

## Running Tests

```bash
pytest test/
```

## License

See McStas license terms.

## Author

Gregory Tucker, ESS (2025)
