"""Protocol and diagnostics for the official coarse-grained Rx-Expert screen.

The executable model is loaded from the pinned upstream checkout at runtime.
This module intentionally contains only the protocol-facing adaptation helpers:
patient-history construction, medication-index alignment, deterministic
decoding, metrics, and router diagnostics.  The upstream model source is not
reimplemented here.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple  # noqa: UP035

CANDIDATE_COUNT = 131
GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
EXPECTED_SOURCE_REVISION = "0750f92cfbf51988d78693ef7797a82ead0ea585"


def gate01_dev(patient_id: int) -> bool:
    """Return the frozen Gate01-Dev half split for a patient index."""

    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{int(patient_id)}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


Admission = Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]  # noqa: UP006


def masked_prefix(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_index: int,
    visit_index: int,
) -> tuple[Admission, ...]:
    """Build an official-style prefix with the current target medication masked.

    Rx-Expert receives current and historical diagnoses/procedures.  Its
    history-attention path reads medication sets only from ``patient_data[:-1]``.
    Passing an empty medication tuple for the current visit makes that contract
    explicit at the adapter boundary while leaving all prior medication sets
    unchanged.
    """

    patient = records[int(patient_index)]
    if visit_index < 0 or visit_index >= len(patient):
        raise IndexError("visit index is outside the selected patient")
    prefix: list[Admission] = []
    for offset, admission in enumerate(patient[: visit_index + 1]):
        diagnoses = tuple(sorted(int(code) for code in admission[0]))
        procedures = tuple(sorted(int(code) for code in admission[1]))
        medications = (
            () if offset == visit_index else tuple(sorted(int(code) for code in admission[2]))
        )
        prefix.append((diagnoses, procedures, medications))
    return tuple(prefix)


def assert_temporal_history(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_index: int,
    visit_index: int,
    prefix: Sequence[Admission],
) -> None:
    """Reject current-target leakage and future-medication history."""

    if len(prefix) != visit_index + 1:
        raise ValueError("patient prefix length does not match the target visit")
    patient = records[int(patient_index)]
    target = {int(code) for code in patient[visit_index][2]}
    if prefix[-1][2]:
        raise ValueError("current target medications entered the current adapter input")
    expected_history = {int(code) for admission in patient[:visit_index] for code in admission[2]}
    observed_history = {int(code) for admission in prefix[:-1] for code in admission[2]}
    if observed_history != expected_history:
        raise ValueError("patient history is not exactly the set of prior-visit medications")
    if any(int(code) in target for admission in prefix[-1:] for code in admission[2]):
        raise ValueError("current target medication entered the current visit input")


def visit_examples(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
) -> tuple[tuple[int, int, tuple[Admission, ...], tuple[int, ...]], ...]:
    """Materialize target-free model prefixes in canonical record order."""

    examples: list[tuple[int, int, tuple[Admission, ...], tuple[int, ...]]] = []
    for patient_index in patient_indices:
        patient = records[int(patient_index)]
        for visit_index, admission in enumerate(patient):
            prefix = masked_prefix(records, int(patient_index), visit_index)
            assert_temporal_history(records, int(patient_index), visit_index, prefix)
            target = tuple(sorted(int(code) for code in admission[2]))
            examples.append((int(patient_index), visit_index, prefix, target))
    return tuple(examples)


def target_matrix(
    examples: Sequence[tuple[int, int, Sequence[Admission], Sequence[int]]],
) -> Any:
    """Create a 131-column target matrix for alignment checks."""

    import numpy as np

    matrix = np.zeros((len(examples), CANDIDATE_COUNT), dtype=np.float32)
    for row, (_, _, _, target) in enumerate(examples):
        for medication in target:
            if medication < 0 or medication >= CANDIDATE_COUNT:
                raise ValueError("target medication is outside the canonical vocabulary")
            matrix[row, int(medication)] = 1.0
    return matrix


def canonical_index_mapping(
    canonical_codes: Sequence[str], official_codes: Sequence[str]
) -> tuple[int, ...]:
    """Map canonical medication positions to official feature positions.

    The mapping is code-based, never an incidental list-order assumption.
    """

    canonical = tuple(str(code) for code in canonical_codes)
    official = tuple(str(code) for code in official_codes)
    if len(canonical) != CANDIDATE_COUNT or len(official) != CANDIDATE_COUNT:
        raise ValueError("Rx-Expert coarse alignment requires two 131-medication vocabularies")
    if len(set(canonical)) != len(canonical) or len(set(official)) != len(official):
        raise ValueError("medication vocabularies contain duplicate codes")
    if set(canonical) != set(official):
        missing = sorted(set(canonical) - set(official))
        extra = sorted(set(official) - set(canonical))
        raise ValueError(
            f"RXEXPERT_DRUG_FEATURE_ALIGNMENT_UNRESOLVED missing={missing} extra={extra}"
        )
    official_index = {code: index for index, code in enumerate(official)}
    return tuple(official_index[code] for code in canonical)


def mapping_checksum(canonical_codes: Sequence[str], mapping: Sequence[int]) -> str:
    """Hash the explicit canonical-code to official-row mapping audit."""

    if len(canonical_codes) != len(mapping):
        raise ValueError("canonical codes and mapping must have equal lengths")
    payload = "\n".join(
        f"{code}\t{int(index)}"
        for code, index in zip(canonical_codes, mapping)  # noqa: B905
    )
    return hashlib.sha256((payload + "\n").encode("utf-8")).hexdigest()


def remap_square(matrix: Any, mapping: Sequence[int]) -> Any:
    """Reindex an official medication square matrix into canonical order."""

    import numpy as np

    values = np.asarray(matrix)
    indices = np.asarray(tuple(int(index) for index in mapping), dtype=np.int64)
    if values.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise ValueError("medication square matrix must have shape 131 by 131")
    return values[np.ix_(indices, indices)]


def remap_rows(matrix: Any, mapping: Sequence[int]) -> Any:
    """Reindex an official medication-row matrix into canonical order."""

    import numpy as np

    values = np.asarray(matrix)
    indices = np.asarray(tuple(int(index) for index in mapping), dtype=np.int64)
    if values.ndim != 2 or values.shape[0] != CANDIDATE_COUNT:
        raise ValueError("medication row matrix must have 131 rows")
    return values[indices]


def topk_set(scores: Sequence[float], cardinality: int) -> frozenset[int]:
    """Decode a deterministic Top-K medication set."""

    values = tuple(float(value) for value in scores)
    if len(values) != CANDIDATE_COUNT:
        raise ValueError("score row must contain 131 medications")
    if cardinality < 0 or cardinality > CANDIDATE_COUNT:
        raise ValueError("cardinality is outside the canonical vocabulary")
    ranked = sorted(range(CANDIDATE_COUNT), key=lambda index: (-values[index], index))
    return frozenset(ranked[: int(cardinality)])


def threshold_set(logits: Sequence[float]) -> frozenset[int]:
    """Match the official sigmoid >= 0.5 decoder (logit >= 0)."""

    values = tuple(float(value) for value in logits)
    if len(values) != CANDIDATE_COUNT:
        raise ValueError("logit row must contain 131 medications")
    return frozenset(index for index, value in enumerate(values) if value >= 0.0)


def average_precision(target: Iterable[int], scores: Sequence[float]) -> float:
    """Compute the protocol's deterministic visit-level average precision."""

    target_set = {int(item) for item in target}
    if not target_set:
        return 0.0
    ranked = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranked, start=1):
        if index in target_set:
            found += 1
            total += found / rank
    return total / len(target_set)


