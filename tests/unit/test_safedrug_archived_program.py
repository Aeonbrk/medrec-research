from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from baselines import safedrug_archived as adapter


def paper_values() -> tuple[
    list[list[list[list[int]]]],
    dict[str, object],
    list[list[int]],
    list[list[int]],
    list[list[int]],
    dict[str, object],
]:
    diag_words = [f"D{i}" for i in range(128)]
    pro_words = [f"P{i}" for i in range(50)]
    med_words = [f"M{i}" for i in range(131)]

    # Patient 0: 2 admissions, has 128 diag, 50 pro, 65 med
    p0_adm1 = [list(range(64)), list(range(25)), list(range(32))]
    p0_adm2 = [list(range(64, 128)), list(range(25, 50)), list(range(32, 65))]
    records = [[p0_adm1, p0_adm2]]

    # 5466 patients with 25 diag, 9/10 pro, 27/28 med
    for i in range(5466):
        adm1 = [list(range(13)), list(range(5)), list(range(14))]
        adm2 = [list(range(13, 25)), list(range(5, 9)), list(range(14, 27))]
        if i < 587:
            adm2[1] = list(range(5, 10))
        if i < 412:
            adm2[2] = list(range(14, 28))
        records.append([adm1, adm2])

    # 882 patients with 24 diag, 9 pro, 27 med
    for _ in range(882):
        adm1 = [list(range(12)), list(range(5)), list(range(14))]
        adm2 = [list(range(12, 24)), list(range(5, 9)), list(range(14, 27))]
        records.append([adm1, adm2])

    # 1 patient with 2334 visits (24 diag, 9 pro, 27 med across all visits)
    p_last = []
    for v in range(2334):
        p_last.append([[v % 24], [v % 9], [v % 27]])
    records.append(p_last)

    vocabulary = {
        "diag_voc": SimpleNamespace(
            idx2word=diag_words, word2idx={w: i for i, w in enumerate(diag_words)}
        ),
        "pro_voc": SimpleNamespace(
            idx2word=pro_words, word2idx={w: i for i, w in enumerate(pro_words)}
        ),
        "med_voc": SimpleNamespace(
            idx2word=med_words, word2idx={w: i for i, w in enumerate(med_words)}
        ),
    }
    ddi = [[0] * 131 for _ in range(131)]
    pairs = ((row, column) for row in range(131) for column in range(row + 1, 131))
    for row, column in itertools.islice(pairs, 448):
        ddi[row][column] = ddi[column][row] = 1
    ddi_mask = [[0] * 491 for _ in range(131)]
    ehr_adj = [[0] * 131 for _ in range(131)]
    idx2drug = {code: "CC(=O)O" for code in med_words}
    idx2drug["seperator"] = {}
    idx2drug["decoder_point"] = {}
    return records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug


def test_profiles_match_archived_entrypoints_and_defaults() -> None:
    observed = {
        baseline_id: (profile.entrypoint, profile.model_name, profile.learning_rate)
        for baseline_id, profile in adapter.PROFILES.items()
    }
    assert observed == {
        "gamenet": ("GAMENet.py", "GAMENet", 1e-4),
        "safedrug": ("SafeDrug.py", "SafeDrug", 5e-4),
        "safedrug-lr-1e-5": ("SafeDrug.py", "SafeDrug", 1e-5),
        "safedrug-lr-1e-4": ("SafeDrug.py", "SafeDrug", 1e-4),
        "safedrug-lr-5e-4": ("SafeDrug.py", "SafeDrug", 5e-4),
        "retain": ("Retain.py", "Retain", 5e-4),
        "leap-safedrug": ("Leap.py", "Leap", 5e-4),
    }

    assert adapter.PROFILES["safedrug"].required_inputs[-3:] == (
        "ehr_adj_final.pkl",
        "ddi_mask_H.pkl",
        "idx2drug.pkl",
    )


def test_training_mode_adaptation_is_exact_and_reversible() -> None:
    source = f"before\n{adapter.TEST_DECLARATION}\nafter\n"
    adapted = adapter.adapt_training_source(source)

    assert adapter.TEST_DECLARATION not in adapted
    assert adapted.count(adapter.TRAIN_DECLARATION) == 1
    assert adapted.replace(adapter.TRAIN_DECLARATION, adapter.TEST_DECLARATION) == source
    assert adapter.test_mode_default(source) is True
    assert adapter.test_mode_default(adapted) is False
    assert adapter.test_mode_default(f"{adapted}\n# --Test") is False


def test_epoch_adaptation_is_exact_and_reversible() -> None:
    source = f"def main():\n{adapter.EPOCH_FORMAL}    pass\n"
    adapted = adapter.adapt_epoch_source(source)

    assert adapter.EPOCH_FORMAL not in adapted
    assert adapted.count(adapter.EPOCH_SMOKE) == 1
    assert adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1) == source


def test_smoke_adaptation_composition_and_leap_fine_tune_preservation() -> None:
    leap_source = (
        "def fine_tune():\n"
        "    EPOCH = 100\n"
        "def main():\n"
        f"{adapter.TEST_DECLARATION}\n"
        f"{adapter.EPOCH_FORMAL}"
        "    pass\n"
    )
    smoke_adapted = adapter.adapt_smoke_source(leap_source)

    assert adapter.TEST_DECLARATION not in smoke_adapted
    assert adapter.TRAIN_DECLARATION in smoke_adapted
    assert adapter.EPOCH_FORMAL not in smoke_adapted
    assert adapter.EPOCH_SMOKE in smoke_adapted
    assert "    EPOCH = 100\n" in smoke_adapted

    reversed_source = smoke_adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1).replace(
        adapter.TRAIN_DECLARATION, adapter.TEST_DECLARATION
    )
    assert reversed_source == leap_source


