"""Command-line entry points for public protocol workflows."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from ._validation import (
    content_sha256,
    parse_json_object,
    require_public_string,
    require_single_line_public_string,
    strict_fields,
    write_json_atomic,
)
from .action_gate import (
    ActionRequestInput,
    AuthorityBundle,
    evaluate_action,
    resolve_action_context,
)
from .baseline_audit import AuditReviewSet, BaselineAudit, BaselineProgram
from .benchmark_program import (
    SelectionAcceptance,
    SelectionDiagnostic,
    SelectionResult,
    SelectionSpecification,
)
from .benchmark_state import (
    ComparisonScope,
    HumanReviewRecord,
    LiveBenchmarkAuthority,
    program_registry_authority_sha256,
)
from .dataset import DatasetManifest
from .errors import ProtocolValidationError
from .evaluation import evaluate_predictions
from .harness import create_harness_server
from .prediction import PredictionRecord
from .project_status import ProjectStatus, publish_medrec_status
from .reference import ReferenceConfig, run_reference_slice
from .registry import BaselineRegistry
from .reproduction_characterization import ReproductionCharacterization
from .reproduction_contract import (
    DecisionPacket,
    H1Approval,
    H2Decision,
    SafeDrugBatchContract,
)
from .research_loop_status import ResearchLoopStatus
from .run_record import ArtifactChecksum, RunParameter, RunRecord

Clock = Callable[[], datetime]


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _nonnegative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return parsed


def _port(value: str) -> int:
    parsed = _nonnegative_integer(value)
    if parsed > 65535:
        raise argparse.ArgumentTypeError("must be an integer between 0 and 65535")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="medrec-research")
    commands = parser.add_subparsers(dest="command", required=True)
    reference = commands.add_parser("reference")
    reference.add_argument("--manifest", type=Path, required=True)
    reference.add_argument("--visits", type=Path, required=True)
    reference.add_argument("--output", type=Path, required=True)
    reference.add_argument("--top-k", type=_positive_integer, default=2)
    reference.add_argument("--seed", type=_nonnegative_integer, default=0)
    reference.set_defaults(handler=_reference)
    acceptance = commands.add_parser("accept-comparison")
    acceptance.add_argument("--manifest", type=Path, required=True)
    acceptance.add_argument("--registry", type=Path, required=True)
    acceptance.add_argument("--baseline-id", required=True)
    acceptance.add_argument("--predictions", type=Path, required=True)
    acceptance.add_argument("--medication-vocabulary", type=Path, required=True)
    acceptance.add_argument("--membership-hmac-key", type=Path)
    acceptance.add_argument("--run-config", type=Path, required=True)
    acceptance.add_argument("--adaptation-budget", type=Path, required=True)
    acceptance.add_argument("--artifact", action="append", default=[], metavar="NAME=PATH")
    acceptance.add_argument("--output", type=Path, required=True)
    acceptance.set_defaults(handler=_accept_comparison_command)

    audit = commands.add_parser("audit-validate")
    _add_program_audits(audit)
    audit.set_defaults(handler=_audit_validate)

    selection = commands.add_parser("selection-publish")
    _add_program_audits(selection)
    selection.add_argument("--registry", type=Path, required=True)
    selection.add_argument("--reviews", type=Path, required=True)
    selection.add_argument("--scope", type=Path, required=True)
    selection.add_argument("--diagnostics", type=Path, required=True)
    selection.add_argument("--output", type=Path, required=True)
    selection.set_defaults(handler=_selection_publish)

    status = commands.add_parser("status-publish")
    _add_program_audits(status)
    status.add_argument("--registry", type=Path, required=True)
    status.add_argument("--reviews", type=Path, required=True)
    status.add_argument("--selection", type=Path, required=True)
    status.add_argument("--selection-acceptance", type=Path)
    status.add_argument("--scope", type=Path, required=True)
    status.add_argument("--human-review", type=Path)
    status.add_argument("--characterization", type=Path)
    status.add_argument("--output", type=Path, required=True)
    status.set_defaults(handler=_status_publish)

    action_context = commands.add_parser("action-context")
    action_context.add_argument("--status", type=Path, required=True)
    action_context.add_argument("--authority-bundle", type=Path)
    action_context.add_argument("--output", type=Path, required=True)
    action_context.set_defaults(handler=_action_context)

    action = commands.add_parser("action-evaluate")
    action.add_argument("--request", type=Path, required=True)
    action.add_argument("--status", type=Path, required=True)
    action.add_argument("--authority-bundle", type=Path)
    action.add_argument("--output", type=Path, required=True)
    action.set_defaults(handler=_action_evaluate)

    harness = commands.add_parser("harness")
    harness.add_argument("--status", type=Path, required=True)
    harness.add_argument("--authority-bundle", type=Path)
    harness.add_argument("--research-loop", type=Path)
    harness.add_argument("--port", type=_port, default=0)
    harness.set_defaults(handler=_serve_harness)

    reproduction = commands.add_parser(
        "validate-reproduction",
        aliases=["reproduction-validate"],
    )
    reproduction.add_argument("--contract", type=Path, required=True)
    reproduction.add_argument("--packet", type=Path, required=True)
    reproduction.add_argument("--h1", type=Path)
    reproduction.add_argument("--h2", type=Path)
    reproduction.add_argument("--output", type=Path, required=True)
    reproduction.set_defaults(handler=_validate_reproduction)

    loop = commands.add_parser("validate-research-loop")
    loop.add_argument("--status", type=Path, required=True)
    loop.add_argument("--output", type=Path, required=True)
    loop.set_defaults(handler=_validate_research_loop)
    return parser


def _add_program_audits(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)


def _system_clock() -> datetime:
    return datetime.now(UTC)


def _write_json_atomic(path: Path, value: object) -> None:
    write_json_atomic(path, value)


def _load_program_audits(
    arguments: argparse.Namespace,
) -> tuple[BaselineProgram, tuple[BaselineAudit, ...]]:
    program = BaselineProgram.load(arguments.program)
    audits = tuple(
        BaselineAudit.load(arguments.audit_dir / f"{candidate_id}.toml")
        for candidate_id in program.candidate_ids
    )
    program.validate_audits(audits)
    return program, audits


def _load_diagnostics(path: Path) -> tuple[SelectionDiagnostic, ...]:
    payload = strict_fields(
        parse_json_object(path.read_text(encoding="utf-8"), context="selection diagnostics"),
        required=("schema_version", "kind", "diagnostics"),
        context="selection diagnostics",
    )
    if payload["schema_version"] != 1 or payload["kind"] != "selection_diagnostics":
        raise ProtocolValidationError("selection diagnostics must use schema version 1")
    diagnostics = payload["diagnostics"]
    if not isinstance(diagnostics, list):
        raise ProtocolValidationError("selection diagnostics must be a list")
    return tuple(SelectionDiagnostic.from_dict(item) for item in diagnostics)


def _canonical_vocabulary(path: Path) -> tuple[tuple[str, ...], str]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProtocolValidationError("medication vocabulary must be UTF-8") from error
    codes = tuple(
        require_single_line_public_string(code, field="medication_vocabulary")
        for code in text.splitlines()
    )
    canonical = "".join(f"{code}\n" for code in sorted(codes))
    if not codes or len(codes) != len(set(codes)) or text != canonical:
        raise ProtocolValidationError(
            "medication vocabulary must be canonical sorted unique codes with trailing newlines"
        )
    return codes, sha256(raw).hexdigest()


def _artifact_argument(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator:
        raise ProtocolValidationError("artifact must use NAME=PATH")
    return require_public_string(name, field="artifact.name"), Path(raw_path)


def _accept_comparison(arguments: argparse.Namespace) -> RunRecord:
    manifest = DatasetManifest.load(arguments.manifest)
    registry = BaselineRegistry.load(arguments.registry)
    try:
        baseline = registry.get(arguments.baseline_id)
    except KeyError as error:
        raise ProtocolValidationError(
            f"baseline is not registered: {arguments.baseline_id}"
        ) from error

    vocabulary, vocabulary_sha256 = _canonical_vocabulary(arguments.medication_vocabulary)
    if vocabulary_sha256 != manifest.medication_vocabulary_sha256:
        raise ProtocolValidationError(
            "medication vocabulary checksum does not match Dataset Manifest"
        )
    vocabulary_set = set(vocabulary)

    prediction_bytes = arguments.predictions.read_bytes()
    try:
        prediction_text = prediction_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProtocolValidationError("Prediction Records must be UTF-8 JSON") from error
    prediction_payload = strict_fields(
        parse_json_object(prediction_text, context="Prediction Records"),
        required=("schema_version", "predictions"),
        context="Prediction Records",
    )
    if prediction_payload["schema_version"] != 1:
        raise ProtocolValidationError("Prediction Records schema_version must be 1")
    raw_predictions = prediction_payload["predictions"]
    if not isinstance(raw_predictions, list):
        raise ProtocolValidationError("Prediction Records predictions must be a list")
    predictions = tuple(PredictionRecord.from_dict(item) for item in raw_predictions)
    if any(
        not set((*record.target_medications, *record.predicted_medications)) <= vocabulary_set
        for record in predictions
    ):
        raise ProtocolValidationError(
            "Prediction Records contain medications outside the declared vocabulary"
        )
    evaluation = evaluate_predictions(predictions)
    membership_hmac_key = (
        arguments.membership_hmac_key.read_bytes()
        if arguments.membership_hmac_key is not None
        else None
    )
    evaluation_visit_membership_digest = manifest.verify_evaluation_visits(
        ((record.patient_id, record.visit_id) for record in predictions),
        membership_hmac_key=membership_hmac_key,
    )

    config = strict_fields(
        parse_json_object(
            arguments.run_config.read_text(encoding="utf-8"),
            context="run config",
        ),
        required=(
            "schema_version",
            "protocol_version",
            "seed",
            "selection_split",
            "evaluation_split",
            "parameters",
        ),
        context="run config",
    )
    if config["schema_version"] != 1:
        raise ProtocolValidationError("run config schema_version must be 1")
    raw_parameters = config["parameters"]
    if not isinstance(raw_parameters, list):
        raise ProtocolValidationError("run config parameters must be a list")
    parameters = tuple(RunParameter.from_dict(item) for item in raw_parameters)

    budget_bytes = arguments.adaptation_budget.read_bytes()
    if not budget_bytes:
        raise ProtocolValidationError("adaptation budget artifact must not be empty")
    artifacts = [ArtifactChecksum("prediction-records", sha256(prediction_bytes).hexdigest())]
    for artifact_argument in arguments.artifact:
        name, path = _artifact_argument(artifact_argument)
        artifacts.append(ArtifactChecksum(name, sha256(path.read_bytes()).hexdigest()))

    return RunRecord.create(
        mode="comparison",
        protocol_version=config["protocol_version"],
        baseline=baseline,
        dataset=manifest,
        seed=config["seed"],
        selection_split=config["selection_split"],
        evaluation_split=config["evaluation_split"],
        parameters=parameters,
        evaluation=evaluation,
        adaptation_budget_sha256=sha256(budget_bytes).hexdigest(),
        artifact_checksums=artifacts,
        evaluation_visit_membership_digest=evaluation_visit_membership_digest,
    )


def _reference(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    del clock
    record = run_reference_slice(
        arguments.manifest,
        arguments.visits,
        config=ReferenceConfig(top_k=arguments.top_k, seed=arguments.seed),
    )
    _write_json_atomic(arguments.output, record.to_dict())
    return 0, record.check_id


def _accept_comparison_command(
    arguments: argparse.Namespace, clock: Clock
) -> tuple[int, str | None]:
    del clock
    record = _accept_comparison(arguments)
    _write_json_atomic(arguments.output, record.to_dict())
    return 0, record.run_id


def _audit_validate(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    del clock
    _, audits = _load_program_audits(arguments)
    digest = content_sha256({"audits": [item.audit_sha256 for item in audits]})
    return 0, digest


def _selection_publish(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    del clock
    program, audits = _load_program_audits(arguments)
    registry = BaselineRegistry.load(arguments.registry)
    scope = ComparisonScope.from_dict(
        parse_json_object(arguments.scope.read_text(encoding="utf-8"), context="ComparisonScope")
    )
    selection = SelectionSpecification().select(
        program,
        audits,
        AuditReviewSet.load(arguments.reviews),
        _load_diagnostics(arguments.diagnostics),
        registry_authority_sha256=program_registry_authority_sha256(program, registry),
        scope_sha256=scope.scope_sha256,
    )
    _write_json_atomic(arguments.output, selection.to_dict())
    return 0, selection.selection_id


def _status_publish(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    program, audits = _load_program_audits(arguments)
    registry = BaselineRegistry.load(arguments.registry)
    scope = ComparisonScope.from_dict(
        parse_json_object(arguments.scope.read_text(encoding="utf-8"), context="ComparisonScope")
    )
    review = (
        HumanReviewRecord.load(arguments.human_review)
        if arguments.human_review is not None
        else None
    )
    authority = LiveBenchmarkAuthority.create(
        program=program,
        audits=audits,
        reviews=AuditReviewSet.load(arguments.reviews),
        registry=registry,
        scope=scope,
        review=review,
        selection=SelectionResult.load(arguments.selection),
    )
    characterization = (
        ReproductionCharacterization.load(arguments.characterization)
        if arguments.characterization is not None
        else None
    )
    selection_acceptance = (
        SelectionAcceptance.load(arguments.selection_acceptance)
        if arguments.selection_acceptance is not None
        else None
    )
    snapshot = publish_medrec_status(
        authority=authority,
        characterization=characterization,
        selection_acceptance=selection_acceptance,
        clock=clock,
    )
    snapshot.write_atomic(arguments.output)
    return 0, snapshot.snapshot_sha256


def _load_action_inputs(
    arguments: argparse.Namespace,
) -> tuple[ProjectStatus, AuthorityBundle | None]:
    snapshot = ProjectStatus.from_json(arguments.status.read_text(encoding="utf-8"))
    bundle = (
        AuthorityBundle.load(arguments.authority_bundle)
        if arguments.authority_bundle is not None
        else None
    )
    return snapshot, bundle


def _action_context(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    snapshot, bundle = _load_action_inputs(arguments)
    context = resolve_action_context(
        snapshot=snapshot,
        authority_bundle=bundle,
        now=clock(),
    )
    _write_json_atomic(arguments.output, context.to_public_dict())
    return 0, context.request_id or context.reason_code


def _action_evaluate(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    request = ActionRequestInput.from_dict(
        parse_json_object(
            arguments.request.read_text(encoding="utf-8"),
            context="ActionRequestInput",
        )
    )
    snapshot, bundle = _load_action_inputs(arguments)
    decision = evaluate_action(
        request=request,
        snapshot=snapshot,
        authority_bundle=bundle,
        now=clock(),
    )
    _write_json_atomic(arguments.output, decision.to_dict())
    identifier = (
        decision.request.request_sha256 if decision.request is not None else decision.reason_code
    )
    return (0 if decision.status == "allowed" else 2), identifier


def _serve_harness(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    snapshot = ProjectStatus.from_json(arguments.status.read_text(encoding="utf-8"))
    server = create_harness_server(
        status_path=arguments.status,
        expected_authorities=snapshot.authorities,
        clock=clock,
        port=arguments.port,
        actions_enabled=arguments.authority_bundle is not None,
        authority_bundle_path=arguments.authority_bundle,
        research_loop_path=arguments.research_loop,
    )
    print(f"http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0, None


def _validate_reproduction(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    del clock
    contract = SafeDrugBatchContract.from_json(arguments.contract.read_text(encoding="utf-8"))
    packet = DecisionPacket.from_json(arguments.packet.read_text(encoding="utf-8"))
    if packet.contract_sha256 != contract.contract_sha256 or not contract.is_current():
        raise ProtocolValidationError("reproduction packet does not match the current contract")
    h1 = (
        H1Approval.from_json(arguments.h1.read_text(encoding="utf-8"))
        if arguments.h1 is not None
        else None
    )
    if h1 is not None and not h1.is_current(contract):
        raise ProtocolValidationError("H1 approval is stale")
    h2 = (
        H2Decision.from_json(arguments.h2.read_text(encoding="utf-8"))
        if arguments.h2 is not None
        else None
    )
    if h2 is not None and not h2.is_current(contract=contract, packet=packet):
        raise ProtocolValidationError("H2 decision is stale")
    payload = {
        "contract": contract.to_dict(),
        "h1": h1.to_dict() if h1 is not None else None,
        "h2": h2.to_dict() if h2 is not None else None,
        "kind": "reproduction_validation",
        "packet": packet.to_dict(),
        "schema_version": 1,
    }
    _write_json_atomic(arguments.output, payload)
    return 0, packet.packet_sha256


def _validate_research_loop(arguments: argparse.Namespace, clock: Clock) -> tuple[int, str | None]:
    del clock
    status = ResearchLoopStatus.from_json(arguments.status.read_text(encoding="utf-8"))
    if not status.is_current or status.stale or not status.h1_current:
        raise ProtocolValidationError("research loop status is stale")
    _write_json_atomic(arguments.output, status.to_dict())
    return 0, status.status_sha256


def main(
    argv: Sequence[str] | None = None,
    *,
    clock: Clock = _system_clock,
) -> int:
    """Run one protocol command and return its process status."""

    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        status, record_id = arguments.handler(arguments, clock)
    except OSError:
        parser.error("input/output operation failed")
    except UnicodeError:
        parser.error("input must be valid UTF-8")
    except ProtocolValidationError as error:
        parser.error(str(error))
    if record_id is not None:
        print(record_id)
    return status


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("main",)