def evaluate_sets(
    targets: Sequence[Iterable[int]],
    predictions: Sequence[Iterable[int]],
    scores: Any,
    ddi: Any,
) -> dict[str, float]:
    """Return the canonical visit-macro metrics."""

    import numpy as np

    score_values = np.asarray(scores)
    ddi_values = np.asarray(ddi)
    if len(targets) != len(predictions) or score_values.shape != (len(targets), CANDIDATE_COUNT):
        raise ValueError("targets, predictions, and scores are not visit-aligned")
    if ddi_values.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise ValueError("DDI matrix must be 131 by 131")
    if not targets:
        raise ValueError("cannot evaluate an empty visit collection")
    jaccard = f1 = prauc = 0.0
    ddi_count = pair_count = 0
    for target_raw, prediction_raw, score_row in zip(targets, predictions, score_values):  # noqa: B905
        target = {int(item) for item in target_raw}
        prediction = {int(item) for item in prediction_raw}
        intersection = len(target & prediction)
        union = len(target | prediction)
        jaccard += 1.0 if not union else intersection / union
        precision = (
            1.0
            if not prediction and not target
            else intersection / len(prediction)
            if prediction
            else 0.0
        )
        recall = (
            1.0 if not prediction and not target else intersection / len(target) if target else 0.0
        )
        f1 += 0.0 if precision + recall == 0.0 else 2 * precision * recall / (precision + recall)
        prauc += average_precision(target, score_row)
        ordered = sorted(prediction)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pair_count += 1
                ddi_count += int(bool(ddi_values[left, right]))
    count = float(len(targets))
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "ddi": 0.0 if not pair_count else ddi_count / pair_count,
        "mean_medication_count": sum(len(set(item)) for item in predictions) / count,
    }


