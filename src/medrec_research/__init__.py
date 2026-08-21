"""Public interfaces for the MedRec Research Library."""

from .adapters import (
    AdapterError,
    AdapterLaunchError,
    AdapterProcessError,
    AdapterProtocolError,
    AdapterTimeoutError,
    PredictionAdapter,
    ProcessPredictionAdapter,
)
from .comparison_protocol import (
    AdaptationBudget,
    ComparisonMethodProfile,
    ComparisonProfile,
    ComparisonProtocolV1_1,
    DecoderClass,
    DecoderProfile,
    IndependentEvaluationInput,
    ProtocolV1_1,
    SelectionSplit,
    ThresholdSelectionRule,
)
from .comparison_scope import ComparisonScope
from .dataset import (
    DatasetManifest,
    DatasetPrivacy,
    DatasetSplit,
    MembershipDigestMethod,
    SplitName,
)
from .errors import ProtocolValidationError
from .evaluation import EvaluationResult, evaluate_predictions
from .molerec import MoleRecArtifactBundle, require_bundle_for_stage
from .prediction import MedicationScore, PredictionRecord
from .protocol_check import ProtocolCheckRecord
from .reference import ReferenceConfig, run_reference_slice
from .registry import (
    BaselineDefinition,
    BaselineReadiness,
    BaselineRegistry,
    ComparisonQualification,
    ReadinessEvidence,
    ReadinessGate,
    ResearchMode,
    SourceIdentity,
    SourceStatus,
)
from .remote_executor import JobStatus, RemoteExecutor, SSHConfig
from .run_record import ArtifactChecksum, RunParameter, RunParameterValue, RunRecord

__all__ = (
    "AdaptationBudget",
    "AdapterError",
    "AdapterLaunchError",
    "AdapterProcessError",
    "AdapterProtocolError",
    "AdapterTimeoutError",
    "ArtifactChecksum",
    "BaselineDefinition",
    "BaselineReadiness",
    "BaselineRegistry",
    "ComparisonMethodProfile",
    "ComparisonProfile",
    "ComparisonProtocolV1_1",
    "ComparisonQualification",
    "ComparisonScope",
    "DatasetManifest",
    "DatasetPrivacy",
    "DatasetSplit",
    "DecoderClass",
    "DecoderProfile",
    "EvaluationResult",
    "IndependentEvaluationInput",
    "JobStatus",
    "MedicationScore",
    "MembershipDigestMethod",
    "MoleRecArtifactBundle",
    "PredictionAdapter",
    "PredictionRecord",
    "ProcessPredictionAdapter",
    "ProtocolCheckRecord",
    "ProtocolV1_1",
    "ProtocolValidationError",
    "ReadinessEvidence",
    "ReadinessGate",
    "ReferenceConfig",
    "RemoteExecutor",
    "ResearchMode",
    "RunParameter",
    "RunParameterValue",
    "RunRecord",
    "SSHConfig",
    "SelectionSplit",
    "SourceIdentity",
    "SourceStatus",
    "SplitName",
    "ThresholdSelectionRule",
    "evaluate_predictions",
    "require_bundle_for_stage",
    "run_reference_slice",
)