def test_smoke_adaptation_handles_parser_rates_and_already_aligned_rate() -> None:
    safedrug_source = (
        "parser.add_argument('--lr', type=float, default=5e-4, help='learning rate')\n"
        f"{adapter.TEST_DECLARATION}\n"
        f"{adapter.EPOCH_FORMAL}"
    )
    adapted = adapter.adapt_smoke_source(safedrug_source, target_lr=1e-4)
    assert "default=1e-4" in adapted
    assert (
        adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1)
        .replace(adapter.TRAIN_DECLARATION, adapter.TEST_DECLARATION)
        .replace("default=1e-4", "default=5e-4")
        == safedrug_source
    )

    gamenet_source = (
        "parser.add_argument('--lr', type=float, default=1e-4, help='learning rate')\n"
        f"{adapter.TEST_DECLARATION}\n"
        f"{adapter.EPOCH_FORMAL}"
    )
    gamenet_adapted = adapter.adapt_smoke_source(gamenet_source, target_lr=1e-4)
    assert "default=1e-4" in gamenet_adapted
    assert (
        gamenet_adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1).replace(
            adapter.TRAIN_DECLARATION, adapter.TEST_DECLARATION
        )
        == gamenet_source
    )


@pytest.mark.parametrize(
    "source",
    [
        "no declaration",
        f"{adapter.TEST_DECLARATION}\n{adapter.TEST_DECLARATION}",
        adapter.TRAIN_DECLARATION,
    ],
)
def test_training_mode_adaptation_rejects_source_drift(source: str) -> None:
    with pytest.raises(adapter.ReproductionError, match="drifted"):
        adapter.adapt_training_source(source)


@pytest.mark.parametrize(
    "source",
    [
        "no epoch declaration",
        f"{adapter.EPOCH_FORMAL}{adapter.EPOCH_FORMAL}",
        adapter.EPOCH_SMOKE,
    ],
)
def test_epoch_adaptation_rejects_source_drift(source: str) -> None:
    with pytest.raises(adapter.ReproductionError, match="drifted"):
        adapter.adapt_epoch_source(source)


def test_test_mode_default_rejects_ambiguous_source() -> None:
    with pytest.raises(adapter.ReproductionError, match="determine"):
        adapter.test_mode_default("no declaration")


def test_paper_dataset_counts_pass_exact_gate() -> None:
    from baselines import safedrug_archived_data

    records, vocabulary, ddi, ddi_mask, _, _ = paper_values()
    counts = safedrug_archived_data.count_dataset(records, vocabulary, ddi, ddi_mask)

    assert counts == safedrug_archived_data.EXPECTED_COUNTS
    safedrug_archived_data.require_executable_counts(counts)


def test_dataset_gate_rejects_non_paper_visit_count() -> None:
    from baselines import safedrug_archived_data

    counts = {**safedrug_archived_data.EXPECTED_COUNTS, "visits": 14_995}

    with pytest.raises(safedrug_archived_data.ReproductionError, match="visits"):
        safedrug_archived_data.require_executable_counts(counts)


def test_dataset_gate_uses_upper_triangle_and_rejects_count_drift() -> None:
    from baselines import safedrug_archived_data

    records, vocabulary, ddi, ddi_mask, _, _ = paper_values()
    ddi[0][1] = ddi[1][0] = 0
    counts = safedrug_archived_data.count_dataset(records, vocabulary, ddi, ddi_mask)

    assert counts["ddi_pairs"] == 447
    with pytest.raises(safedrug_archived_data.ReproductionError, match="ddi_pairs"):
        safedrug_archived_data.require_executable_counts(counts)


def test_dataset_gate_rejects_matrix_shape_drift() -> None:
    from baselines import safedrug_archived_data

    records, vocabulary, ddi, ddi_mask, _, _ = paper_values()

    with pytest.raises(safedrug_archived_data.ReproductionError, match="ddi_A_final shape"):
        safedrug_archived_data.count_dataset(records, vocabulary, ddi[:-1], ddi_mask)
    with pytest.raises(safedrug_archived_data.ReproductionError, match="ddi_mask_H rows"):
        safedrug_archived_data.count_dataset(records, vocabulary, ddi, ddi_mask[:-1])


