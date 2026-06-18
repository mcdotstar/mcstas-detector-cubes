from mccode_antlr.loader.loader import parse_mcstas_instr
from mccode_antlr.utils import parse_instr_string, compile_and_run
from mccode_antlr.test import compiled_test
from textwrap import dedent


def this_registry():
    from git import Repo, InvalidGitRepositoryError
    from mccode_antlr.reader.registry import LocalRegistry
    try:
        repo = Repo('.', search_parent_directories=True) 
        root = repo.working_tree_dir
        return LocalRegistry('this_registry', root)
    except InvalidGitRepositoryError as ex:
        raise RuntimeError(f"Unable to identify base repository, {ex}")


def assemble_instr():
    from math import atan, pi, sin, cos, atan2
    from mccode_antlr import Flavor
    from mccode_antlr.assembler import Assembler
    from textwrap import dedent
    ts = Assembler('trex_secondary', flavor=Flavor.MCSTAS, registries=[this_registry()])
    ts.parameter('int dummy/"s"=0')
    ts.user_vars(dedent("""
    int ROW; // x
    int GRID; // y
    int LAYER; // z
    double event_time;
    int RING;
    int WIRE;
    int COLUMN;
    int BOX;    
    """))
    common_mg_pars = {
        'index_x': '"ROW"',
        'index_y': '"GRID"',
        'index_z': '"LAYER"',
        'detection_time': '"event_time"',
        'width': 0.2, # m
        'height': 2.2, # m
        'depth': 0.5, # m
        'Nx': 6, # rows per MG
        'Ny': 88, # grids per MG
        'Nz': 20, # layers per MG
    }
    origin=ts.component("origin", "Progress_bar")
    source=ts.component("source", "Source_simple", parameters={
        "yheight": 0.1, "xwidth": 1., "dist": 2,
        'focus_xw': 6*common_mg_pars['width']*4,
        'focus_yh': common_mg_pars['height'],
        'lambda0': 1.5, 'dlambda': 0.1
    }, at=[(0,0,0), origin], rotate=[(0,45,0), origin])
    r_inner = 3.
    r = 3.25
    delta = atan(3*common_mg_pars['width']/r_inner)
    eta = atan(common_mg_pars['width']/r_inner)
    delta = 3 * eta # contiguous in angle at inner radius

    # Or use `for box in range(4, 8):` to match initial scope
    # range(10) for the full detector

    # Day zero coverage goes from 1 degree to 72 degrees in four modules
    for box in range(4, 8):
        theta = (1 + 2 * (7 - box)) * delta
        ref = ts.component(
            f'box{box}_ref', 'Arm',
            at=[(r_inner*sin(theta), 0, r_inner*cos(theta)), origin],
            rotate=[(0, theta/pi*180, 0), origin]
        )
        for column in range(6):
            pars = {f'projection_{k}_filename': f'"g{box}{column}{k}"'
                    for k in ('xy', 'yz', 'zx')}
            pars.update(common_mg_pars)
            local_x = (column-2.5)*common_mg_pars['width']
            local_y = common_mg_pars['depth']/2
            phi = atan2(local_x, r)
            phi = (column - 2.5) * eta
            local_x = (r_inner + common_mg_pars['depth']/2) * sin(phi)
            local_y = (r_inner + common_mg_pars['depth']/2) * cos(phi)
            col = ts.component(
                f'mg_box{box}_col{column}', 'Detector_cubes',
                parameters=pars, at=([local_x, 0, local_y - r_inner], ref),
                rotate=[(0, phi/pi*180, 0), ref]
            )
            col.GROUP('MultiGrid')
            col.EXTEND(dedent(f"""
            if (SCATTERED) {{
              BOX={box};
              COLUMN={column};
            }}
            """))

    ts.component(
        'translator', 'Arm', at=([0, 0, 0], 'ABSOLUTE')
    ).EXTEND(dedent("""
    printf("Particle detected at box=%d column=%d, row=%d grid=%d layer=%d\\n", BOX, COLUMN, ROW, GRID, LAYER);
    // ICD v5 says origin per column is at front upper left corner:
    //   wire number increases from 0 to 19 front to back, then in steps of 20 from left to right, ultimately in [0, 119]
    //   grid number increases from top to bottom
    WIRE = 20 * ROW + LAYER; // ICD v5
    GRID = 88 - GRID;

    """))

    # The Readout components have not been made available in this test, and ReadoutVMM3 is not in the repository
    #ts.component('readout', 'ReadoutVMM3', at=([0, 0, 0], 'ABSOLUTE'))

    return ts.instrument

def test_detector_cubes_instr_file():
    tr = assemble_instr()
    with open(f'{tr.name}.instr', 'w') as file:
        tr.to_file(file)

@compiled_test
def test_detector_cubes():
    from numpy import sum, std, abs
    tr = assemble_instr()

    compile_and_run(tr, '-n 1 dummy=1', run=True)
