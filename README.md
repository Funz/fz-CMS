# fz-CMS

FZ plugin for the Studsvik CMS code chain: **CASMO5** (lattice physics), **CMSLINK5** (cross-section library)
and **SIMULATE5** (nodal core simulator).

This plugin enables parametric studies with the CMS codes using the [fz framework](https://github.com/Funz/fz).
It supersedes `fz-Casmo` (CASMO5 only).

## Features

* **Three models**: `CASMO5`, `CMSLINK5`, `SIMULATE5`, one calculator `localhost_CMS`
* **Variable syntax**: `$(variable_name)` or `$(variable_name~default_value)`
* **Formula syntax**: `@(expression)` (Python), with context lines for imports and functions
* **Comment / context lines**: `*` for CASMO5 (`*@ import math`), `'COM'` for SIMULATE5 and CMSLINK5 (`'COM'@ ...`)
* **Output parsing**: k-inf and depletion table of CASMO5, keff / critical boron / peaking / axial offset of
  every SIMULATE5 Output Summary, segments of a CMSLINK5 library
* **Error handling**: the CMS wrappers always return 0; the calculator reads the termination banner and fails the
  case with the first fatal message (also extracted as the `fatal_message` output)

## Installation

### Prerequisites

1. **CMS installation**: a licensed Studsvik CMS installation (`$CMSHOME/bin/cas5`, `cmslink5`, `sim5`)
2. **Python 3.8+** and the **fz framework**: `pip install git+https://github.com/Funz/fz.git`

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/Funz/fz-CMS.git
   cd fz-CMS
   ```

2. Set the CMS environment:
   ```bash
   export CMSHOME=/path/to/CMSCODES             # contains bin/cas5, bin/cmslink5, bin/sim5
   export LM_LICENSE_FILE=port@license_server   # FlexNet license of the CMS codes
   export CMS_DATA_PATH=/path/to/libs:/path/to/caxs   # optional, see "Data files" below
   ```

3. The plugin is ready to use! The `.fz` directory contains:
   - `.fz/models/CASMO5.json`, `SIMULATE5.json`, `CMSLINK5.json` - model definitions
   - `.fz/calculators/CMS.sh` - calculation script (run, data files, termination check), called by
     `CASMO5.sh`, `SIMULATE5.sh`, `CMSLINK5.sh`
   - `.fz/calculators/localhost_CMS.json` - calculator configuration

## Usage

### Example: CASMO5 pin cell, enrichment and moderation ratio

**Input file (`examples/CASMO5/pincell.inp`):**
```
* CASMO5 UO2 pin cell, parametrized for fz: variables with defaults, a formula, context lines (*@)
*@ import math
*@ def cell_radius(pitch): return round(pitch / math.sqrt(math.pi), 5)
TTL * Pin cell $(enrichment~4.45) w/o, square pitch $(pitch~1.26) cm
TFU=$(tfu~900) TMO=$(tmo~575) BOR=$(boron~800)
FUE 1 10.45/$(enrichment~4.45)
* last radius = radius of the cylindrical cell of same area as the square cell (not the pitch)
PIC .4096 .4178 .4750 @(cell_radius($(pitch~1.26)))/'1' 'HEL' 'CAN' 'COO'
STA
END
```

**Python:**
```python
import fz

results = fz.fzr(
    input_path="examples/CASMO5/pincell.inp",
    input_variables={"enrichment": [3.0, 4.45], "pitch": [1.26, 1.30]},
    model="CASMO5",
    calculators="localhost_CMS",
    results_dir="results_pincell"
)
print(results[["enrichment", "pitch", "status", "kinf", "m2"]])
```

**Output (CASMO5 3.10):**
```
   enrichment  pitch status       kinf       m2
0        3.00   1.26   done    [1.219]  [58.46]
1        3.00   1.30   done   [1.2258]  [57.93]
2        4.45   1.26   done  [1.30945]   [57.1]
3        4.45   1.30   done  [1.32091]  [56.62]
```
CASMO5 outputs are lists with one value per state point (here a single one): `kinf[0]`.

### Example: SIMULATE5 critical boron vs power and inlet temperature

`examples/SIMULATE5/quarter_core.inp` (2D quarter core, library of the SIMULATE5 installation) converts an inlet
temperature given in °C to the °F expected by `'COR.TIN'`:
```
'COM'@ def degF(celsius): return round(celsius * 9 / 5 + 32, 2)
...
'COR.OPE' $(power~100) 100. 2250. /
'COR.TIN' @(degF($(tin_c~291.7))) /
'ITE.BOR' 1500 /
```
```python
results = fz.fzr("examples/SIMULATE5/quarter_core.inp", {"power": [0, 100], "tin_c": [286, 291.7]},
                 "SIMULATE5", calculators="localhost_CMS", results_dir="results_s5")
print(results[["power", "tin_c", "status", "keff", "boron", "fdh", "tfu_avg"]])
```
```
   power  tin_c status       keff      boron      fdh   tfu_avg
0      0  286.0   done  [0.99997]   [2135.7]   [1.65]  [559.15]
1      0  291.7   done  [0.99997]  [2143.15]  [1.637]  [564.85]
2    100  286.0   done      [1.0]  [2054.46]  [1.555]  [860.38]
3    100  291.7   done      [1.0]  [2058.85]  [1.543]  [865.74]
```

### Other examples
- `examples/CASMO5/assembly_dep.inp`: PWR 17x17 assembly depletion (`enrichment`, `boron`, `max_burnup`, `tfu`,
  `tmo`): `burnup`, `kinf`, `pin_peak`, `u235_wt`... are the depletion curves.
- `examples/CMSLINK5/library.inp`: 4-group library from the `.cax` of the CMSLINK5 installation (`library`, `groups`).
- `examples/example_pincell.py`: complete script of the pin cell study.

### Input file syntax

| | CASMO5 | SIMULATE5 / CMSLINK5 |
|---|---|---|
| Variable | `$(enr)`, `$(enr~4.0)` | same |
| Formula | `@(2*$(enr))` | same |
| Context line (Python, kept in the input as a comment) | `*@ import math` | `'COM'@ import math` |

- A line starting with `*` is a comment for CASMO5 only: SIMULATE5 and CMSLINK5 read it as a card
  (`DIM.PWR card appears after other input cards`, `Missing slash "/"`); use `'COM'` there.
- A formula may contain **one** level of parentheses: `@(cell_radius($(pitch)))` works,
  `@(round(cell_radius($(pitch)), 5))` is left unevaluated (CASMO5 then stops on `Illegal input line`):
  move the inner call into a context function.
- Do not write `$(...)` or `@(...)` in plain comments: they are substituted too.
- Do not name an input variable like an output (`burnup`, `kinf`, `boron`...): both are columns of the results.
- Units are those of the codes: CASMO5 temperatures in K, boron in ppm; SIMULATE5 `'COR.TIN'` in °F, pressure
  in psia (use a formula to convert).

## Outputs

All outputs of a code are read from its own files (`<input>.log` for CASMO5, `<input>.out` for CMSLINK5 and
SIMULATE5), so `fz.fzo()` works on any result directory. Lists have one value per state point / Output Summary.

### CASMO5 (`<input>.log`, summary table)
| Output | Description |
|---|---|
| `normal_termination` | 1 if `Normal Termination`, else 0 |
| `fatal_message` | first `[Fatal Error]` (routine and text), None if none |
| `warnings` | number of warnings |
| `burnup` | burnup of each state point (MWd/kg) |
| `kinf` | k-infinity of each state point (depletion, then each `COE` branch block) |
| `kinf_2g` | k-infinity from the 2-group constants |
| `m2` | migration area (cm²) |
| `pin_peak` | maximum pin power / average |
| `u235_wt`, `fiss_pu_wt`, `tot_pu_wt` | U-235, fissile Pu, total Pu (wt%) |

A `S5C` (case matrix) run prints no summary table: its lists are empty, its result is the `.cax` file (in the
result directory) for CMSLINK5.

### SIMULATE5 (`<input>.out`, every Output Summary)
| Output | Description |
|---|---|
| `normal_termination`, `fatal_message` | `Normal Termination`; first line `LABEL count FATAL CARD text` of the message table |
| `keff` | K-effective (1.00000 within convergence with `'ITE.BOR'`) |
| `boron` | boron concentration (ppm): the critical boron with `'ITE.BOR'`, the input with `'COR.BOR'` |
| `exposure`, `cycle_efpd` | core average exposure EBAR (GWd/MT), cycle exposure (EFPD) |
| `power_pct` | relative power (%) |
| `peak_nodal_power`, `fdh`, `max_fxy` | peak nodal power, F-delta-H, Max-Fxy |
| `axial_offset`, `leakage`, `tfu_avg` | axial offset, total neutron leakage, average fuel temperature (K) |

### CMSLINK5 (`<input>.out`)
| Output | Description |
|---|---|
| `normal_termination`, `fatal_message` | `NORMAL TERMINATION` without `RUN ABORTED`; first FATAL message |
| `library` | library written (`NEW LIBRARY "..." WAS WRITTEN`) |
| `segments` | SIMULATE5 segments processed |

## Calculator

`.fz/calculators/CMS.sh <cas5|cmslink5|sim5> <input file or directory>`:
- runs the wrapper of `$CMSHOME/bin` with `CMS_PROMPT=no CMS_PROTECT=no CMS_KILL=yes` (the wrappers otherwise ask
  before overwriting and write-protect their outputs); copies the input to `<name>.inp` if needed (required by
  the wrappers);
- **data files**: every quoted `*.lib`, `*.cax`, `*.res` named in the input (except the library created on a
  CMSLINK5 `'NEW'` card) and absent from the case directory is symlinked from `CMS_DATA_PATH` (or decompressed
  from `<file>.gz`). Default: the `install_inputs` directories of SIMULATE5 and CMSLINK5 under `$CMSHOME`, which
  hold `clnk.pwr.4grp.lib` and the `.cax.gz` used by the examples. Data files can also be passed with the input:
  `fz.fzr("my_case_dir/", ...)` copies the whole directory into each case;
- **errors**: exit code 1 when the termination banner is missing, with the first fatal messages on stderr: the
  case gets `status = failed` and fz's `error` column holds the message, e.g.
  `[Fatal Error] in INPUT1 Incorrect moderator temperature.`

Models set no timeout except CASMO5 (6 h, for `S5C` case matrices); override with `fz.fzr(..., timeout=...)`.

### Chaining CASMO5 → CMSLINK5 → SIMULATE5
Each code is a separate fz model: run the CASMO5 study, then point the CMSLINK5 input to the `.cax` files of
its result directories (`CMS_DATA_PATH` or copies), then the SIMULATE5 input to the new library. Results of
previous runs can be reused with `calculators=["cache://results_dir", "localhost_CMS"]`.

## Advanced usage

### Remote calculators
```python
results = fz.fzr("examples/CASMO5/pincell.inp", {"enrichment": [3.0, 4.0]}, "CASMO5",
                 calculators="ssh://user@cluster/bash /path/to/fz-CMS/.fz/calculators/CASMO5.sh",
                 results_dir="remote_results")
```
`CMSHOME` and `LM_LICENSE_FILE` must be set in the remote login environment.

### Parallel execution
```python
results = fz.fzr("examples/CASMO5/pincell.inp", {"enrichment": [3.0, 3.5, 4.0, 4.5, 5.0]}, "CASMO5",
                 calculators=["localhost_CMS"] * 4, results_dir="parallel_results")
```
Each run takes one license token.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `CMSHOME environment variable is not set` / `cas5 not found` | set `CMSHOME` to the directory holding `bin/cas5` |
| `failed`, `No fatal message found: check license` | license server unreachable (`LM_LICENSE_FILE`), see `out.txt` of the case |
| SIMULATE5 `Requested cross section library not found` | library not in the case directory nor in `CMS_DATA_PATH` |
| CMSLINK5 `NEW LIBRARY ALREADY EXISTS` | the input directory already holds the library named on `'NEW'` |
| `Illegal input line: ... @(...)` | formula not evaluated (nested parentheses), see "Input file syntax" |
| Normal termination but wrong values | silent input errors (unquoted strings on `PIN`, units of `'COR.TIN'`...): check the physics |

## Tests
```bash
python tests/test_plugin.py   # structure, fzi/fzc, output parsing on tests/fixtures (trimmed real outputs);
                              # also runs the examples when CMSHOME holds a CMS installation
```

## License

BSD 3-Clause, as the fz framework. CASMO5, CMSLINK5 and SIMULATE5 are products of Studsvik Scandpower; this
repository holds no part of them and no data library.

## Related Links

- [fz framework](https://github.com/Funz/fz) - Main parametric computing framework
- [fz-Casmo](https://github.com/Funz/fz-Casmo) - previous CASMO5-only plugin
