from __future__ import annotations

from baselines import molerec_profile as adapter


def test_profile_patient_split_matches_frozen_miii_contract() -> None:
    train, dev = adapter.patient_split(6350)
    assert len(train) == 4233
    assert len(dev) == 1004
    assert train == tuple(range(4233))
    assert not set(train).intersection(dev)


def test_profile_operating_points_are_the_frozen_global_grid() -> None:
    assert adapter.OPERATING_POINTS == (
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
        0.95,
    )
    assert adapter.NATIVE_DEFAULT == 0.35


def test_profile_membership_digests_match_frozen_profile() -> None:
    train, dev = adapter.patient_split(6350)
    assert adapter._membership_digest(train) == (
        "43124aa2cf02e1f7780ee6dcc97e936dd412a836bad742d1423c57f7ad282f3c"
    )
    assert adapter._membership_digest(dev) == (
        "6377c372218ab566162d9d347f515e1590af0843f243f10c2f03b11d18d73215"
    )


def test_profile_seed_rejects_unregistered_variants() -> None:
    class DummyTorch:
        def manual_seed(self, value: int) -> None:
            raise AssertionError(value)

    class DummyNumpy:
        def seed(self, value: int) -> None:
            raise AssertionError(value)

    try:
        adapter._seed(1204, DummyTorch(), DummyNumpy())
    except adapter.MoleRecProfileError as error:
        assert "only source seed 1203" in str(error)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("unregistered seed was accepted")


def test_profile_model_declares_no_medication_history_consumption() -> None:
    rows = adapter._rows([[[[0], [0], [1, 2]]]], (0,))
    assert rows == [{"patient_id": "0", "visit_id": "0:0", "target": [1, 2]}]
    assert set(rows[0]) == {"patient_id", "visit_id", "target"}


def test_profile_forward_prefix_clears_only_current_target() -> None:
    patient = [[[1], [2], [3]], [[4], [5], [6, 7]]]
    assert adapter._target_free_prefix(patient, 1) == [[[1], [2], []]]
    assert adapter._target_free_prefix(patient, 2) == [
        [[1], [2], [3]],
        [[4], [5], []],
    ]
