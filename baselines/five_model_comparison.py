#!/usr/bin/env python3
"""Run one fail-fast five-model Comparison qualification on 319."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import subprocess
from pathlib import Path

from medrec_research import (
    AdaptationBudget,
    ComparisonProtocolPacket,
    ComparisonProtocolV1_1,
    ComparisonQualification,
    ComparisonQualificationAttempt,
    ComparisonScope,
    DatasetManifest,
    DecoderClass,
    DecoderProfile,
    ProcessPredictionAdapter,
    QualificationGateResult,
    QualificationGateState,
    ReadinessEvidence,
    ReadinessGate,
    ThresholdSelectionRule,
    evaluate_comparison_predictions,
    join_comparison_targets,
)
from medrec_research._validation import canonical_json, content_sha256, write_json_atomic
from medrec_research.comparison_protocol import QUALIFICATION_GATE_ORDER

METHODS = ("retain", "leap-safedrug", "gamenet", "safedrug", "molerec")
SAFE_DRUG_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(path: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return completed.stdout.strip()


def _source_identity(method_id: str, safe_root: Path, molerec_root: Path) -> dict[str, object]:
    if method_id == "molerec":
        if _git_revision(molerec_root) != MOLEREC_REVISION:
            raise ValueError("MoleRec source revision drift")
        files = (
            "src/modules/MoleRec.py",
            "src/modules/SetTransformer.py",
            "src/modules/gnn/GNNs.py",
            "src/modules/gnn/GNNConv.py",
        )
        return {
            "revision": MOLEREC_REVISION,
            "source_files": {name: _file_sha256(molerec_root / name) for name in files},
        }
    if _git_revision(safe_root) != SAFE_DRUG_REVISION:
        raise ValueError("SafeDrug archived source revision drift")
    return {
        "revision": SAFE_DRUG_REVISION,
        "source_files": {
            name: _file_sha256(safe_root / name) for name in ("src/models.py", "src/util.py")
        },
    }


def _configuration(method_id: str, checkpoint_sha256: str) -> dict[str, object]:
    shared = {
        "checkpoint_sha256": checkpoint_sha256,
        "numpy_seed": 2048,
        "torch_seed": 1203,
    }
    if method_id == "retain":
        return {**shared, "decoder": "sigmoid-threshold", "threshold": 0.4}
    if method_id == "leap-safedrug":
        return {
            **shared,
            "decoder": "autoregressive-stop-token",
            "maximum_length": 20,
            "score_surface": "mean-native-timestep-probability",
        }
    if method_id == "safedrug":
        return {
            **shared,
            "decoder": "sigmoid-threshold",
            "learning_rate": 0.0005,
            "threshold": 0.5,
        }
    if method_id == "molerec":
        return {
            **shared,
            "decoder": "sigmoid-threshold",
            "dropout": 0.7,
            "embedding": True,
            "threshold": 0.5,
        }
    return {**shared, "decoder": "sigmoid-threshold", "threshold": 0.5}


def _preregistration_sha256(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    model_ids = {model["scientific_baseline_id"] for model in payload["models"]}
    if (
        payload["protocol_version"] != "1.1"
        or model_ids != set(METHODS)
        or payload["selected_safedrug_lane"] != "molerec-safedrug-lr-5e-4"
        or payload["selected_safedrug_learning_rate"] != 0.0005
    ):
        raise ValueError("Comparison preregistration does not match the frozen five-model decision")
    return content_sha256(payload)


def _load_checkpoint_specs(path: Path) -> dict[str, dict[str, str]]:
    specs = json.loads(path.read_text(encoding="utf-8"))
    if set(specs) != set(METHODS):
        raise ValueError("checkpoint specification must cover the five frozen methods")
    for method_id, spec in specs.items():
        checkpoint = Path(spec["path"])
        if _file_sha256(checkpoint) != spec["sha256"]:
            raise ValueError(f"{method_id} checkpoint identity drift")
    return specs


def _adaptation_budget() -> AdaptationBudget:
    return AdaptationBudget(
        max_trials=1,
        max_compute_units=1,
        trials_used=0,
        compute_units_used=0,
        stopping_rule="mechanical adapter only; no Comparison search",
        seed_policy="upstream source defaults",
    )


def _build_packet(args: argparse.Namespace) -> tuple[ComparisonProtocolPacket, dict[str, object]]:
    summary = json.loads((args.staging_root / "public-summary.json").read_text(encoding="utf-8"))
    preregistration_sha256 = _preregistration_sha256(args.preregistration)
    checkpoint_specs = _load_checkpoint_specs(args.checkpoint_spec)
    safe_adapter_sha256 = _file_sha256(args.harness_root / "baselines/safedrug_comparison.py")
    molerec_adapter_sha256 = _file_sha256(args.harness_root / "baselines/molerec_comparison.py")
    profiles = []
    for method_id in METHODS:
        checkpoint_sha256 = checkpoint_specs[method_id]["sha256"]
        configuration = _configuration(method_id, checkpoint_sha256)
        baseline_core_sha256 = content_sha256(
            {
                "checkpoint_sha256": checkpoint_sha256,
                **_source_identity(method_id, args.safedrug_root, args.molerec_root),
            }
        )
        profile_fields: dict[str, object] = {
            "adapter_sha256": (
                molerec_adapter_sha256 if method_id == "molerec" else safe_adapter_sha256
            ),
            "baseline_core_sha256": baseline_core_sha256,
            "configuration_sha256": content_sha256(configuration),
            "ddi_asset_sha256": summary["ddi_asset_sha256"],
            "environment_sha256": args.environment_sha256,
            "feature_availability_sha256": summary["feature_availability_sha256"],
            "method_id": method_id,
            "preregistration_sha256": preregistration_sha256,
        }
        if method_id == "leap-safedrug":
            profile_fields.update(
                decoder_class=DecoderClass.STRUCTURAL_SEQUENCE,
                native_decoder="source autoregressive top-1 with stop tokens and deduplication",
            )
        else:
            threshold = _configuration(method_id, checkpoint_sha256)["threshold"]
            profile_fields.update(
                decoder_class=DecoderClass.SCORE_THRESHOLD,
                native_decoder=f"source sigmoid threshold {threshold}",
                threshold_rule=ThresholdSelectionRule(
                    max_trials=1,
                    trials_used=0,
                    stopping_rule="source-fixed threshold; no Comparison search",
                    seed_policy="upstream source defaults",
                ),
            )
        profiles.append(DecoderProfile(**profile_fields))
    budget = _adaptation_budget()
    protocol = ComparisonProtocolV1_1(
        adaptation_budget=budget,
        decoder_profiles=tuple(profiles),
    )
    scopes = tuple(
        (
            profile.method_id,
            ComparisonScope(
                protocol_version="1.1",
                dataset_manifest_sha256=summary["dataset_manifest_sha256"],
                adaptation_budget_sha256=budget.budget_sha256,
                protocol_amendment_sha256=protocol.protocol_sha256,
                method_profile_sha256=profile.profile_sha256,
            ),
        )
        for profile in profiles
    )
    return (
        ComparisonProtocolPacket(
            dataset_manifest_sha256=summary["dataset_manifest_sha256"],
            preregistration_sha256=preregistration_sha256,
            protocol=protocol,
            method_scopes=scopes,
        ),
        checkpoint_specs,
    )


def _adapter_command(
    args: argparse.Namespace,
    method_id: str,
    checkpoint: Path,
    *,
    smoke: bool,
) -> tuple[str, ...]:
    common = (
        str(args.conda_executable),
        "run",
        "--no-capture-output",
        "-n",
        args.baseline_environment,
        "python",
        str(
            args.harness_root
            / "baselines"
            / ("molerec_comparison.py" if method_id == "molerec" else "safedrug_comparison.py")
        ),
    )
    profile = () if method_id == "molerec" else (method_id,)
    command = (
        *common,
        *profile,
        "--upstream-root",
        str(args.molerec_root if method_id == "molerec" else args.safedrug_root),
        "--dataset-root",
        str(args.dataset_root),
        "--features",
        str(args.staging_root / "features.pkl"),
        "--checkpoint",
        str(checkpoint),
    )
    return (*command, "--smoke") if smoke else command


def _smoke_adapter(
    command: tuple[str, ...],
    *,
    method_id: str,
    dataset_id: str,
    vocabulary: tuple[str, ...],
    stderr_path: Path,
) -> str:
    request = canonical_json({"request": {"dataset_id": dataset_id}, "schema_version": 2})
    with stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(
            command,
            input=request + "\n",
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            timeout=1800,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError("adapter smoke process failed")
    payload = json.loads(completed.stdout)
    if (
        payload.get("schema_version") != 2
        or payload.get("method_id") != method_id
        or len(payload.get("predictions", [])) != 1
    ):
        raise ValueError("adapter smoke output shape is invalid")
    prediction = payload["predictions"][0]
    if (
        any(
            field in prediction
            for field in (
                "ground_truth",
                "labels",
                "split",
                "target_medications",
                "targets",
                "y_true",
            )
        )
        or tuple(item["medication_code"] for item in prediction["vocabulary_scores"]) != vocabulary
    ):
        raise ValueError("adapter smoke output is not target-free full-vocabulary data")
    return content_sha256(
        {
            "method_id": method_id,
            "predicted_count": len(prediction["predicted_medications"]),
            "score_count": len(prediction["vocabulary_scores"]),
        }
    )


def _write_blocked(
    output_root: Path,
    method_id: str,
    failed_gate: str,
    evidence: dict[str, str],
    error: Exception,
) -> None:
    failure_artifact = content_sha256(
        {"error_type": type(error).__name__, "failed_gate": failed_gate, "method_id": method_id}
    )
    attempt = ComparisonQualificationAttempt.blocked(
        method_id=method_id,
        failed_gate=failed_gate,
        evidence_sha256_by_gate=evidence,
        failure_artifact_sha256=failure_artifact,
    )
    write_json_atomic(output_root / "qualification-attempt.json", attempt.to_dict())
    write_json_atomic(
        output_root / "failure-summary.json",
        {
            "error_type": type(error).__name__,
            "failed_gate": failed_gate,
            "method_id": method_id,
        },
    )
    (output_root / "failure-private.txt").write_text(str(error) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method_id", choices=METHODS)
    parser.add_argument("--harness-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--safedrug-root", type=Path, required=True)
    parser.add_argument("--molerec-root", type=Path, required=True)
    parser.add_argument("--checkpoint-spec", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--environment-sha256", required=True)
    parser.add_argument("--core-environment-sha256", required=True)
    parser.add_argument("--conda-executable", type=Path, required=True)
    parser.add_argument("--baseline-environment", default="medrec-molerec-table1")
    parser.add_argument("--bootstrap-seed", type=int, default=1203)
    args = parser.parse_args()
    for field in (
        "harness_root",
        "dataset_root",
        "staging_root",
        "output_root",
        "safedrug_root",
        "molerec_root",
        "checkpoint_spec",
        "preregistration",
        "conda_executable",
    ):
        setattr(args, field, getattr(args, field).resolve())
    args.output_root.mkdir(parents=True, exist_ok=False)

    evidence: dict[str, str] = {}
    failed_gate = QUALIFICATION_GATE_ORDER[0]
    try:
        evidence["environment_lock"] = content_sha256(
            {
                "baseline_environment_sha256": args.environment_sha256,
                "core_environment_sha256": args.core_environment_sha256,
            }
        )
        failed_gate = "adapter_smoke"
        raw_checkpoint_specs = json.loads(args.checkpoint_spec.read_text(encoding="utf-8"))
        checkpoint = Path(raw_checkpoint_specs[args.method_id]["path"])
        features = pickle.load((args.staging_root / "features.pkl").open("rb"))
        vocabulary = tuple(features["medication_vocabulary"])
        evidence["adapter_smoke"] = _smoke_adapter(
            _adapter_command(args, args.method_id, checkpoint, smoke=True),
            method_id=args.method_id,
            dataset_id=features["dataset_id"],
            vocabulary=vocabulary,
            stderr_path=args.output_root / "adapter-smoke.stderr",
        )

        failed_gate = "cohort_identity"
        manifest = DatasetManifest.load(args.staging_root / "dataset-manifest.json")
        target_bundle = pickle.load((args.staging_root / "targets.pkl").open("rb"))
        targets = target_bundle["targets"]
        manifest.verify_evaluation_visits(
            targets,
            membership_hmac_key=(args.staging_root / "membership-hmac.key").read_bytes(),
        )
        evidence["cohort_identity"] = manifest.manifest_sha256
        failed_gate = "adaptation_budget"
        evidence["adaptation_budget"] = _adaptation_budget().budget_sha256
        failed_gate = "core_integrity"
        packet, checkpoint_specs = _build_packet(args)
        profile = packet.protocol.profile_for(args.method_id)
        checkpoint = Path(checkpoint_specs[args.method_id]["path"])
        if packet.protocol.adaptation_budget.budget_sha256 != evidence["adaptation_budget"]:
            raise ValueError("Comparison adaptation budget identity drift")
        evidence["core_integrity"] = profile.baseline_core_sha256
        failed_gate = "deterministic_adapter"
        adapter = ProcessPredictionAdapter(
            _adapter_command(args, args.method_id, checkpoint, smoke=False),
            timeout_seconds=3600,
        )
        batch = adapter.predict_comparison(
            {"dataset_id": features["dataset_id"]},
            method_id=args.method_id,
            expected_visits=targets,
            medication_vocabulary=vocabulary,
        )
        prediction_sha256 = content_sha256(batch.to_dict())
        evidence["deterministic_adapter"] = prediction_sha256
        with (args.output_root / "prediction-batch.pkl").open("wb") as stream:
            pickle.dump(batch, stream, protocol=pickle.HIGHEST_PROTOCOL)

        failed_gate = "independent_evaluation"
        ddi_pairs = pickle.load((args.staging_root / "ddi-pairs.pkl").open("rb"))
        joined = join_comparison_targets(
            batch,
            targets=targets,
            dataset_manifest=manifest,
            membership_hmac_key=(args.staging_root / "membership-hmac.key").read_bytes(),
        )
        packet.protocol.validate_evaluation(profile, joined.evaluation_input)
        evaluation = evaluate_comparison_predictions(
            joined,
            ddi_pairs=ddi_pairs,
            bootstrap_seed=args.bootstrap_seed,
        )
        evaluation_input_sha256 = content_sha256(joined.evaluation_input.to_dict())
        outcomes_sha256 = content_sha256(evaluation.point.to_dict())
        uncertainty_payload = {
            "intervals": {name: interval.to_dict() for name, interval in evaluation.intervals},
            "rounds": [round_result.to_dict() for round_result in evaluation.rounds],
        }
        uncertainty_sha256 = content_sha256(uncertainty_payload)
        evidence["independent_evaluation"] = evaluation_input_sha256
        qualification = ComparisonQualification(
            protocol_version="1.1",
            dataset_manifest_sha256=manifest.manifest_sha256,
            adaptation_budget_sha256=packet.protocol.adaptation_budget.budget_sha256,
            protocol_amendment_sha256=packet.protocol.protocol_sha256,
            method_profile_sha256=profile.profile_sha256,
            evidence=(
                ReadinessEvidence(ReadinessGate.COHORT_IDENTITY, evidence["cohort_identity"]),
                ReadinessEvidence(ReadinessGate.ADAPTATION_BUDGET, evidence["adaptation_budget"]),
                ReadinessEvidence(ReadinessGate.CORE_INTEGRITY, evidence["core_integrity"]),
                ReadinessEvidence(
                    ReadinessGate.DETERMINISTIC_ADAPTER,
                    evidence["deterministic_adapter"],
                ),
                ReadinessEvidence(
                    ReadinessGate.INDEPENDENT_EVALUATION,
                    evidence["independent_evaluation"],
                ),
            ),
        )
        attempt = ComparisonQualificationAttempt(
            method_id=args.method_id,
            gates=tuple(
                QualificationGateResult(
                    gate=gate,
                    state=QualificationGateState.PASSED,
                    artifact_sha256=evidence[gate],
                )
                for gate in QUALIFICATION_GATE_ORDER
            ),
            qualification_sha256=qualification.qualification_sha256,
            evaluation_sha256=evaluation_input_sha256,
            outcomes_sha256=outcomes_sha256,
            uncertainty_sha256=uncertainty_sha256,
        )
        write_json_atomic(args.output_root / "protocol-packet.json", packet.to_dict())
        write_json_atomic(args.output_root / "qualification.json", qualification.to_dict())
        write_json_atomic(args.output_root / "qualification-attempt.json", attempt.to_dict())
        write_json_atomic(args.output_root / "evaluation.json", evaluation.to_dict())
        write_json_atomic(
            args.output_root / "readiness-evidence.json",
            {
                "adapter_revision": profile.adapter_sha256,
                "core_environment_sha256": args.core_environment_sha256,
                "environment_sha256": args.environment_sha256,
                "evidence": [
                    ReadinessEvidence(
                        ReadinessGate.ADAPTER_SMOKE, evidence["adapter_smoke"]
                    ).to_dict(),
                    ReadinessEvidence(
                        ReadinessGate.ENVIRONMENT_LOCK, evidence["environment_lock"]
                    ).to_dict(),
                ],
                "method_id": args.method_id,
            },
        )
        print(
            canonical_json(
                {
                    "attempt_sha256": attempt.attempt_sha256,
                    "method_id": args.method_id,
                    "outcomes": evaluation.point.to_dict(),
                    "qualified": True,
                    "qualification_sha256": qualification.qualification_sha256,
                }
            )
        )
    except Exception as error:
        _write_blocked(args.output_root, args.method_id, failed_gate, evidence, error)
        raise


if __name__ == "__main__":
    main()
