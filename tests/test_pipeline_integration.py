"""Forest-rents pipeline integration smoke tests.

Exercises every (region, species) pair the forest-rents pipeline
simulates. Mirrors the pipeline's own call pattern:

    set_default_variant(variant)
    stand = Stand.initialize_planted(trees_per_acre, site_index, species,
                                     variant=variant, random_seed=...)
    stand.grow(years=rotation_age)
    metrics = stand.get_metrics()  # 8 required keys

Goal: catch any remaining coverage gap (missing coefficient, volume-model
failure, fallback-to-SN) in one test run rather than having the pipeline
find them one at a time.
"""
import pytest

from pyfvs import Stand, set_default_variant
from pyfvs.config_loader import get_default_variant


PIPELINE_METRIC_KEYS = {
    'volume', 'basal_area', 'qmd', 'merchantable_volume', 'board_feet',
    'tpa', 'mean_height', 'top_height',
}

# Forest-rents pipeline specification: (region, short_code, FIA, variant).
# Mountain + pacific_northwest use species→variant dispatch because CA's
# Fortran species list doesn't include ES/AF/GF/WL and PN's doesn't include
# WL. See memory/project_forest_rents_pipeline.md.
PIPELINE_MATRIX = [
    # Southern (SN)
    ('southern', 'LP',  131, 'SN'),
    ('southern', 'SA',  111, 'SN'),
    ('southern', 'LL',  121, 'SN'),
    ('southern', 'SP',  110, 'SN'),
    ('southern', 'WO',  802, 'SN'),
    ('southern', 'RO',  833, 'SN'),
    ('southern', 'YP',  621, 'SN'),
    ('southern', 'SU',  611, 'SN'),
    ('southern', 'HI',  400, 'SN'),
    # Northeast (NE)
    ('northeast', 'WP', 129, 'NE'),
    ('northeast', 'RS',  97, 'NE'),
    ('northeast', 'BF',  12, 'NE'),
    ('northeast', 'SM', 318, 'NE'),
    ('northeast', 'RM', 316, 'NE'),
    ('northeast', 'RO', 833, 'NE'),
    ('northeast', 'YB', 371, 'NE'),
    ('northeast', 'BC', 762, 'NE'),
    # Lake States (LS)
    ('lake_states', 'RP', 125, 'LS'),
    ('lake_states', 'JP', 105, 'LS'),
    ('lake_states', 'WP', 129, 'LS'),
    ('lake_states', 'WS',  94, 'LS'),
    ('lake_states', 'BF',  12, 'LS'),
    ('lake_states', 'QA', 746, 'LS'),
    ('lake_states', 'SM', 318, 'LS'),
    ('lake_states', 'RO', 833, 'LS'),
    ('lake_states', 'YB', 371, 'LS'),
    ('lake_states', 'PB', 375, 'LS'),
    ('lake_states', 'WA', 541, 'LS'),
    # Central States (CS)
    ('central_states', 'WO', 802, 'CS'),
    ('central_states', 'WN', 602, 'CS'),
    ('central_states', 'BC', 762, 'CS'),
    ('central_states', 'RO', 833, 'CS'),
    ('central_states', 'SM', 318, 'CS'),
    ('central_states', 'SH', 402, 'CS'),
    ('central_states', 'YP', 621, 'CS'),
    ('central_states', 'RM', 316, 'CS'),
    # Pacific Northwest
    ('pacific_northwest', 'DF', 202, 'PN'),
    ('pacific_northwest', 'WH', 263, 'PN'),
    ('pacific_northwest', 'SS',  98, 'PN'),
    ('pacific_northwest', 'RC', 242, 'PN'),
    ('pacific_northwest', 'PP', 122, 'PN'),
    ('pacific_northwest', 'LP', 108, 'PN'),
    ('pacific_northwest', 'GF',  17, 'PN'),
    ('pacific_northwest', 'WL',  73, 'EC'),
    # Mountain
    ('mountain', 'DF', 202, 'CA'),
    ('mountain', 'PP', 122, 'CA'),
    ('mountain', 'LP', 108, 'CA'),
    ('mountain', 'WF',  15, 'CA'),
    ('mountain', 'ES',  93, 'PN'),
    ('mountain', 'AF',  19, 'PN'),
    ('mountain', 'GF',  17, 'PN'),
    ('mountain', 'WL',  73, 'EC'),
]


@pytest.fixture(autouse=True)
def _restore_default_variant():
    """Reset module-global default variant after each test."""
    saved = get_default_variant()
    yield
    set_default_variant(saved)


def _run(species, variant, site_index=70, tpa=400, rotation=25,
         seed=42, natural=False):
    """Mirror the forest-rents pipeline call pattern."""
    set_default_variant(variant)
    ctor = Stand.initialize_natural if natural else Stand.initialize_planted
    stand = ctor(
        trees_per_acre=tpa,
        site_index=site_index,
        species=species,
        variant=variant,
        random_seed=seed,
    )
    stand.grow(years=rotation)
    return stand.get_metrics()


def _assert_metrics_sane(m, label):
    """Pipeline-shape checks: 8 keys, non-negative, in plausible ranges."""
    missing = PIPELINE_METRIC_KEYS - set(m.keys())
    assert not missing, f"{label}: missing keys {missing}"

    for key in PIPELINE_METRIC_KEYS:
        assert m[key] >= 0, f"{label}: {key} = {m[key]}"

    assert m['tpa'] > 0, f"{label}: tpa = {m['tpa']} (stand fully died)"
    assert 1.0 <= m['qmd'] <= 60, f"{label}: qmd={m['qmd']} out of range"
    assert 5 <= m['top_height'] <= 200, f"{label}: top_height={m['top_height']}"
    assert 0 < m['basal_area'] <= 500, f"{label}: basal_area={m['basal_area']}"


@pytest.mark.parametrize("region,short,fia,variant", PIPELINE_MATRIX)
def test_planted_pipeline_species(region, short, fia, variant):
    label = f"{region}/{variant}/{short} (FIA {fia})"
    metrics = _run(short, variant, seed=42)
    _assert_metrics_sane(metrics, label)


@pytest.mark.parametrize("region,short,fia,variant", PIPELINE_MATRIX)
def test_natural_pipeline_species(region, short, fia, variant):
    """Natural-regen variant of the same matrix. Catches variants where
    the establishment cycle can't seed a species cohort."""
    label = f"natural/{region}/{variant}/{short} (FIA {fia})"
    metrics = _run(short, variant, seed=42, natural=True, rotation=30)
    _assert_metrics_sane(metrics, label)


def test_pipeline_coverage_completeness():
    """Guard against the matrix drifting away from the documented pipeline
    spec. Counts match memory/project_forest_rents_pipeline.md."""
    counts = {}
    for region, _, _, _ in PIPELINE_MATRIX:
        counts[region] = counts.get(region, 0) + 1

    assert counts == {
        'southern': 9,
        'northeast': 8,
        'lake_states': 11,
        'central_states': 8,
        'pacific_northwest': 8,
        'mountain': 8,
    }, counts
