"""
High-level NativeStand API that mirrors the pyfvs Stand interface.

NativeStand provides a familiar API for running simulations through the
native FVS Fortran library, producing results in the same format as
pyfvs.Stand for direct comparison.

Usage:
    >>> from pyfvs.native import NativeStand
    >>> with NativeStand(variant='SN') as ns:
    ...     ns.initialize_planted(500, 70, 'LP')
    ...     ns.grow(50)
    ...     metrics = ns.get_metrics()
    ...     print(f"TPA: {metrics['tpa']:.0f}, BA: {metrics['basal_area']:.1f}")

Important limitations:
    - FVS uses Fortran COMMON blocks for global state. Only one NativeStand
      instance per variant can be active at a time within a process.
    - Requires the FVS shared library to be built and installed.
      See native/BUILD.md for instructions.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from pyfvs.exceptions import FVSNativeError
from pyfvs.native.fvs_bindings import FVSBindings
from pyfvs.native.species_map import get_species_index

logger = logging.getLogger(__name__)


class NativeStand:
    """High-level interface to the native FVS shared library.

    Mirrors the pyfvs Stand API for direct comparison of simulation results.
    Generates FVS keyword files and manages temporary working directories.

    Args:
        variant: FVS variant code (e.g., 'SN', 'PN', 'LS').
        work_dir: Optional working directory. If None, a temporary
            directory is created and cleaned up on close().
    """

    # FVS default cycle lengths per variant (from variant source code)
    # SN and OP use 5-year cycles; all others use 10-year cycles
    _VARIANT_CYCLE_LENGTHS = {
        "SN": 5, "LS": 10, "PN": 10, "WC": 10,
        "NE": 10, "CS": 10, "CA": 10, "OC": 10,
        "WS": 10, "OP": 5,
    }

    def __init__(self, variant: str = "SN", work_dir: Optional[str] = None):
        self.variant = variant.upper()
        self._bindings = FVSBindings(self.variant)
        self._initialized = False
        self._years_grown = 0
        self._cycle_length = self._VARIANT_CYCLE_LENGTHS.get(self.variant, 10)

        # Working directory for keyword files
        if work_dir:
            self._work_dir = Path(work_dir)
            self._work_dir.mkdir(parents=True, exist_ok=True)
            self._owns_work_dir = False
        else:
            self._work_dir = Path(tempfile.mkdtemp(prefix="fvs_native_"))
            self._owns_work_dir = True

        self._keyword_file: Optional[Path] = None
        self._species: Optional[str] = None
        self._site_index: Optional[float] = None
        self._trees_per_acre: Optional[float] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        """Clean up temporary working directory."""
        if self._owns_work_dir and self._work_dir.exists():
            shutil.rmtree(self._work_dir, ignore_errors=True)

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize_planted(
        self,
        trees_per_acre: float,
        site_index: float,
        species: str,
        age: int = 1,
        dbh: float = 0.1,
        height: float = 1.0,
        ecounit: str = "",
    ) -> None:
        """Initialize a planted stand, matching the pyfvs Stand API.

        Generates an FVS keyword file with STDIDENT, SITECODE, DESIGN,
        PLANT/TREEFMT, NUMCYCLE, and PROCESS keywords, then initializes
        the native FVS library.

        Args:
            trees_per_acre: Planting density (trees per acre).
            site_index: Site index (base age 25 or 50 depending on variant).
            species: Two-letter species code (e.g., 'LP', 'DF').
            age: Initial stand age in years.
            dbh: Initial DBH in inches.
            height: Initial height in feet.
            ecounit: Ecological unit code (if applicable).
        """
        self._species = species.upper()
        self._site_index = site_index
        self._trees_per_acre = trees_per_acre

        # Map species to FVS integer index
        species_index = get_species_index(self._species, self.variant)

        # Calculate number of cycles needed (will be set during grow())
        num_cycles = 10  # default, updated in grow()

        # Generate keyword file
        self._keyword_file = self._generate_keyword_file(
            species_index=species_index,
            trees_per_acre=trees_per_acre,
            site_index=site_index,
            age=age,
            dbh=dbh,
            height=height,
            num_cycles=num_cycles,
            ecounit=ecounit,
        )

        logger.info(
            "NativeStand initialized: %s variant, %s species, "
            "SI=%.0f, TPA=%.0f, keyword=%s",
            self.variant,
            self._species,
            site_index,
            trees_per_acre,
            self._keyword_file,
        )

        self._initialized = True

    def _generate_keyword_file(
        self,
        species_index: int,
        trees_per_acre: float,
        site_index: float,
        age: int,
        dbh: float,
        height: float,
        num_cycles: int,
        ecounit: str = "",
    ) -> Path:
        """Generate an FVS keyword file for the simulation.

        Uses ESTAB/PLANT keywords to establish planted trees on bare ground,
        avoiding complex TREEFMT/TREEIN formatting issues.

        Returns:
            Path to the generated .key file.
        """
        key_path = self._work_dir / "stand.key"

        # Build keyword file
        lines = []
        lines.append("STDIDENT")
        lines.append(f"PYFVS_NATIVE_{self.variant}_{self._species}")

        # Site index - field 1 is species index, field 2 is site index
        lines.append("SITECODE")
        lines.append(f"         {species_index:3d}  {site_index:6.1f}")

        # No initial tree data — bare ground planting
        lines.append("NOTREES")
        lines.append("NOTRIPLE")

        # Stand info
        lines.append("STDINFO")
        lines.append(f"         0  {age:4d}       0       0       0")

        # Inventory year
        lines.append("INVYEAR         2000")

        # Suppress automatic establishment
        lines.append("NOAUTOES")

        # Number of cycles (value in columns 11-20 of keyword record)
        lines.append(f"NUMCYCLE  {num_cycles:10d}")

        # Plant trees using ESTAB/PLANT keywords
        # PLANT: year, species_index, TPA
        tpa_int = int(round(trees_per_acre))
        lines.append("ESTAB           2000")
        lines.append(f"PLANT           2000{species_index:10d}{tpa_int:10d}")
        lines.append("END")

        # Process
        lines.append("PROCESS")
        lines.append("STOP")

        with open(key_path, "w") as key_file:
            key_file.write("\n".join(lines) + "\n")

        return key_path

    # =========================================================================
    # Simulation
    # =========================================================================

    def grow(self, years: int = 50) -> None:
        """Run the FVS simulation for the specified number of years.

        The simulation runs all cycles at once through the native FVS
        library, matching the keyword file configuration.

        Args:
            years: Number of years to simulate.

        Raises:
            FVSNativeError: If the simulation has not been initialized
                or if the native library returns an error.
        """
        if not self._initialized:
            raise FVSNativeError(
                "Stand not initialized. Call initialize_planted() first."
            )

        # Recalculate number of cycles and regenerate keyword file
        num_cycles = max(1, years // self._cycle_length)
        self._keyword_file = self._generate_keyword_file(
            species_index=get_species_index(self._species, self.variant),
            trees_per_acre=self._trees_per_acre,
            site_index=self._site_index,
            age=1,
            dbh=0.1,
            height=1.0,
            num_cycles=num_cycles,
        )

        # Initialize FVS with keyword file (FVS expects --keywordfile=<path> format)
        cmd_line = f"--keywordfile={self._keyword_file}"
        self._bindings.set_cmd_line(cmd_line)

        # Run simulation - FVS returns 2 when simulation is complete
        return_code = self._bindings.run()
        while return_code == 0:
            return_code = self._bindings.run()

        if return_code not in (0, 2):
            raise FVSNativeError(
                f"FVS simulation failed with return code {return_code}"
            )

        self._years_grown = years
        logger.info(
            "NativeStand simulation complete: %d years, %d cycles",
            years,
            num_cycles,
        )

    # =========================================================================
    # Output retrieval
    # =========================================================================

    def get_metrics(self) -> Dict[str, float]:
        """Get current stand metrics in the same format as Stand.get_metrics().

        Computes metrics directly from tree-level attributes via fvsTreeAttr,
        which provides reliable final-state data after simulation completes.

        Returns:
            Dictionary with keys: tpa, basal_area, qmd, top_height,
            sdi, volume, age.
        """
        import math

        dims = self._bindings.get_dim_sizes()
        ntrees = dims["ntrees"]

        if ntrees <= 0:
            return {
                "tpa": 0.0,
                "basal_area": 0.0,
                "qmd": 0.0,
                "top_height": 0.0,
                "sdi": 0.0,
                "volume": 0.0,
                "age": self._years_grown,
            }

        # Get tree-level arrays
        dbh = self._bindings.get_tree_attr("dbh", ntrees)
        ht = self._bindings.get_tree_attr("ht", ntrees)
        tpa_arr = self._bindings.get_tree_attr("tpa", ntrees)

        try:
            tcuft = self._bindings.get_tree_attr("tcuft", ntrees)
        except FVSNativeError:
            tcuft = None

        # Compute stand metrics from tree arrays
        import numpy as np

        total_tpa = float(np.sum(tpa_arr))
        basal_area = float(np.sum(0.005454 * dbh**2 * tpa_arr))

        if total_tpa > 0 and basal_area > 0:
            qmd = math.sqrt(basal_area / (0.005454 * total_tpa))
        else:
            qmd = 0.0

        top_height = float(np.max(ht)) if len(ht) > 0 else 0.0

        # Volume: sum of per-tree cubic foot volume * TPA
        if tcuft is not None:
            volume = float(np.sum(tcuft * tpa_arr))
        else:
            volume = 0.0

        # SDI = sum(TPA_i * (DBH_i / 10)^1.605) — Reineke's formula
        sdi = float(np.sum(tpa_arr * (dbh / 10.0) ** 1.605))

        return {
            "tpa": total_tpa,
            "basal_area": basal_area,
            "qmd": qmd,
            "top_height": top_height,
            "sdi": sdi,
            "volume": volume,
            "age": self._years_grown,
        }

    def get_tree_list(self) -> List[Dict[str, float]]:
        """Get individual tree data in the same format as Stand tree lists.

        Returns:
            List of dictionaries, one per tree, with keys: species, dbh,
            height, tpa, crown_ratio, tcuft.
        """
        dims = self._bindings.get_dim_sizes()
        ntrees = dims["ntrees"]

        if ntrees <= 0:
            return []

        dbh = self._bindings.get_tree_attr("dbh", ntrees)
        ht = self._bindings.get_tree_attr("ht", ntrees)
        tpa = self._bindings.get_tree_attr("tpa", ntrees)
        cratio = self._bindings.get_tree_attr("cratio", ntrees)

        try:
            tcuft = self._bindings.get_tree_attr("tcuft", ntrees)
        except FVSNativeError:
            tcuft = [0.0] * ntrees

        try:
            species = self._bindings.get_tree_attr("species", ntrees)
        except FVSNativeError:
            species = [0] * ntrees

        tree_list = []
        for i in range(ntrees):
            tree_list.append({
                "species_index": int(species[i]) if i < len(species) else 0,
                "dbh": float(dbh[i]),
                "height": float(ht[i]),
                "tpa": float(tpa[i]),
                "crown_ratio": float(cratio[i]),
                "tcuft": float(tcuft[i]) if i < len(tcuft) else 0.0,
            })

        return tree_list

    def get_keyword_file(self) -> Optional[str]:
        """Return the contents of the keyword file used for this simulation.

        Returns:
            Keyword file contents as a string, or None if not yet initialized.
        """
        if self._keyword_file and self._keyword_file.exists():
            return self._keyword_file.read_text()
        return None

    def get_keyword_file_path(self) -> Optional[Path]:
        """Return the path to the keyword file used for this simulation.

        Returns:
            Path to the .key file, or None if not yet initialized.
        """
        return self._keyword_file

    def export_keyword_file(self, dest: str) -> Path:
        """Copy the keyword file to a destination path.

        Args:
            dest: Destination file path or directory. If a directory,
                the file is copied as 'stand.key' inside it.

        Returns:
            Path to the exported file.

        Raises:
            FVSNativeError: If no keyword file exists.
        """
        if not self._keyword_file or not self._keyword_file.exists():
            raise FVSNativeError("No keyword file available. Initialize the stand first.")

        dest_path = Path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / "stand.key"
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(self._keyword_file, dest_path)
        return dest_path

    def get_output_file(self) -> Optional[str]:
        """Return the contents of the FVS .out file for this simulation.

        Returns:
            Output file contents as a string, or None if not available.
        """
        out_path = self._work_dir / "stand.out"
        if out_path.exists():
            return out_path.read_text()
        return None

    def get_output_file_path(self) -> Optional[Path]:
        """Return the path to the FVS .out file for this simulation.

        Returns:
            Path to the .out file, or None if not available.
        """
        out_path = self._work_dir / "stand.out"
        return out_path if out_path.exists() else None

    def export_output_file(self, dest: str) -> Path:
        """Copy the FVS .out file to a destination path.

        Args:
            dest: Destination file path or directory. If a directory,
                the file is copied as 'stand.out' inside it.

        Returns:
            Path to the exported file.

        Raises:
            FVSNativeError: If no output file exists.
        """
        out_path = self._work_dir / "stand.out"
        if not out_path.exists():
            raise FVSNativeError("No output file available. Run the simulation first.")

        dest_path = Path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / "stand.out"
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(out_path, dest_path)
        return dest_path

    def list_output_files(self) -> List[Dict[str, any]]:
        """List all files in the FVS working directory.

        Returns:
            List of dicts with 'name', 'size', and 'path' for each file.
        """
        if not self._work_dir.exists():
            return []
        return [
            {"name": f.name, "size": f.stat().st_size, "path": f}
            for f in sorted(self._work_dir.iterdir())
            if f.is_file()
        ]

    def get_yield_table(self) -> List[Dict[str, float]]:
        """Get the complete yield table from the FVS simulation.

        Returns cycle-by-cycle summary data in a format compatible with
        the pyfvs validation system. FVS summary uses 1-based indexing:
        cycle 1 = initial conditions, cycle ncycles+1 = final state.

        Note: IOSUM summary values are integer-encoded. Begin-of-period
        BA, SDI, CCF, TopHt, QMD are NOT in IOSUM (they live in the
        SUMTAB common block and are not accessible via fvsSummary).

        Returns:
            List of dictionaries, one per cycle, with keys matching
            FVS summary output fields.
        """
        dims = self._bindings.get_dim_sizes()
        ncycles = dims["ncycles"]

        # If dims doesn't have ncycles, try to get it from summary
        if ncycles <= 0:
            try:
                s = self._bindings.get_summary(1)
                ncycles = s["ncycles"]
            except FVSNativeError:
                return []

        yield_table = []
        # FVS summary is 1-indexed: cycle 1 through ncycles+1
        for cycle in range(1, ncycles + 2):
            try:
                summary = self._bindings.get_summary(cycle)
                yield_table.append(summary)
            except FVSNativeError:
                logger.warning("Could not retrieve summary for cycle %d", cycle)

        return yield_table
