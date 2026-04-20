"""Tests for Stand.initialize_natural (MVP natural-regen entry point).

Covers the pipeline-relevant variants and confirms:
- the initializer returns a stand with bare_ground pending
- grow() consumes the establishment cycle then the remaining rotation
- get_metrics() returns the 8 keys the forest-rents pipeline consumes
- natural stands do not outgrow planted stands at the same rotation
- random_seed gives reproducible results
"""
import pytest

from pyfvs import Stand


PIPELINE_METRIC_KEYS = {
    'volume',
    'basal_area',
    'qmd',
    'merchantable_volume',
    'board_feet',
    'tpa',
    'mean_height',
    'top_height',
}


@pytest.mark.parametrize("variant,species", [
    ('SN', 'LP'),
    ('NE', 'WP'),
    ('LS', 'RP'),
    ('CS', 'WO'),
    ('PN', 'DF'),
    ('WS', 'DF'),
    ('CA', 'DF'),
])
def test_initialize_natural_smoke(variant, species):
    """Each pipeline variant can initialize, grow, and report metrics."""
    stand = Stand.initialize_natural(
        trees_per_acre=400,
        site_index=70,
        species=species,
        variant=variant,
        random_seed=42,
    )

    assert stand._establishment_pending is True
    assert stand.age == 0
    assert len(stand.trees) == 400

    stand.grow(years=25)

    metrics = stand.get_metrics()
    assert PIPELINE_METRIC_KEYS.issubset(metrics.keys())
    for key in PIPELINE_METRIC_KEYS:
        assert metrics[key] >= 0, f"{variant}/{species}: {key} = {metrics[key]}"
    assert metrics['tpa'] > 0


def test_establishment_cycle_fires_on_first_grow():
    """bare_ground flag clears after the first cycle runs."""
    from pyfvs.variant_registry import get_variant_config

    stand = Stand.initialize_natural(
        trees_per_acre=300,
        site_index=70,
        species='LP',
        variant='SN',
        random_seed=7,
    )
    cycle = get_variant_config('SN').cycle_length

    assert stand._establishment_pending is True
    stand.grow(years=cycle)
    assert stand._establishment_pending is False
    assert stand.age == cycle


def test_natural_does_not_outgrow_planted_at_same_rotation():
    """At a fixed rotation, natural regen (first cycle spent establishing)
    produces <= basal area than planted (starts at cycle-length size)."""
    planted = Stand.initialize_planted(
        trees_per_acre=500, site_index=70, species='LP',
        variant='SN', random_seed=123,
    )
    natural = Stand.initialize_natural(
        trees_per_acre=500, site_index=70, species='LP',
        variant='SN', random_seed=123,
    )

    planted.grow(years=25)
    natural.grow(years=25)

    p_ba = planted.get_metrics()['basal_area']
    n_ba = natural.get_metrics()['basal_area']
    assert n_ba <= p_ba, (
        f"natural BA ({n_ba:.2f}) should not exceed planted BA ({p_ba:.2f})"
    )


def test_reproducible_with_seed():
    """Identical random_seed -> identical metrics."""
    def run():
        stand = Stand.initialize_natural(
            trees_per_acre=400, site_index=70, species='LP',
            variant='SN', random_seed=99,
        )
        stand.grow(years=20)
        return stand.get_metrics()

    a = run()
    b = run()
    for key in PIPELINE_METRIC_KEYS:
        assert a[key] == b[key], f"key {key} differs: {a[key]} vs {b[key]}"


def test_rejects_nonpositive_tpa():
    with pytest.raises(ValueError):
        Stand.initialize_natural(trees_per_acre=0, site_index=70, species='LP')
    with pytest.raises(ValueError):
        Stand.initialize_natural(trees_per_acre=-10, site_index=70, species='LP')