def set_change_summary(
    baseline: Sequence[Iterable[int]],
    compared: Sequence[Iterable[int]],
) -> dict[str, float]:
    """Summarize set movement against a fixed baseline."""

    if len(baseline) != len(compared) or not baseline:
        raise ValueError("baseline and compared sets must be non-empty and aligned")
    differences = [
        len(set(left) ^ set(right))
        for left, right in zip(baseline, compared)  # noqa: B905
    ]
    return {
        "changed_fraction": sum(value > 0 for value in differences) / len(differences),
        "mean_symmetric_difference": sum(differences) / len(differences),
    }


@dataclass
class RouterProbe:
    """Non-invasive instrumentation for the official Top2Gating modules."""

    records: list[dict[str, Any]]

    def __init__(self) -> None:
        self.records = []
        self._handles: list[Any] = []
        self._pending: dict[int, Any] = {}

    def attach(self, model: Any) -> None:
        for module in model.modules():
            if module.__class__.__name__ != "Top2Gating":
                continue
            self._handles.append(module.register_forward_pre_hook(self._before))
            self._handles.append(module.register_forward_hook(self._after))

    def _before(self, module: Any, inputs: tuple[Any, ...]) -> None:
        if not inputs:
            return
        self._pending[id(module)] = (module, inputs[0].detach())

    def _after(self, module: Any, inputs: tuple[Any, ...], output: Any) -> None:
        pending = self._pending.pop(id(module), None)
        if pending is None or len(output) < 5:
            return
        _, tensor = pending
        dispatch, combine, _loss, index1, index2 = output[:5]
        raw = torch_einsum_softmax(tensor, module.w_gating)
        self.records.append(
            {
                "num_experts": int(module.num_gates),
                "weights": raw.detach().cpu(),
                "index1": index1.detach().cpu(),
                "index2": index2.detach().cpu(),
                "dispatch": dispatch.detach().cpu(),
                "combine": combine.detach().cpu(),
            }
        )

    def clear(self) -> None:
        self.records.clear()

    def close(self) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles.clear()
        self._pending.clear()

    def summary(self, dead_threshold: float = 0.01) -> dict[str, Any]:
        """Aggregate mean gate weights, Top-2 utilization, entropy, and dead rate."""

        if not self.records:
            raise ValueError("router probe captured no Top2Gating calls")
        num_experts = max(int(item["num_experts"]) for item in self.records)
        weights = []
        top1 = [0] * num_experts
        top2 = [0] * num_experts
        total = 0
        entropy = []
        for item in self.records:
            values = item["weights"].reshape(-1, num_experts).float()
            weights.append(values)
            entropy.extend((-(values * values.clamp_min(1e-12).log()).sum(dim=-1)).tolist())
            first = item["index1"].reshape(-1).tolist()
            second = item["index2"].reshape(-1).tolist()
            for index in first:
                top1[int(index)] += 1
            for index in second:
                top2[int(index)] += 1
            total += len(first)
        mean_weights = torch_cat(weights).mean(dim=0).tolist()
        top1_utilization = [value / total for value in top1]
        top2_utilization = [value / total for value in top2]
        combined = [
            (left + right) / (2.0 * total)
            for left, right in zip(top1, top2)  # noqa: B905
        ]
        dead = sum(value < dead_threshold for value in combined) / num_experts
        return {
            "num_experts": num_experts,
            "mean_routing_weights": [float(value) for value in mean_weights],
            "top1_utilization": [float(value) for value in top1_utilization],
            "top2_utilization": [float(value) for value in top2_utilization],
            "combined_top2_utilization": [float(value) for value in combined],
            "routing_entropy": float(sum(entropy) / len(entropy)),
            "routing_entropy_normalized": float(
                (sum(entropy) / len(entropy)) / math.log(num_experts)
            ),
            "effective_dead_expert_fraction": float(dead),
            "effective_dead_threshold": float(dead_threshold),
            "routing_calls": len(self.records),
            "routed_positions": int(total),
        }


def torch_einsum_softmax(inputs: Any, weights: Any) -> Any:
    """Compute official Top2Gating's raw softmax for a probe."""

    import torch

    raw = torch.einsum("...bnd,...de->...bne", inputs, weights)
    return raw.softmax(dim=-1)


def torch_cat(values: Sequence[Any]) -> Any:
    """Small lazy torch helper to keep import-time dependencies optional."""

    import torch

    return torch.cat(tuple(values), dim=0)


def parameter_count(model: Any) -> dict[str, int]:
    """Return total and trainable parameter counts."""

    total = trainable = 0
    for parameter in model.parameters():
        count = int(parameter.numel())
        total += count
        if parameter.requires_grad:
            trainable += count
    return {"total": total, "trainable": trainable}


def source_revision(source_root: Path) -> str:
    """Read the pinned official checkout revision without mutating it."""

    import subprocess

    completed = subprocess.run(
        ["git", "-c", f"safe.directory={source_root}", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
