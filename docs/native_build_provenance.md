# Native FVS Build Provenance

The parity suite (`tests/parity/`, `-m parity`) compares pyfvs against the
native USDA FVS Fortran libraries built by `scripts/build_native_fvs.sh` and
installed to `~/.fvs/lib/`. Parity results are only meaningful relative to a
**pinned** native build — this file records exactly what was built, so the
2026-06-21 baseline and its annotation reconciliations are reproducible.

## Pinned build — 2026-06-21

| Component | Value |
|---|---|
| **ForestVegetationSimulator commit** | `58a9752025e10e5fde80883a6aa019bab1da767b` (`58a97520`) |
| FVS commit date / subject | 2026-04-06 — *Merge branch 'staging' … into open_main* |
| **NVEL submodule commit** (`volume/NVEL`) | `d6bbbf140d99310d6d99c3ac5b8d081b86959d18` (`d6bbbf1`) |
| NVEL commit date / subject | 2026-02-09 — *vollib release 20260209* |
| Build date | **2026-06-21** (libs timestamped 06:50–06:52) |
| Built variants | all 11: SN, LS, CS, NE, PN, WC, EC, CA, WS, OP, OC |
| Toolchain | macOS arm64 (Darwin 25.5.0), gfortran 15.2 (Homebrew) |
| Install path | `~/.fvs/lib/FVS{variant}.so` |

The FVS source tree was clean at this commit (only untracked build artifacts —
`bin/FVS*.so`, `bin/FVS*_buildDir/` — were present; no tracked-source edits), so
the libraries are a faithful compile of the pinned commit + pinned NVEL submodule.

## How to reproduce

```bash
git -C ~/Projects/ForestVegetationSimulator checkout 58a97520
git -C ~/Projects/ForestVegetationSimulator submodule update --init --recursive   # pins NVEL d6bbbf1
cd ~/Projects/pyfvs && scripts/build_native_fvs.sh        # builds all 11 → ~/.fvs/lib
uv run pytest tests/parity/ -m parity                     # 40 passed, 14 xfailed (2026-06-21 baseline)
```

## Verify the live build matches this record

```bash
git -C ~/Projects/ForestVegetationSimulator rev-parse HEAD              # -> 58a97520…
git -C ~/Projects/ForestVegetationSimulator -C volume/NVEL rev-parse HEAD  # -> d6bbbf1…
```

If either SHA differs, the parity tallies and the xfail/xpass annotations in
`docs/parity_scorecard_2026-06-21.md` must be re-reconciled — a different native
build is a different source of truth.