def test_load_and_validate_canonical_inputs_validates_all_six(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pickle

    from baselines import safedrug_archived_data

    monkeypatch.setattr(
        safedrug_archived_data.importlib,
        "import_module",
        lambda name: pickle if name == "dill" else sys.modules.get(name),
    )

    records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug = paper_values()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    for name, val in [
        ("records_final.pkl", records),
        ("voc_final.pkl", vocabulary),
        ("ddi_A_final.pkl", ddi),
        ("ddi_mask_H.pkl", ddi_mask),
        ("ehr_adj_final.pkl", ehr_adj),
        ("idx2drug.pkl", idx2drug),
    ]:
        with (data_dir / name).open("wb") as stream:
            pickle.dump(val, stream)

    results, counts, bridge_checks, statistics_evidence, metadata_disclosure = (
        safedrug_archived_data.load_and_validate_canonical_inputs(data_dir)
    )
    assert len(results) == 6
    assert all(status == "passed" for status in results.values())
    assert counts == safedrug_archived_data.EXPECTED_COUNTS
    assert counts["visits"] == 15_032
    assert set(bridge_checks.keys()) == {
        "vocabulary_bijections",
        "records_structure",
        "idx2drug_contract",
        "ddi_matrix_properties",
        "ehr_matrix_properties",
        "ddi_mask_properties",
        "records_statistics",
    }
    assert all(v == "passed" for v in bridge_checks.values())
    assert statistics_evidence["diagnoses"]["numerator"] == 157_970
    assert statistics_evidence["procedures"]["numerator"] == 57_778
    assert statistics_evidence["medications"]["numerator"] == 171_900
    assert metadata_disclosure == {
        "paper_reported_visits": 14_995,
        "executable_visits": 15_032,
        "difference": 37,
    }


def test_load_and_validate_canonical_inputs_rejects_shape_or_length_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pickle
    import sys

    from baselines import safedrug_archived_data

    monkeypatch.setattr(
        safedrug_archived_data.importlib,
        "import_module",
        lambda name: pickle if name == "dill" else sys.modules.get(name),
    )

    records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug = paper_values()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    for name, val in [
        ("records_final.pkl", records),
        ("voc_final.pkl", vocabulary),
        ("ddi_A_final.pkl", ddi),
        ("ddi_mask_H.pkl", ddi_mask),
        ("ehr_adj_final.pkl", ehr_adj[:-1]),
        ("idx2drug.pkl", idx2drug),
    ]:
        with (data_dir / name).open("wb") as stream:
            pickle.dump(val, stream)

    with pytest.raises(adapter.ReproductionError, match="ehr_adj_final shape"):
        safedrug_archived_data.load_and_validate_canonical_inputs(data_dir)


def test_semantic_bridge_checks_reject_invalid_structures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pickle
    import sys

    from baselines import safedrug_archived_data

    monkeypatch.setattr(
        safedrug_archived_data.importlib,
        "import_module",
        lambda name: pickle if name == "dill" else sys.modules.get(name),
    )

    def write_dataset(overrides: dict[str, Any]) -> Path:
        data_dir = tmp_path / f"data_{len(list(tmp_path.iterdir()))}"
        data_dir.mkdir()
        records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug = paper_values()
        vals = {
            "records_final.pkl": records,
            "voc_final.pkl": vocabulary,
            "ddi_A_final.pkl": ddi,
            "ddi_mask_H.pkl": ddi_mask,
            "ehr_adj_final.pkl": ehr_adj,
            "idx2drug.pkl": idx2drug,
            **overrides,
        }
        for name, val in vals.items():
            with (data_dir / name).open("wb") as stream:
                pickle.dump(val, stream)
        return data_dir

    # 1. Asymmetric DDI matrix
    records, _vocabulary, ddi, _ddi_mask, ehr_adj, _idx2drug = paper_values()
    ddi_asym = [row[:] for row in ddi]
    ddi_asym[0][1] = 1
    ddi_asym[1][0] = 0
    d1 = write_dataset({"ddi_A_final.pkl": ddi_asym})
    with pytest.raises(adapter.ReproductionError, match="must be symmetric"):
        safedrug_archived_data.load_and_validate_canonical_inputs(d1)

    # 2. Non-zero diagonal in DDI matrix
    ddi_diag = [row[:] for row in ddi]
    ddi_diag[0][0] = 1
    d2 = write_dataset({"ddi_A_final.pkl": ddi_diag})
    with pytest.raises(adapter.ReproductionError, match="zero diagonal"):
        safedrug_archived_data.load_and_validate_canonical_inputs(d2)

    # 3. Asymmetric EHR adjacency matrix
    ehr_asym = [row[:] for row in ehr_adj]
    ehr_asym[0][1] = 1
    ehr_asym[1][0] = 0
    d3 = write_dataset({"ehr_adj_final.pkl": ehr_asym})
    with pytest.raises(safedrug_archived_data.ReproductionError, match="must be symmetric"):
        safedrug_archived_data.load_and_validate_canonical_inputs(d3)

    # 4. Inconsistent idx2drug keys
    _, _, _, _, _, idx2drug_bad = paper_values()
    del idx2drug_bad["seperator"]
    d4 = write_dataset({"idx2drug.pkl": idx2drug_bad})
    with pytest.raises(safedrug_archived_data.ReproductionError, match="idx2drug keys mismatch"):
        safedrug_archived_data.load_and_validate_canonical_inputs(d4)

    # 5. Invalid admission indices out of vocabulary bounds
    records_bad1 = [patient[:] for patient in records]
    records_bad1[0] = [[records[0][0][0][:], records[0][0][1][:], [9999]], records[0][1]]
    d5 = write_dataset({"records_final.pkl": records_bad1})
    with pytest.raises(safedrug_archived_data.ReproductionError, match="invalid index"):
        safedrug_archived_data.load_and_validate_canonical_inputs(d5)

    records_bad2 = [patient[:] for patient in records]
    records_bad2[0] = [[[9999], records[0][0][1][:], records[0][0][2][:]], records[0][1]]
    d6 = write_dataset({"records_final.pkl": records_bad2})
    with pytest.raises(safedrug_archived_data.ReproductionError, match="invalid index"):
        safedrug_archived_data.load_and_validate_canonical_inputs(d6)


def test_probe_environment_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from baselines import safedrug_archived_probe as probe_mod

    monkeypatch.setattr(
        probe_mod,
        "check_imports",
        lambda upstream: {m: "passed" for m in probe_mod.REGISTRY_IMPORT_MODULES},
    )
    monkeypatch.setattr(probe_mod, "check_cuda_tensor", lambda: "passed")
    monkeypatch.setattr(probe_mod, "check_rdkit_brics", lambda: "passed")
    monkeypatch.setattr(probe_mod, "check_dnc_forward", lambda: "passed")
    monkeypatch.setattr(
        probe_mod,
        "probe_environment_details",
        lambda: {
            "conda_explicit_sha256": "f" * 64,
            "python": "3.11.9",
            "pytorch": "2.2.2",
            "torch_cuda": "12.1",
            "nvidia_driver": "535.183.01",
            "numpy": "1.26.4",
            "pandas": "2.0.3",
            "scipy": "1.11.4",
            "scikit_learn": "1.3.2",
            "rdkit": "2023.09.6",
            "dill": "0.3.7",
            "dnc": "1.1.0",
            "cuda_visible_device_count": 1,
            "gpu_name": "NVIDIA GeForce RTX 3090",
            "gpu_capability": "8.6",
        },
    )

    (tmp_path / "upstream" / "src").mkdir(parents=True)
    probe = probe_mod.run_probe(
        baseline_id="gamenet",
        upstream_root=tmp_path / "upstream",
        data_dir=None,
        scope="environment",
    )

    assert probe["schema_version"] == 1
    assert probe["kind"] == "safedrug_archived_probe"
    assert probe["scope"] == "environment"
    assert probe["baseline_id"] == "gamenet"
    assert probe["source_revision"] == adapter.ARCHIVED_REVISION
    assert probe["checks"]["cuda_tensor"] == "passed"
    assert probe["inputs"] is None
    assert probe["dataset_counts"] is None


def test_probe_full_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from baselines import safedrug_archived_data
    from baselines import safedrug_archived_probe as probe_mod

    monkeypatch.setattr(
        probe_mod,
        "check_imports",
        lambda upstream: {m: "passed" for m in probe_mod.REGISTRY_IMPORT_MODULES},
    )
    monkeypatch.setattr(probe_mod, "check_cuda_tensor", lambda: "passed")
    monkeypatch.setattr(probe_mod, "check_rdkit_brics", lambda: "passed")
    monkeypatch.setattr(probe_mod, "check_dnc_forward", lambda: "passed")
    monkeypatch.setattr(
        probe_mod,
        "probe_environment_details",
        lambda: {
            "conda_explicit_sha256": "f" * 64,
            "python": "3.11.9",
            "pytorch": "2.2.2",
            "torch_cuda": "12.1",
            "nvidia_driver": "535.183.01",
            "numpy": "1.26.4",
            "pandas": "2.0.3",
            "scipy": "1.11.4",
            "scikit_learn": "1.3.2",
            "rdkit": "2023.09.6",
            "dill": "0.3.7",
            "dnc": "1.1.0",
            "cuda_visible_device_count": 1,
            "gpu_name": "NVIDIA GeForce RTX 3090",
            "gpu_capability": "8.6",
        },
    )
    monkeypatch.setattr(
        probe_mod,
        "load_and_validate_canonical_inputs",
        lambda d: (
            {name: "passed" for name in safedrug_archived_data.CANONICAL_SIX_INPUTS},
            safedrug_archived_data.EXPECTED_COUNTS,
            {"vocabulary_bijections": "passed", "records_structure": "passed"},
            {
                "diagnoses": {"numerator": 157_970, "average": 10.5089, "max": 128},
                "procedures": {"numerator": 57_778, "average": 3.8437, "max": 50},
                "medications": {"numerator": 171_900, "average": 11.4356, "max": 65},
            },
            safedrug_archived_data.REPORTED_PAPER_METADATA,
        ),
    )

    (tmp_path / "upstream" / "src").mkdir(parents=True)
    (tmp_path / "data").mkdir(parents=True)
    probe = probe_mod.run_probe(
        baseline_id="safedrug",
        upstream_root=tmp_path / "upstream",
        data_dir=tmp_path / "data",
        scope="full",
    )

    assert probe["schema_version"] == 1
    assert probe["scope"] == "full"
    assert len(probe["inputs"]) == 6
    assert probe["dataset_counts"] == safedrug_archived_data.EXPECTED_COUNTS
    assert probe["bridge_checks"] == {
        "vocabulary_bijections": "passed",
        "records_structure": "passed",
    }
    assert probe["metadata"] == safedrug_archived_data.REPORTED_PAPER_METADATA
    assert probe["statistics"]["diagnoses"]["numerator"] == 157_970


def test_smoke_lane_executes_one_epoch_and_emits_smoke_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from baselines import safedrug_archived_data

    upstream = tmp_path / "upstream"
    upstream_src = upstream / "src"
    upstream_src.mkdir(parents=True)
    entrypoint = upstream_src / "SafeDrug.py"
    entrypoint.write_text(
        f"import sys\n{adapter.TEST_DECLARATION}\ndef main():\n{adapter.EPOCH_FORMAL}    pass\n",
        encoding="utf-8",
    )

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in safedrug_archived_data.CANONICAL_SIX_INPUTS:
        (data_dir / name).touch()

    run_root = tmp_path / "runs" / "smoke_run"

    monkeypatch.setattr(adapter, "verify_upstream_source", lambda root: None)
    monkeypatch.setattr(
        adapter,
        "load_and_validate_canonical_inputs",
        lambda d: (
            {name: "passed" for name in safedrug_archived_data.CANONICAL_SIX_INPUTS},
            safedrug_archived_data.EXPECTED_COUNTS,
            {"vocabulary_bijections": "passed"},
            {
                "diagnoses": {"numerator": 157_970, "average": 10.5089, "max": 128},
                "procedures": {"numerator": 57_778, "average": 3.8437, "max": 50},
                "medications": {"numerator": 171_900, "average": 11.4356, "max": 65},
            },
            safedrug_archived_data.REPORTED_PAPER_METADATA,
        ),
    )
    monkeypatch.setattr(
        adapter,
        "environment_summary",
        lambda: {"conda_explicit_sha256": "f" * 64, "python": "3.11.9"},
    )

    def mock_run_logged(cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
        log_path.write_text("epoch 1 -------------------\nbest_epoch: 0\n", encoding="utf-8")
        checkpoint_dir = cwd / "saved" / f"SafeDrug_{run_root.name}"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "Epoch_0_TARGET_0.0_JA_0.5000_DDI_0.0800.model").touch()

    monkeypatch.setattr(adapter, "run_logged", mock_run_logged)

    adapter.run_smoke_lane(
        profile=adapter.PROFILES["safedrug"],
        upstream_root=upstream,
        data_dir=data_dir,
        run_root=run_root,
        python="python",
    )

    assert not (run_root / "test.log").exists()
    assert not (run_root / "result.json").exists()

    status = json.loads((run_root / "status.json").read_text())
    assert status["schema_version"] == 1
    assert status["kind"] == "safedrug_archived_smoke_status"
    assert status["state"] == "completed"
    assert status["stage"] == "terminal"

    smoke = json.loads((run_root / "smoke.json").read_text())
    assert smoke["schema_version"] == 1
    assert smoke["kind"] == "safedrug_archived_smoke"
    assert smoke["non_evidence"] is True
    assert smoke["baseline_id"] == "safedrug"
    assert smoke["epochs_requested"] == 1
    assert smoke["epochs_observed"] == 1
    assert smoke["best_epoch"] == 0
    assert smoke["checkpoint"]["best_epoch"] == 0
    assert len(smoke["checkpoint"]["sha256"]) == 64


def _write_test_selection_artifact(selection_path: Path) -> tuple[Path, dict[str, Any]]:
    from medrec_research.reproduction.safedrug_selection import (
        SAFE_DRUG_LANE_IDS,
        select_safedrug_candidate,
        write_selection,
    )

    specs = {
        "molerec-safedrug-lr-1e-5": (1e-5, 0.50, 0.08),
        "molerec-safedrug-lr-1e-4": (1e-4, 0.51, 0.07),
        "molerec-safedrug-lr-5e-4": (5e-4, 0.52, 0.06),
    }
    candidates = []
    for lane_id in SAFE_DRUG_LANE_IDS:
        lr, jaccard, ddi_rate = specs[lane_id]
        checkpoint_bytes = f"{lane_id}-bytes".encode()
        checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
        candidates.append(
            {
                "lane_id": lane_id,
                "learning_rate": lr,
                "checkpoint_identity": checkpoint_sha256,
                "validation_jaccard": jaccard,
                "validation_ddi_rate": ddi_rate,
                "training_evidence": {
                    "state": "completed",
                    "artifact_type": "training",
                    "identity": {
                        "attempt_id": "attempt-1",
                        "lane_id": lane_id,
                        "scientific_baseline_id": "safedrug",
                        "program_id": "safedrug-archived",
                        "profile_id": "safedrug",
                        "harness_revision": "a" * 40,
                        "model_source_revision": adapter.ARCHIVED_REVISION,
                        "preprocessing_revision": "c" * 40,
                        "snapshot_id": "snapshots/molerec-table1-c721-www23",
                        "environment_sha256": "d" * 64,
                        "mode": "formal",
                        "submission_id": f"submission-{lane_id}",
                    },
                    "learning_rate": lr,
                    "best_epoch": 49,
                    "validation_jaccard": jaccard,
                    "validation_ddi_rate": ddi_rate,
                    "checkpoint": {
                        "best_epoch": 49,
                        "relative_path": f"work/saved/SafeDrug_{lane_id}/Epoch_49.model",
                        "sha256": checkpoint_sha256,
                        "size_bytes": len(checkpoint_bytes),
                    },
                    "recovery": None,
                },
            }
        )

    selection_record = select_safedrug_candidate(candidates)
    write_selection(selection_path, selection_record)
    valid_selection = json.loads(selection_path.read_text(encoding="utf-8"))
    return selection_path, valid_selection


def test_training_and_test_commands_preserve_archived_cli_behavior(tmp_path: Path) -> None:
    entrypoint = tmp_path / "work" / "SafeDrug.py"
    entrypoint.parent.mkdir(parents=True, exist_ok=True)
    entrypoint.touch()
    original = tmp_path / "upstream" / "src" / "SafeDrug.py"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.touch()
    checkpoint = tmp_path / "work" / "saved" / "SafeDrug_run" / "Epoch_49.model"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.touch()
    selection_path, _ = _write_test_selection_artifact(tmp_path / "selection.json")

    assert adapter.training_command("python", entrypoint, "SafeDrug_run") == [
        "python",
        str(entrypoint),
        "--model_name",
        "SafeDrug_run",
    ]
    assert adapter.test_command(
        "python",
        original,
        adapter.PROFILES["safedrug"],
        "SafeDrug_run",
        checkpoint,
        lane_id="molerec-safedrug-lr-5e-4",
        selection_path=selection_path,
    )[-3:] == ["--Test", "--resume_path", str(checkpoint.resolve())]
    assert (
        adapter.test_command(
            "python", original, adapter.PROFILES["retain"], "Retain_run", checkpoint
        )[-1]
        == checkpoint.name
    )


def test_checkpoint_selection_uses_zero_based_best_epoch(tmp_path: Path) -> None:
    from baselines import safedrug_archived_logs

    checkpoint = tmp_path / "Epoch_49_JA_0.5000_DDI_0.0800.model"
    checkpoint.touch()

    assert (
        safedrug_archived_logs.select_checkpoint(tmp_path, adapter.PROFILES["gamenet"], 49)
        == checkpoint
    )


def test_native_history_path_is_model_specific(tmp_path: Path) -> None:
    assert adapter.native_history_path(tmp_path, "Retain_attempt-1") == (
        tmp_path / "history_Retain_attempt-1.pkl"
    )


def test_environment_summary_records_conda_and_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from baselines import safedrug_archived_probe

    completed = SimpleNamespace(stdout=b"explicit lock\n")
    monkeypatch.setattr(
        safedrug_archived_probe.subprocess, "run", lambda *args, **kwargs: completed
    )

    summary = safedrug_archived_probe.environment_summary()

    assert len(summary["conda_explicit_sha256"]) == 64
    assert summary["python"] == sys.version.split()[0]


def test_test_log_requires_ten_rounds_and_matching_upstream_summary() -> None:
    from baselines import safedrug_archived_logs

    metric_line = (
        "DDI Rate: 0.1, Jaccard: 0.2, PRAUC: 0.3, AVG_PRC: 0.4, "
        "AVG_RECALL: 0.5, AVG_F1: 0.6, AVG_MED: 7.0"
    )
    summary_line = (
        "0.1000 $\\pm$ 0.0000 & 0.2000 $\\pm$ 0.0000 & "
        "0.6000 $\\pm$ 0.0000 & 0.3000 $\\pm$ 0.0000 & 7.0000 $\\pm$ 0.0000 &"
    )

    parsed = safedrug_archived_logs.parse_test_log("\n".join([metric_line] * 10 + [summary_line]))

    assert len(parsed["test_rounds"]) == 10
    assert parsed["harness_summary"]["avg_f1"]["mean"] == pytest.approx(0.6)
    with pytest.raises(safedrug_archived_logs.ReproductionError, match="disagrees"):
        safedrug_archived_logs.parse_test_log(
            "\n".join([metric_line] * 10 + [summary_line.replace("0.1000", "0.2000", 1)])
        )


def test_test_log_comparison_respects_upstream_significant_digit_precision() -> None:
    from baselines import safedrug_archived_logs

    metric_line = (
        "DDI Rate: 0.1, Jaccard: 0.2, PRAUC: 0.3, AVG_PRC: 0.4, "
        "AVG_RECALL: 0.5, AVG_F1: 0.6, AVG_MED: 20.58"
    )
    summary_line = (
        "0.1000 $\\pm$ 0.0000 & 0.2000 $\\pm$ 0.0000 & "
        "0.6000 $\\pm$ 0.0000 & 0.3000 $\\pm$ 0.0000 & 20.5825 $\\pm$ 0.0000 &"
    )

    safedrug_archived_logs.parse_test_log("\n".join([metric_line] * 10 + [summary_line]))


def test_terminal_status_is_written_before_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []
    original_write_json = adapter.write_json

    def recording_write(path: Path, value: dict[str, object]) -> None:
        calls.append(path)
        original_write_json(path, value)

    monkeypatch.setattr(adapter, "write_json", recording_write)
    status = {"state": "completed", "stage": "terminal"}
    adapter._publish_legacy_terminal_status(tmp_path, status, {"schema_version": 1})

    assert [path.name for path in calls] == ["status.json", "result.json"]
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == status


def test_internal_modules_importable_and_consistent() -> None:
    from baselines import (
        safedrug_archived_data,
        safedrug_archived_logs,
        safedrug_archived_probe,
    )

    assert safedrug_archived_data.EXPECTED_COUNTS["patients"] == 6350
    assert hasattr(safedrug_archived_data, "load_and_validate_canonical_inputs")
    assert not hasattr(safedrug_archived_data, "load_archived_values")
    assert not hasattr(adapter, "load_archived_values")
    assert hasattr(safedrug_archived_logs, "parse_training_log")
    assert hasattr(safedrug_archived_probe, "run_probe")
    assert adapter.__all__ == ("execute", "probe")


@pytest.mark.parametrize(
    ("baseline_id", "filename", "expected_match", "expected_epoch"),
    [
        ("gamenet", "Epoch_12_JA_0.5100_DDI_0.0850.model", True, 12),
        ("gamenet", "Epoch_12_TARGET_0.4000_JA_0.5100_DDI_0.0850.model", False, None),
        ("safedrug", "Epoch_45_TARGET_0.3500_JA_0.5200_DDI_0.0600.model", True, 45),
        ("safedrug", "Epoch_45_JA_0.5200_DDI_0.0600.model", False, None),
        ("retain", "Epoch_30_JA_0.4900_DDI_0.0830.model", True, 30),
        ("leap-safedrug", "Epoch_15_JA_0.4500_DDI_0.0730.model", True, 15),
    ],
)
def test_checkpoint_regexes_match_expected_patterns(
    baseline_id: str, filename: str, expected_match: bool, expected_epoch: int | None
) -> None:
    profile = adapter.PROFILES[baseline_id]
    match = profile.checkpoint_pattern.fullmatch(filename)
    if expected_match:
        assert match is not None
        assert int(match.group(1)) == expected_epoch
    else:
        assert match is None


@pytest.mark.parametrize("lr", [1e-5, 1e-4, 5e-4])
def test_learning_rate_adaptation_is_exact_and_reversible(lr: float) -> None:
    source = "optimizer = Adam(model.parameters(), lr=5e-4)\n"
    adapted = adapter.adapt_learning_rate_source(source, lr)
    if lr == 5e-4:
        assert adapted == source
    else:
        lr_str = adapter._format_lr(lr)
        assert f"lr={lr_str}" in adapted
        reverted = adapter.adapt_learning_rate_source(adapted, 5e-4, original_lr=lr)
        assert reverted == source


def test_profiles_include_candidate_learning_rates() -> None:
    assert adapter.PROFILES["safedrug-lr-1e-5"].learning_rate == 1e-5
    assert adapter.PROFILES["safedrug-lr-1e-4"].learning_rate == 1e-4
    assert adapter.PROFILES["safedrug-lr-5e-4"].learning_rate == 5e-4


def test_program_probe_and_execute_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_calls = []

    def mock_run_probe(*args: Any, **kwargs: Any) -> dict[str, Any]:
        probe_calls.append((args, kwargs))
        return {"kind": "safedrug_archived_probe", "status": "ok"}

    monkeypatch.setattr(adapter, "run_probe", mock_run_probe)

    probe_result = adapter.probe(
        {
            "baseline_id": "safedrug",
            "upstream_root": str(tmp_path / "upstream"),
            "dataset_root": str(tmp_path / "data"),
            "scope": "environment",
        }
    )
    assert probe_result["kind"] == "safedrug_archived_probe"
    assert len(probe_calls) == 1

    smoke_calls = []

    def mock_run_smoke(*args: Any, **kwargs: Any) -> None:
        smoke_calls.append((args, kwargs))

    monkeypatch.setattr(adapter, "run_smoke_lane", mock_run_smoke)

    execute_result = adapter.execute(
        {
            "mode": "smoke",
            "baseline_id": "safedrug",
            "upstream_root": str(tmp_path / "upstream"),
            "dataset_root": str(tmp_path / "data"),
            "run_root": str(tmp_path / "run"),
        }
    )
    assert execute_result["state"] == "completed"
    assert execute_result["mode"] == "smoke"
    assert len(smoke_calls) == 1


def test_safedrug_selection_admission_via_execute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from baselines import safedrug_archived_data

    # 1. Active controller identity (selected lane: molerec-safedrug-lr-5e-4)
    active_identity = {
        "attempt_id": "attempt-1",
        "lane_id": "molerec-safedrug-lr-5e-4",
        "scientific_baseline_id": "safedrug",
        "program_id": "safedrug-archived",
        "profile_id": "safedrug",
        "harness_revision": "a" * 40,
        "model_source_revision": adapter.ARCHIVED_REVISION,
        "preprocessing_revision": "c" * 40,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "environment_sha256": "d" * 64,
        "mode": "formal",
        "submission_id": "submission-1",
    }
    monkeypatch.setattr(adapter, "identity_from_environment", lambda mode, **_: active_identity)

    # 2. Upstream tree with entrypoint
    upstream = tmp_path / "upstream"
    upstream_src = upstream / "src"
    upstream_src.mkdir(parents=True)
    (upstream_src / "SafeDrug.py").touch()
    monkeypatch.setattr(adapter, "verify_upstream_source", lambda root: None)

    # 3. Dataset directory with required inputs
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in safedrug_archived_data.CANONICAL_SIX_INPUTS:
        (data_dir / name).touch()

    # 4. Completed training run_root with valid checkpoint and v2 artifacts
    run_root = tmp_path / "run"
    run_root.mkdir()
    checkpoint_file = run_root / "work" / "saved" / f"SafeDrug_{run_root.name}" / "Epoch_49.model"
    checkpoint_file.parent.mkdir(parents=True)
    checkpoint_file.write_bytes(b"checkpoint-evidence")
    checkpoint_sha = hashlib.sha256(b"checkpoint-evidence").hexdigest()

    training_status = {
        "schema_version": 2,
        "kind": "reproduction_status_v2",
        "state": "completed",
        "stage": "terminal",
        "identity": active_identity,
        "mode": "formal",
        "non_evidence": False,
    }
    training_result = {
        "schema_version": 2,
        "kind": "reproduction_result_v2",
        "state": "completed",
        "identity": active_identity,
        "artifact_type": "training",
        "mode": "formal",
        "non_evidence": False,
        "status": training_status,
        "dataset_counts": safedrug_archived_data.EXPECTED_COUNTS,
        "epochs_requested": 50,
        "epochs_observed": 50,
        "checkpoint": {
            "best_epoch": 49,
            "relative_path": str(checkpoint_file.relative_to(run_root)),
            "sha256": checkpoint_sha,
            "size_bytes": len(b"checkpoint-evidence"),
        },
    }
    (run_root / "status.json").write_text(json.dumps(training_status), encoding="utf-8")
    (run_root / "result.json").write_text(json.dumps(training_result), encoding="utf-8")
    (run_root / "finalization.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "reproduction_finalization",
                "status": "finalized",
                "identity": active_identity,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        adapter,
        "environment_summary",
        lambda: {"conda_explicit_sha256": active_identity["environment_sha256"]},
    )

    # 5. Generate selection.json using core selector
    selection_path, valid_selection = _write_test_selection_artifact(tmp_path / "selection.json")

    # 6. Mock ONLY lower-level work after admission so no scientific workload runs
    executed_commands: list[list[str]] = []

    def mock_run_logged(cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
        executed_commands.append(cmd)
        metric_line = (
            "DDI Rate: 0.1, Jaccard: 0.2, PRAUC: 0.3, AVG_PRC: 0.4, "
            "AVG_RECALL: 0.5, AVG_F1: 0.6, AVG_MED: 7.0"
        )
        summary_line = (
            "0.1000 $\\pm$ 0.0000 & 0.2000 $\\pm$ 0.0000 & "
            "0.6000 $\\pm$ 0.0000 & 0.3000 $\\pm$ 0.0000 & 7.0000 $\\pm$ 0.0000 &"
        )
        log_path.write_text("\n".join([metric_line] * 10 + [summary_line]), encoding="utf-8")

    monkeypatch.setattr(adapter, "run_logged", mock_run_logged)

    # Positive test: genuine Program-side admission through execute(request)
    base_request = {
        "mode": "formal",
        "phase": "test",
        "baseline_id": "safedrug",
        "upstream_root": str(upstream),
        "dataset_root": str(data_dir),
        "run_root": str(run_root),
        "selection_path": str(selection_path),
        "test_root": str(tmp_path / "test_success"),
    }
    result = adapter.execute(base_request)
    assert result["state"] == "completed"
    assert result["phase"] == "test"
    assert len(executed_commands) == 1
    assert "--Test" in executed_commands[0]
    assert "--resume_path" in executed_commands[0]

    # Negative 1: Missing selection_path rejected during execute
    req_missing_selection = dict(
        base_request,
        selection_path=None,
        test_root=str(tmp_path / "test_missing_selection"),
    )
    with pytest.raises(adapter.ReproductionError, match=r"requires selection\.json"):
        adapter.execute(req_missing_selection)

    # Negative 2: Unselected lane rejected during execute
    unselected_identity = {**active_identity, "lane_id": "molerec-safedrug-lr-1e-5"}
    unselected_run = tmp_path / "run_unselected"
    unselected_run.mkdir()
    unselected_ckpt = (
        unselected_run / "work" / "saved" / f"SafeDrug_{unselected_run.name}" / "Epoch_49.model"
    )
    unselected_ckpt.parent.mkdir(parents=True)
    unselected_ckpt.write_bytes(b"checkpoint-evidence-1e5")
    unselected_status = dict(training_status, identity=unselected_identity)
    unselected_result = dict(
        training_result,
        identity=unselected_identity,
        status=unselected_status,
        checkpoint={
            "best_epoch": 49,
            "relative_path": str(unselected_ckpt.relative_to(unselected_run)),
            "sha256": hashlib.sha256(b"checkpoint-evidence-1e5").hexdigest(),
            "size_bytes": len(b"checkpoint-evidence-1e5"),
        },
    )
    (unselected_run / "status.json").write_text(json.dumps(unselected_status), encoding="utf-8")
    (unselected_run / "result.json").write_text(json.dumps(unselected_result), encoding="utf-8")
    (unselected_run / "finalization.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "reproduction_finalization",
                "status": "finalized",
                "identity": unselected_identity,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        adapter,
        "identity_from_environment",
        lambda mode, **_: unselected_identity,
    )
    req_unselected = dict(
        base_request,
        run_root=str(unselected_run),
        test_root=str(tmp_path / "test_unselected"),
    )
    with pytest.raises(adapter.ReproductionError, match="does not authorize this lane"):
        adapter.execute(req_unselected)

    # Negative 3: Tampered selection with leaked test_metrics rejected during execute
    monkeypatch.setattr(
        adapter,
        "identity_from_environment",
        lambda mode, **_: active_identity,
    )
    invalid_selection = json.loads(json.dumps(valid_selection))
    invalid_selection["candidates"][0]["test_metrics"] = {"jaccard": 0.9}
    invalid_path = tmp_path / "invalid_selection.json"
    invalid_path.write_text(json.dumps(invalid_selection), encoding="utf-8")
    req_tampered = dict(
        base_request,
        selection_path=str(invalid_path),
        test_root=str(tmp_path / "test_tampered"),
    )
    with pytest.raises(adapter.ReproductionError, match="invalid candidate evidence"):
        adapter.execute(req_tampered)


def test_safedrug_cli_main_dispatches_probe_and_execute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    run_root = tmp_path / "run"
    run_root.mkdir()

    probe_calls = []
    execute_calls = []

    def mock_probe(req):
        probe_calls.append(req)
        return {"kind": "safedrug_probe", "status": "ok"}

    def mock_execute(req):
        execute_calls.append(req)
        return {"state": "completed", "mode": req["mode"]}

    monkeypatch.setattr(adapter, "probe", mock_probe)
    monkeypatch.setattr(adapter, "execute", mock_execute)

    # 1. Main dispatches probe
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "SafeDrug.py",
            "safedrug",
            "--upstream-root",
            str(upstream),
            "--dataset-root",
            str(data_dir),
            "--mode",
            "probe",
            "--scope",
            "environment",
        ],
    )
    adapter.main()
    assert len(probe_calls) == 1
    assert probe_calls[0]["baseline_id"] == "safedrug"
    captured = capsys.readouterr()
    assert "safedrug_probe" in captured.out

    # 2. Main dispatches execute (smoke)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "SafeDrug.py",
            "safedrug",
            "--upstream-root",
            str(upstream),
            "--dataset-root",
            str(data_dir),
            "--run-root",
            str(run_root),
            "--mode",
            "smoke",
        ],
    )
    adapter.main()
    assert len(execute_calls) == 1
    assert execute_calls[0]["baseline_id"] == "safedrug"
    assert execute_calls[0]["mode"] == "smoke"


