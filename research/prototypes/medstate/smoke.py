#!/usr/bin/env python3
"""Targeted synthetic checks for the MedState causal and equivariance contracts."""

from __future__ import annotations

import copy

import numpy as np
import torch
from medstate import CANDIDATE_COUNT, MedStateModel, build_relation_features


def _synthetic_batch(device: torch.device) -> dict[str, torch.Tensor]:
    batch_size = 2
    time_steps = 3
    diagnosis_codes = torch.tensor(
        [
            [[3, 7], [5, 9], [3, 0]],
            [[11, 13], [17, 0], [19, 23]],
        ],
        dtype=torch.long,
        device=device,
    )
    diagnosis_mask = torch.tensor(
        [
            [[True, True], [True, True], [True, False]],
            [[True, True], [True, False], [True, True]],
        ],
        dtype=torch.bool,
        device=device,
    )
    procedure_codes = torch.tensor(
        [
            [[2, 4], [6, 8], [10, 0]],
            [[12, 14], [16, 0], [18, 20]],
        ],
        dtype=torch.long,
        device=device,
    )
    procedure_mask = torch.tensor(
        [
            [[True, True], [True, True], [True, False]],
            [[True, True], [True, False], [True, True]],
        ],
        dtype=torch.bool,
        device=device,
    )
    history_features = torch.zeros(
        (batch_size, time_steps, CANDIDATE_COUNT, 3), dtype=torch.float32, device=device
    )
    history_features[:, 1, 4, 0] = 1.0
    history_features[:, 1, 4, 1] = 1.0
    history_features[:, 2, 4, 2] = 0.5
    history_features[:, 2, 7, 0] = 1.0
    visit_mask = torch.ones((batch_size, time_steps), dtype=torch.bool, device=device)
    targets = torch.zeros(
        (batch_size, time_steps, CANDIDATE_COUNT), dtype=torch.float32, device=device
    )
    targets[:, 0, 4] = 1.0
    targets[:, 1, 7] = 1.0
    return {
        "diagnosis_codes": diagnosis_codes,
        "diagnosis_mask": diagnosis_mask,
        "procedure_codes": procedure_codes,
        "procedure_mask": procedure_mask,
        "history_features": history_features,
        "visit_mask": visit_mask,
        "observed_targets": targets,
    }


def _relation() -> tuple[np.ndarray, np.ndarray]:
    ehr = np.zeros((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32)
    ddi = np.zeros_like(ehr)
    for index in range(6):
        ehr[index, index + 1] = 1.0
        ehr[index + 1, index] = 1.0
    ddi[4, 7] = ddi[7, 4] = 1.0
    return build_relation_features(ehr, ddi)


def _model(variant: str, device: torch.device) -> MedStateModel:
    relation_features, edge_mask = _relation()
    return MedStateModel(
        diagnosis_hash_width=64,
        procedure_hash_width=32,
        state_dim=16,
        relation_features=relation_features,
        edge_mask=edge_mask,
        variant=variant,
    ).to(device)


def _assert_finite(value: torch.Tensor, name: str) -> None:
    if not bool(torch.isfinite(value).all()):
        raise AssertionError(f"{name} contains non-finite values")


def main() -> None:
    torch.manual_seed(20260914)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    batch = _synthetic_batch(device)

    # Current y_t must not affect the logits for the same visit, while a
    # previous observed prescription may affect the next visit.
    persistent = _model("persistent_relational", device).eval()
    altered = batch["observed_targets"].clone()
    altered[:, 0, :] = 1.0
    with torch.no_grad():
        base_output = persistent(**batch, collect_states=True)
        changed_batch = {**batch, "observed_targets": altered}
        changed_output = persistent(**changed_batch, collect_states=True)
    torch.testing.assert_close(base_output.logits[:, 0], changed_output.logits[:, 0])
    if float((base_output.logits[:, 1] - changed_output.logits[:, 1]).abs().max()) <= 1e-6:
        raise AssertionError("previous-visit prescription did not change persistent prediction")
    print("current_target_leakage=PASS")
    print("previous_visit_causal_effect=PASS")

    # StatelessRelational must reset medication states at every visit.
    stateless = _model("stateless_relational", device).eval()
    with torch.no_grad():
        stateless_base = stateless(**batch, collect_states=True)
        stateless_changed = stateless(**changed_batch, collect_states=True)
    torch.testing.assert_close(stateless_base.logits[:, 1], stateless_changed.logits[:, 1])
    torch.testing.assert_close(stateless_base.state_prev[:, 1], stateless_base.state_prev[:, 0])
    print("stateless_state_reset=PASS")

    # PersistentIndependent carries identity states even when relation messages
    # are disabled, isolating persistence from relational co-evolution.
    independent = _model("persistent_independent", device).eval()
    with torch.no_grad():
        independent_base = independent(**batch, collect_states=True)
        independent_changed = independent(**changed_batch, collect_states=True)
    if (
        float((independent_base.logits[:, 1] - independent_changed.logits[:, 1]).abs().max())
        <= 1e-6
    ):
        raise AssertionError("persistent independent state did not carry forward")
    print("persistent_identity_carry=PASS")

    # Medication-index permutation should permute outputs when identity,
    # history, targets, and relation tensors are permuted together.
    permutation = torch.randperm(CANDIDATE_COUNT, device=device)
    permuted = copy.deepcopy(stateless)
    with torch.no_grad():
        permuted.medication_embeddings.copy_(stateless.medication_embeddings[permutation])
        if permuted.interaction is None or stateless.interaction is None:
            raise AssertionError("equivariance check requires the relational surface")
        permuted.interaction.relation_features.copy_(
            stateless.interaction.relation_features[permutation][:, permutation]
        )
        permuted.interaction.edge_mask.copy_(
            stateless.interaction.edge_mask[permutation][:, permutation]
        )
    permuted_batch = {key: value.clone() for key, value in batch.items()}
    permuted_batch["history_features"] = batch["history_features"][:, :, permutation]
    permuted_batch["observed_targets"] = batch["observed_targets"][:, :, permutation]
    with torch.no_grad():
        permuted_output = permuted(**permuted_batch, collect_states=False)
        original_output = stateless(**batch, collect_states=False)
    torch.testing.assert_close(permuted_output.logits, original_output.logits[..., permutation])
    print("medication_permutation_equivariance=PASS")

    # A finite forward/backward smoke is run on CUDA when available; CPU is a
    # fallback only for environments without the approved GPU runtime.
    train_model = _model("persistent_relational", device)
    output = train_model(**batch, collect_states=False)
    if output.loss is None:
        raise AssertionError("forward did not produce a training loss")
    _assert_finite(output.loss, "loss")
    output.loss.backward()
    gradients = [
        parameter.grad for parameter in train_model.parameters() if parameter.grad is not None
    ]
    if not gradients or not all(bool(torch.isfinite(grad).all()) for grad in gradients):
        raise AssertionError("forward/backward produced non-finite or missing gradients")
    print(f"finite_{device.type}_forward_backward=PASS")


if __name__ == "__main__":
    main()
