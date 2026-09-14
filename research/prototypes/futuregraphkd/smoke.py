#!/usr/bin/env python3
"""Small CUDA forward/backward and privilege-boundary smoke."""

from __future__ import annotations

import numpy as np
import torch
from futuregraphkd import (
    CANDIDATE_COUNT,
    DEFAULT_CODE_HASH_WIDTH,
    FutureGraphKDModel,
    build_relation_features,
    context_feature_dimension,
    future_feature_dimension,
    future_graph_kd_loss,
)


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for the FutureGraphKD smoke")
    torch.manual_seed(20260914)
    device = torch.device("cuda")
    rng = np.random.default_rng(20260914)
    relation = build_relation_features(
        rng.random((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32),
        (rng.random((CANDIDATE_COUNT, CANDIDATE_COUNT)) > 0.98).astype(np.float32),
    )
    model_kwargs = {
        "embedding_dim": 64,
        "context_dim": context_feature_dimension(DEFAULT_CODE_HASH_WIDTH),
        "future_dim": future_feature_dimension(DEFAULT_CODE_HASH_WIDTH),
        "relation_features": relation,
        "hidden_dim": 96,
    }
    student = FutureGraphKDModel(**model_kwargs, use_future=False).to(device)
    teacher = FutureGraphKDModel(**model_kwargs, use_future=True).to(device)
    embeddings = torch.randn(3, CANDIDATE_COUNT, 64, device=device)
    scores = torch.randn(3, CANDIDATE_COUNT, device=device)
    context = torch.randn(3, model_kwargs["context_dim"], device=device)
    future_a = torch.randn(3, model_kwargs["future_dim"], device=device)
    future_b = torch.randn(3, model_kwargs["future_dim"], device=device)
    targets = torch.randint(0, 2, (3, CANDIDATE_COUNT), device=device).float()
    supported = torch.tensor([True, True, False], device=device)
    student_a = student(embeddings, scores, context, future_a)
    student_b = student(embeddings, scores, context, future_b)
    teacher_a = teacher(embeddings, scores, context, future_a)
    if not torch.allclose(student_a.logits, student_b.logits, atol=1e-6, rtol=1e-6):
        raise RuntimeError("Student output changed when only privileged future features changed")
    if torch.allclose(teacher_a.logits, student_a.logits, atol=1e-6, rtol=1e-6):
        raise RuntimeError("Teacher did not consume its privileged future features")
    loss, detail = future_graph_kd_loss(student_a, teacher_a, targets, supported)
    loss.backward()
    if not torch.isfinite(loss) or not all(
        parameter.grad is None or torch.isfinite(parameter.grad).all()
        for model in (student, teacher)
        for parameter in model.parameters()
    ):
        raise RuntimeError("FutureGraphKD smoke produced a non-finite loss or gradient")
    print(
        {
            "device": str(device),
            "loss": float(loss.detach().cpu()),
            "detail": detail,
            "student_future_invariant": True,
            "teacher_future_used": True,
        }
    )


if __name__ == "__main__":
    main()
