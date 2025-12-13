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
    from math import atan, pi, sin, cos
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
    r = 3.5
    delta = atan(3*common_mg_pars['width']/r)
    # Or use `for box in range(4, 8):` to match initial scope
    for box in range(10):
        theta = (1 + 2 * (7 - box)) * delta
        ref = ts.component(
            f'box{box}_ref', 'Arm',
            at=[(r*sin(theta), 0, r*cos(theta)), origin],
            rotate=[(0, theta/pi*180, 0), origin]
        )
        for column in range(6):
            pars = {f'projection_{k}_filename': f'"g{box}{column}{k}"'
                    for k in ('xy', 'yz', 'zx')}
            pars.update(common_mg_pars)
            local_x = (column-2.5)*common_mg_pars['width']
            local_y = common_mg_pars['depth']/2
            col = ts.component(
                f'mg_box{box}_col{column}', 'Detector_cubes',
                parameters=pars, at=([local_x, 0, local_y], ref)
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
    """))

    ts.instrument.determine_groups()
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

    # assert 'wire' in files
    # assert 'pack' in files
    # assert 'division' in files
    # # verify that the output files are as expected ...
    #
    # pack = files['pack'].structured['I']
    # assert sum(pack[:]) == 1000, "Every produced ray should be detected"
    # assert std(pack[:]) == 0, "All 2-D pixels should be hit the same number of times"
    #
    # wire = files['wire'].structured['I']
    # assert sum(wire) == 1000, "The wire output indexes the same pixelated space"
    # assert std(wire) == 0
    #
    # # Now the real test for charge division correctness. The ratios of (1m)*rho and R have been chosen as 2:1.
    # # This means that each tube should be twice as long as a gap in charge-division; so the whole
    # # space needs to be divisible by 14 = 2*5 + 4 to have an integer number of bins per section.
    # division = files['division'].structured['I']
    # gaps = division[[2, 5, 8, 11]]
    # assert sum(gaps) < 5, "Raster/randomness might put one event per gap"
    # assert abs(sum(division)-sum(wire)) < 10, "All events should show up in the division signal, but one might be missing"
    #
    #

