from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "research" / "prototypes" / "dmgexnet-reset" / "audit.py"
)
SPEC = importlib.util.spec_from_file_location("dmgexnet_reset_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def test_matrix_audit_detects_full_patient_union_and_medication_labels() -> None:
    source = """
    rows = 6350
    for step, input in enumerate(data):
        for idx, adm in enumerate(input):
            d = adm[0]
            p = adm[1]
            m = adm[2]
            diag[step][j] = 1
            pro[step][j] = 1
            med[step][j] = 1
    diag_new.pkl pro_new.pkl med131_new.pkl
    """
    result = AUDIT.audit_matrix_source(source)
    assert result["full_patient_union"] is True
    assert result["uses_all_admissions"] is True
    assert result["uses_medication_channel"] is True
    assert result["information_budget_violation"] is True
    assert result["output_names"] == ("diag_new.pkl", "pro_new.pkl", "med131_new.pkl")


def test_provenance_table_marks_medication_as_target_derived() -> None:
    resources = {item.resource: item for item in AUDIT.auxiliary_resources()}
    assert resources["med131_new.pkl"].uses_medication_labels is True
    assert resources["med131_new.pkl"].available_at_inference is False
    assert resources["med131_new.pkl"].train_only_required is True
    assert resources["diag_new.pkl"].uses_medication_labels is False
    assert resources["diag_new.pkl"].available_at_inference is False


def test_pinned_execution_defects_are_reported_without_rewriting_model() -> None:
    model = """
    nn.Embedding(vocab_size[i], 64)
    TransformerEncoderLayer(emb_dim, 4, 4)
    self.cross_attention(o1, o2)
    adm[2] = input[idx - 1][2][:]
    diag[step]; pro[step]; med[step]
    """
    main = 'from seed import set_seed\nparser.add_argument("--Test", action="store_true", default=True)'
    defects = AUDIT.audit_model_source(model, main, seed_exists=False)
    names = {defect.name for defect in defects}
    assert {
        "missing_seed_module",
        "test_mode_default",
        "cross_attention_arity",
        "stream_width_mismatch",
        "in_place_target_mutation",
        "global_aspect_rows",
    } <= names
