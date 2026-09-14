#!/usr/bin/env python3
"""Audit the pinned DMGExNet source before any canonical execution.

This prototype intentionally stops before model training when the official
auxiliary aspect matrices cannot satisfy the canonical point-in-time input
budget.  It is an audit and provenance tool, not a replacement DMGExNet model.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_REVISION = "66b32302947e248d9caeb15ee1bfdb13b50cbdce"
OFFICIAL_SOURCE_URL = "https://github.com/pc-star123/DMGExNet"
PAPER_URL = "https://doi.org/10.1002/eng2.70899"


@dataclass(frozen=True)
class AuxiliaryResource:
    """Provenance and point-in-time admissibility of an official input."""

    resource: str
    source_data: str
    construction: str
    uses_medication_labels: bool
    train_only_required: bool
    available_at_inference: bool
    canonical_status: str


@dataclass(frozen=True)
class SourceDefect:
    """A concrete execution defect observed in the pinned source."""

    name: str
    evidence: str
    impact: str


def auxiliary_resources() -> tuple[AuxiliaryResource, ...]:
    """Return the audited provenance table for ``matrix.py`` outputs."""

    construction = (
        "matrix.py allocates one row per patient, loops over every admission, "
        "and sets each code column to one; the row is therefore a whole-patient "
        "union rather than a visit-time feature."
    )
    return (
        AuxiliaryResource(
            resource="diag_new.pkl",
            source_data="records.pkl (all 6,350 patients)",
            construction=f"{construction} Diagnosis channel; shape [6350, 1958].",
            uses_medication_labels=False,
            train_only_required=True,
            available_at_inference=False,
            canonical_status="inadmissible_full_cohort_future_union",
        ),
        AuxiliaryResource(
            resource="pro_new.pkl",
            source_data="records.pkl (all 6,350 patients)",
            construction=f"{construction} Procedure channel; shape [6350, 1430].",
            uses_medication_labels=False,
            train_only_required=True,
            available_at_inference=False,
            canonical_status="inadmissible_full_cohort_future_union",
        ),
        AuxiliaryResource(
            resource="med131_new.pkl",
            source_data="records.pkl (all 6,350 patients)",
            construction=f"{construction} Medication channel; shape [6350, 131].",
            uses_medication_labels=True,
            train_only_required=True,
            available_at_inference=False,
            canonical_status="inadmissible_target_and_future_union",
        ),
    )


def _contains_all(text: str, fragments: tuple[str, ...]) -> bool:
    return all(fragment in text for fragment in fragments)


def audit_matrix_source(matrix_source: str) -> dict[str, Any]:
    """Extract the relevant construction facts without importing upstream code."""

    full_patient_union = _contains_all(
        matrix_source,
        (
            "rows = 6350",
            "for step, input in enumerate(data):",
            "for idx, adm in enumerate(input):",
            "diag[step][j] = 1",
            "pro[step][j] = 1",
            "med[step][j] = 1",
        ),
    )
    output_names = tuple(
        name for name in ("diag_new.pkl", "pro_new.pkl", "med131_new.pkl") if name in matrix_source
    )
    return {
        "full_patient_union": full_patient_union,
        "uses_all_admissions": "for idx, adm in enumerate(input):" in matrix_source,
        "uses_medication_channel": "m = adm[2]" in matrix_source,
        "output_names": output_names,
        "information_budget_violation": full_patient_union,
    }


def audit_model_source(
    model_source: str, main_source: str, *, seed_exists: bool
) -> tuple[SourceDefect, ...]:
    """Report concrete pinned-source defects that block an unchanged run."""

    defects: list[SourceDefect] = []
    if "from seed import set_seed" in main_source and not seed_exists:
        defects.append(
            SourceDefect(
                name="missing_seed_module",
                evidence="DMGExNet_main.py imports seed.set_seed but src/seed.py is absent",
                impact="the official entry point cannot import",
            )
        )
    if 'action="store_true", default=True' in main_source:
        defects.append(
            SourceDefect(
                name="test_mode_default",
                evidence="--Test is store_true with default=True",
                impact="a default invocation skips the 70-epoch training loop",
            )
        )
    if "self.cross_attention(o1, o2)" in model_source:
        defects.append(
            SourceDefect(
                name="cross_attention_arity",
                evidence="CrossBiAttention.forward requires query, key, value",
                impact="the model call supplies only query and key",
            )
        )
    if (
        "nn.Embedding(vocab_size[i], 64)" in model_source
        and "TransformerEncoderLayer(emb_dim" in model_source
    ):
        defects.append(
            SourceDefect(
                name="stream_width_mismatch",
                evidence="stream embeddings are 64-wide while the default Transformer d_model is 128",
                impact="the declared default forward has incompatible tensor widths",
            )
        )
    if "adm[2] = input[idx - 1][2][:]" in model_source:
        defects.append(
            SourceDefect(
                name="in_place_target_mutation",
                evidence="forward overwrites the admission medication list in place",
                impact="current targets can be mutated during evaluation/training",
            )
        )
    if "diag[step]" in model_source and "pro[step]" in model_source and "med[step]" in model_source:
        defects.append(
            SourceDefect(
                name="global_aspect_rows",
                evidence="forward consumes patient-indexed auxiliary rows",
                impact="matrix.py rows are not point-in-time visit features",
            )
        )
    return tuple(defects)


def _git_revision(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def audit_official_source(root: Path) -> dict[str, Any]:
    """Produce a public-safe audit report for one official-source checkout."""

    root = root.resolve()
    model_path = root / "src" / "DMGExNet_models.py"
    main_path = root / "src" / "DMGExNet_main.py"
    matrix_path = root / "data" / "matrix.py"
    model_source = model_path.read_text(encoding="utf-8") if model_path.exists() else ""
    main_source = main_path.read_text(encoding="utf-8") if main_path.exists() else ""
    matrix_source = matrix_path.read_text(encoding="utf-8") if matrix_path.exists() else ""
    resources = auxiliary_resources()
    matrix_audit = audit_matrix_source(matrix_source)
    defects = audit_model_source(
        model_source,
        main_source,
        seed_exists=(root / "src" / "seed.py").exists(),
    )
    source_revision = _git_revision(root)
    resource_files_present = {
        resource.resource: (root / "data" / "data_new" / resource.resource).exists()
        for resource in resources
    }
    information_budget_mismatch = bool(
        matrix_audit["information_budget_violation"]
        and any(resource.uses_medication_labels for resource in resources)
    )
    return {
        "schema_version": 1,
        "official_source": OFFICIAL_SOURCE_URL,
        "paper": PAPER_URL,
        "expected_source_revision": EXPECTED_SOURCE_REVISION,
        "source_revision": source_revision,
        "source_revision_verified": source_revision == EXPECTED_SOURCE_REVISION,
        "resource_files_present": resource_files_present,
        "matrix_source": matrix_audit,
        "auxiliary_resources": [asdict(resource) for resource in resources],
        "source_execution_sanity": {
            "status": "blocked_by_pinned_source_execution_defects" if defects else "not_run",
            "defects": [asdict(defect) for defect in defects],
        },
        "official_training_defaults": {
            "epochs": 70,
            "learning_rate": 5e-4,
            "embedding_dimension": 128,
            "attention_heads": 4,
            "target_ddi": 0.05,
            "kp": 0.05,
            "a": 0.9,
            "run_status": "not_started_after_information_budget_gate",
        },
        "official_objective": {
            "base_loss": "0.95 * BCE + 0.05 * multilabel_margin",
            "conditional_ddi_loss": "used when current predicted DDI rate exceeds target_ddi",
            "similarity_explanation_loss": "mixed with the base/DDI branch using a=0.9",
            "simplified_for_canonical_run": False,
        },
        "official_inference_policy": {
            "activation": "sigmoid",
            "threshold": 0.5,
            "same_k_diagnostic": "not run",
            "molerec_k_diagnostic": "not run",
        },
        "fidelity_checks": {
            "diagnosis_procedure_streams_separate": "source_inspected_not_executed",
            "longitudinal_visit_order": "source_inspected_not_executed",
            "cross_stream_attention_directions": "source_inspected_bidirectional_not_executed",
            "historical_medications_temporally_aligned": "source_mutates_target_and_not_executed",
            "drug_graph_vocabulary_131_alignment": "not_executed_after_information_budget_gate",
            "train_only_ehr_graph": "not_executed_after_information_budget_gate",
            "dev_prescriptions_excluded_from_graphs": "not_executed_after_information_budget_gate",
            "cuda_finite_forward_backward": "not_executed_after_information_budget_gate",
            "deterministic_seed_plumbing": "source_seed_module_missing",
        },
        "drug_graph_contract": {
            "required_resources": ["ehr_adj", "ddi_adj", "ddi_mask_H", "idx2drug"],
            "required_medication_count": 131,
            "canonical_index_assertion": "not executed because information budget gate failed",
        },
        "implementation_fidelity": "DMGEXNET_ADAPTATION_FIDELITY_UNRESOLVED",
        "canonical_performance": None,
        "terminal_verdict": (
            "DMGEXNET_INFORMATION_BUDGET_MISMATCH"
            if information_budget_mismatch
            else "DMGEXNET_SOURCE_REPRO_MISMATCH"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_official_source(args.official_root)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.resolve().write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
