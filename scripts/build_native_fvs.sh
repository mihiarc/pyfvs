#!/usr/bin/env bash
#
# Build native FVS shared libraries for pyfvs parity testing.
#
# Compiles each requested FVS variant from the USDA Fortran source into a
# loadable shared library (FVS<variant>.so) and installs it to ~/.fvs/lib,
# where pyfvs.native and the parity suite discover it.
#
# Usage:
#   scripts/build_native_fvs.sh                 # build all pyfvs variants
#   scripts/build_native_fvs.sh sn ls ne        # build a subset (lowercase codes)
#
# Environment:
#   FVS_SRC   FVS source checkout   (default: ~/Projects/ForestVegetationSimulator)
#   FVS_LIB_PATH / LIBDIR  install dir (default: ~/.fvs/lib)
#   JOBS      max concurrent variant builds (default: 4)
#
# Requires: gfortran, gcc, make. The volume/NVEL git submodule is initialized
# automatically if absent (the build fails without it).
set -uo pipefail

FVS_SRC="${FVS_SRC:-$HOME/Projects/ForestVegetationSimulator}"
LIBDIR="${LIBDIR:-${FVS_LIB_PATH:-$HOME/.fvs/lib}}"
JOBS="${JOBS:-4}"
LOGDIR="${LOGDIR:-$FVS_SRC/bin/_build_logs}"

# pyfvs-implemented variants (10 + EC). FVS ships 20 geographic variants total.
PYFVS_VARIANTS="sn ls cs ne pn wc ec ca ws op oc"

# --- child mode: build a single variant (re-invoked by xargs below) ----------
if [ "${1:-}" = "--build-one" ]; then
	v="$2"
	lib="FVS${v}.so"
	mkdir -p "$LIBDIR"
	( cd "$FVS_SRC/bin" && rm -rf "FVS${v}_buildDir" && make "$lib" ) \
		> "$LOGDIR/build_${v}.log" 2>&1
	if [ -f "$FVS_SRC/bin/$lib" ]; then
		cp "$FVS_SRC/bin/$lib" "$LIBDIR/$lib"
		codesign -s - "$LIBDIR/$lib" >/dev/null 2>&1 || true   # macOS ad-hoc sign
		echo "OK    $v  ->  $LIBDIR/$lib"
	else
		echo "FAIL  $v  (see $LOGDIR/build_${v}.log)"
	fi
	exit 0
fi

# --- main dispatch -----------------------------------------------------------
if [ "$#" -gt 0 ]; then VARIANTS="$*"; else VARIANTS="$PYFVS_VARIANTS"; fi

# Ensure the NVEL volume library submodule is present.
if [ ! -f "$FVS_SRC/volume/NVEL/beqinfo.inc" ]; then
	echo "Initializing volume/NVEL submodule..."
	git -C "$FVS_SRC" submodule update --init --recursive
fi

mkdir -p "$LOGDIR" "$LIBDIR"
export FVS_SRC LIBDIR LOGDIR

echo "Building variants: $VARIANTS  (JOBS=$JOBS, install -> $LIBDIR)"
printf '%s\n' $VARIANTS | xargs -P "$JOBS" -n1 "$0" --build-one
echo "Done. Installed libraries:"
ls -1 "$LIBDIR"/FVS*.so 2>/dev/null || echo "  (none)"