def test_safedrug_parser_supports_probe_scope_and_modes() -> None:
    parser = adapter.build_parser()
    args = parser.parse_args(
        [
            "safedrug",
            "--upstream-root",
            "/path/to/upstream",
            "--dataset-root",
            "/path/to/dataset",
            "--mode",
            "probe",
            "--probe-scope",
            "full",
        ]
    )
    assert args.baseline_id == "safedrug"
    assert args.mode == "probe"
    assert args.scope == "full"
    assert str(args.upstream_root) == "/path/to/upstream"
    assert str(args.dataset_root) == "/path/to/dataset"


def test_safedrug_program_execute_recovery_dispatches_to_recover_formal_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "data"
    dataset.mkdir()
    run = tmp_path / "run"
    run.mkdir()
    expected_marker = run / "recoveries" / "finalizer-1"

    calls = []

    def mock_recover_formal_lane(
        *,
        profile: Any,
        data_dir: Path,
        run_root: Path,
        recovery_id: str,
        finalizer_revision: str,
    ) -> Path:
        calls.append(
            {
                "profile": profile,
                "data_dir": data_dir,
                "run_root": run_root,
                "recovery_id": recovery_id,
                "finalizer_revision": finalizer_revision,
            }
        )
        return expected_marker

    monkeypatch.setattr(adapter, "recover_formal_lane", mock_recover_formal_lane)

    request = {
        "mode": "recovery",
        "baseline_id": "retain",
        "dataset_root": str(dataset),
        "run_root": str(run),
        "recovery_id": "finalizer-1",
        "finalizer_revision": "e" * 40,
    }

    result = adapter.execute(request)

    assert result == {
        "state": "completed",
        "mode": "recovery",
        "marker_path": str(expected_marker),
    }
    assert len(calls) == 1
    call = calls[0]
    assert call["profile"].baseline_id == "retain"
    assert call["data_dir"] == dataset
    assert call["run_root"] == run
    assert call["recovery_id"] == "finalizer-1"
    assert call["finalizer_revision"] == "e" * 40
