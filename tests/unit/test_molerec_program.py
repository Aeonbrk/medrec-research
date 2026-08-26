from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROGRAM_PATH = Path(__file__).parents[2] / "baselines" / "molerec.py"
SPEC = importlib.util.spec_from_file_location("molerec_program", PROGRAM_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def valid_records_and_vocab() -> tuple[
    list[list[list[list[int]]]],
    dict[str, object],
    list[list[int]],
    list[list[int]],
]:
    diag_words = [f"D{i}" for i in range(128)]
    pro_words = [f"P{i}" for i in range(50)]
    med_words = [f"M{i}" for i in range(131)]

    # Patient 0: 2 admissions
    p0_adm1 = [list(range(128)), list(range(50)), list(range(65))]
    p0_adm2 = [list(range(64)), list(range(25)), list(range(32))]
    records = [[p0_adm1, p0_adm2]]

    # 5466 patients with 2 admissions
    for i in range(5466):
        adm1 = [list(range(13)), list(range(5)), list(range(14))]
        adm2 = [list(range(13, 25)), list(range(5, 9)), list(range(14, 27))]
        if i < 587:
            adm2[1] = list(range(5, 10))
        if i < 412:
            adm2[2] = list(range(14, 28))
        records.append([adm1, adm2])

    # 882 patients with 2 admissions
    for _ in range(882):
        adm1 = [list(range(12)), list(range(5)), list(range(14))]
        adm2 = [list(range(12, 24)), list(range(5, 9)), list(range(14, 27))]
        records.append([adm1, adm2])

    # 1 patient with 2334 visits
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
    for row, column in list(pairs)[:448]:
        ddi[row][column] = ddi[column][row] = 1
    ddi_mask = [[0] * 491 for _ in range(131)]
    return records, vocabulary, ddi, ddi_mask


def test_molerec_profiles_match_entrypoints_and_defaults() -> None:
    observed = {
        baseline_id: (profile.entrypoint, profile.model_name, profile.learning_rate)
        for baseline_id, profile in adapter.PROFILES.items()
    }
    assert observed == {
        "molerec": ("main.py", "MoleRec", 5e-4),
        "molerec-embedding": ("main.py", "MoleRec", 5e-4),
    }
    assert adapter.PROFILES["molerec"].required_inputs == adapter.COMMON_INPUTS
    assert adapter.COMMON_INPUTS == (
        "records_final.pkl",
        "voc_final.pkl",
        "ddi_A_final.pkl",
        "ehr_adj_final.pkl",
        "ddi_mask_H.pkl",
        "substructure_smiles.pkl",
        "idx2SMILES.pkl",
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


def test_epoch_adaptation_is_exact_and_reversible() -> None:
    source = f"def main():\n{adapter.EPOCH_FORMAL}    pass\n"
    adapted = adapter.adapt_epoch_source(source)

    assert adapter.EPOCH_FORMAL not in adapted
    assert adapted.count(adapter.EPOCH_SMOKE) == 1
    assert adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1) == source


def test_smoke_adaptation_composes_cleanly_and_reversibly() -> None:
    source = f"{adapter.TEST_DECLARATION}\ndef main():\n{adapter.EPOCH_FORMAL}    pass\n"
    adapted = adapter.adapt_smoke_source(source)

    assert adapter.TEST_DECLARATION not in adapted
    assert adapter.EPOCH_FORMAL not in adapted
    assert adapter.TRAIN_DECLARATION in adapted
    assert adapter.EPOCH_SMOKE in adapted


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


def test_count_dataset_returns_expected_canonical_counts() -> None:
    records, vocab, ddi, ddi_mask = valid_records_and_vocab()
    counts = adapter.count_dataset(records, vocab, ddi, ddi_mask)

    assert counts == {
        "patients": 6350,
        "visits": 15032,
        "medications": 131,
        "ddi_pairs": 448,
        "molecular_substructures": 491,
    }


def test_validate_binary_symmetric_matrix_rejects_asymmetry() -> None:
    ddi = [[0] * 131 for _ in range(131)]
    ddi[0][1] = 1
    ddi[1][0] = 0

    with pytest.raises(adapter.ReproductionError, match="asymmetric"):
        adapter._validate_binary_symmetric_matrix(ddi, 131)


def test_validate_records_statistics_rejects_invalid_counts() -> None:
    records = [[[list(range(5)), list(range(5)), list(range(5))]]]

    with pytest.raises(adapter.ReproductionError, match="mismatch"):
        adapter._validate_records_statistics(records)


def test_parse_training_log_extracts_best_epoch() -> None:
    log_text = "\n".join([f"epoch {i}\nloss: 0.1\nbest_epoch: {min(i, 42)}" for i in range(50)])
    best_epoch = adapter.parse_training_log(log_text, expected_epochs=50)
    assert best_epoch == 42


def test_parse_test_log_extracts_metrics() -> None:
    log_text = """
    Evaluation Results:
    DDI Rate: 0.0654
    Jaccard: 0.5230
    PRAUC: 0.7712
    F1-score: 0.6840
    AVG_MED: 19.45
    """
    parsed = adapter.parse_test_log(log_text)
    metrics = parsed["metrics"]
    assert metrics["ddi_rate"] == 0.0654
    assert metrics["ja"] == 0.5230
    assert metrics["prauc"] == 0.7712
    assert metrics["f1"] == 0.6840
    assert metrics["med"] == 19.45


def test_parse_formal_test_log_recomputes_ten_round_population_summary() -> None:
    rounds = "\n".join(
        (
            f"DDI Rate: {0.10 + index / 100:.2f}, "
            f"Jaccard: {0.40 + index / 100:.2f}, "
            f"PRAUC: {0.60 + index / 100:.2f}, "
            f"AVG_PRC: {0.20 + index / 100:.2f}, "
            f"AVG_RECALL: {0.30 + index / 100:.2f}, "
            f"AVG_F1: {0.50 + index / 100:.2f}, "
            f"AVG_MED: {20 + index:.2f}"
        )
        for index in range(10)
    )
    log_text = (
        f"{rounds}\n"
        "0.1450 $\\pm$ 0.0287 & 0.4450 $\\pm$ 0.0287 & "
        "0.5450 $\\pm$ 0.0287 & 0.6450 $\\pm$ 0.0287 & "
        "24.5000 $\\pm$ 2.8723 &\n"
    )

    parsed = adapter.parse_formal_test_log(log_text)

    assert len(parsed["rounds"]) == 10
    assert parsed["harness_summary"]["jaccard"] == pytest.approx(
        {"mean": 0.445, "std": 0.028722813232690143}
    )
    assert parsed["upstream_summary"]["avg_medications"] == {
        "mean": 24.5,
        "std": 2.8723,
    }


def test_select_checkpoint_finds_exact_epoch(tmp_path: Path) -> None:
    profile = adapter.PROFILES["molerec"]
    (tmp_path / "Epoch_10_TARGET_0.30_JA_0.50_DDI_0.07.model").touch()
    (tmp_path / "Epoch_25_TARGET_0.28_JA_0.53_DDI_0.06.model").touch()
    (tmp_path / "Epoch_40_TARGET_0.31_JA_0.51_DDI_0.07.model").touch()

    selected = adapter.select_checkpoint(tmp_path, profile, best_epoch=25)
    assert selected.name == "Epoch_25_TARGET_0.28_JA_0.53_DDI_0.06.model"


def test_split_responsibility_modules_importable() -> None:
    from baselines import (
        molerec_contract,
        molerec_data,
        molerec_logs,
        molerec_probe,
        molerec_runner,
    )

    assert molerec_contract.ARCHIVED_REVISION == adapter.ARCHIVED_REVISION
    assert hasattr(molerec_data, "load_and_validate_canonical_inputs")
    assert hasattr(molerec_logs, "parse_training_log")
    assert hasattr(molerec_probe, "run_probe")
    assert hasattr(molerec_runner, "run_formal_lane")
