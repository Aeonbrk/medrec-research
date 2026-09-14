#!/usr/bin/env python3
"""Run the faithful coarse-grained Rx-Expert Train/Gate01-Dev screen.

The model is loaded from the exact upstream checkout supplied with
``--official-source-root``.  The only source transformation is a mechanical
rename of the upstream hyphenated class identifier (the checked-in source is
not valid Python as published).  All molecular encoders, MoE routers, history
attention, loss terms, and the recommendation head remain upstream code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch
from rxexpert import (
    CANDIDATE_COUNT,
    EXPECTED_SOURCE_REVISION,
    RouterProbe,
    canonical_index_mapping,
    evaluate_sets,
    gate01_dev,
    mapping_checksum,
    parameter_count,
    remap_rows,
    remap_square,
    set_change_summary,
    source_revision,
    target_matrix,
    threshold_set,
    topk_set,
    visit_examples,
)
from torch import nn
from torch.nn.functional import binary_cross_entropy_with_logits, multilabel_margin_loss

DEFAULT_SEED = 20260914
DEFAULT_EPOCHS = 50
CHECKPOINT_EPOCHS = (10, 20, 30, 40, 50)
EXECUTION_BATCH_SIZE = 256
OFFICIAL_DIM = 64
OFFICIAL_LR = 5e-4
OFFICIAL_DROPOUT = 0.7
OFFICIAL_DDI_COEFFICIENT = 0.0005
OFFICIAL_AUX_COEFFICIENT = 1e-2


@dataclass
class Assets:
    records: Any
    voc: Any
    ddi: np.ndarray
    drug_caption: torch.Tensor
    drug_data: dict[str, Any]
    feature_audit: dict[str, Any]
    canonical_codes: tuple[str, ...]
    train_examples: tuple[Any, ...]
    dev_examples: tuple[Any, ...]
    train_targets: np.ndarray
    dev_targets: np.ndarray
    dev_molerec_scores: np.ndarray


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _idx2word(vocabulary: Any) -> tuple[str, ...]:
    values = vocabulary.idx2word
    return tuple(str(values[index]) for index in range(len(values)))


def _load_official_util(source_root: Path) -> Any:
    path = source_root / "util.py"
    spec = spec_from_file_location("rxexpert_official_util", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load official utility module: {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_official_model(source_root: Path) -> tuple[type[nn.Module], dict[str, Any]]:
    """Load upstream modules and mechanically repair only invalid identifiers."""

    import importlib

    source_root = source_root.resolve()
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    importlib.invalidate_caches()
    # These names are upstream's own imports.  Removing only prior instances
    # avoids accidentally importing a module from a different checkout.
    for name in ("MoE", "GNNConv", "GNNs", "SetTransformer"):
        sys.modules.pop(name, None)
    model_path = source_root / "Rx-Expert.py"
    source = model_path.read_text(encoding="utf-8")
    class_count = source.count("class Rx-Expert")
    super_count = source.count("super(Rx-Expert")
    if class_count != 1 or super_count != 1:
        raise RuntimeError("unexpected upstream Rx-Expert source shape; refuse adaptation")
    patched = source.replace("class Rx-Expert", "class RxExpert").replace(
        "super(Rx-Expert", "super(RxExpert"
    )
    namespace: dict[str, Any] = {
        "__name__": "rxexpert_official_model",
        "__file__": str(model_path),
        "__package__": None,
    }
    exec(compile(patched, str(model_path), "exec"), namespace)
    model_class = namespace.get("RxExpert")
    if not isinstance(model_class, type):
        raise RuntimeError("mechanically loaded upstream model did not expose RxExpert")
    return model_class, {
        "source_file": str(model_path),
        "syntax_patches": [
            "class Rx-Expert -> class RxExpert",
            "super(Rx-Expert -> super(RxExpert",
        ],
        "source_patch_counts": {"class_identifier": class_count, "super_identifier": super_count},
    }


def _assert_no_held_out_path(path: Path, label: str) -> None:
    lowered = str(path).lower()
    forbidden = ("audit", "test", "heldout", "held-out")
    if any(token in lowered for token in forbidden):
        raise RuntimeError(f"{label} path appears to reference a held-out resource: {path}")


def _valid_smiles_groups(molecule: dict[str, Any], canonical_codes: tuple[str, ...]) -> None:
    missing = [code for code in canonical_codes if code not in molecule]
    if missing:
        raise RuntimeError(
            "RXEXPERT_DRUG_FEATURE_ALIGNMENT_UNRESOLVED missing molecule codes " + repr(missing)
        )


def _load_assets(args: argparse.Namespace, execution_device: torch.device | None = None) -> Assets:
    snapshot_root = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    official_root = args.official_source_root.resolve()
    _assert_no_held_out_path(snapshot_root, "snapshot")
    _assert_no_held_out_path(train_dev_root, "Train/Dev")
    required = (
        "records_final.pkl",
        "voc_final.pkl",
        "ddi_A_final.pkl",
    )
    for name in required:
        if not (snapshot_root / name).is_file():
            raise FileNotFoundError(f"canonical snapshot is missing {name}")
    for name in ("train_targets.npy", "dev_targets.npy", "dev_scores.npy"):
        if not (train_dev_root / name).is_file():
            raise FileNotFoundError(f"Train/Dev artifact is missing {name}")

    records = dill.load((snapshot_root / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot_root / "voc_final.pkl").open("rb"))
    canonical_codes = _idx2word(voc["med_voc"])
    if len(records) != 6350 or len(canonical_codes) != CANDIDATE_COUNT:
        raise RuntimeError("canonical snapshot does not have the expected cohort or vocabulary")

    train_patient_indices = tuple(range(int(len(records) * 2 / 3)))
    dev_patient_indices = tuple(
        patient_id
        for patient_id in range(int(len(records) * 2 / 3), len(records))
        if gate01_dev(patient_id)
    )
    train_examples = visit_examples(records, train_patient_indices)
    dev_examples = visit_examples(records, dev_patient_indices)
    train_targets = np.asarray(np.load(train_dev_root / "train_targets.npy"), dtype=np.float32)
    dev_targets = np.asarray(np.load(train_dev_root / "dev_targets.npy"), dtype=np.float32)
    dev_molerec_scores = np.asarray(np.load(train_dev_root / "dev_scores.npy"), dtype=np.float32)
    expected_train_targets = target_matrix(train_examples)
    expected_dev_targets = target_matrix(dev_examples)
    for name, observed, expected in (
        ("train_targets", train_targets, expected_train_targets),
        ("dev_targets", dev_targets, expected_dev_targets),
    ):
        if observed.shape != expected.shape or not np.array_equal(observed, expected):
            raise RuntimeError(f"{name} does not align with canonical target-free visit order")
    if dev_molerec_scores.shape != dev_targets.shape:
        raise RuntimeError("dev_scores and dev_targets are not visit-aligned")
    if (len(train_examples), len(dev_examples)) != (10489, 2130):
        raise RuntimeError(
            f"canonical Train/Gate01-Dev counts changed: {len(train_examples)} / {len(dev_examples)}"
        )

    official_data = official_root.parent.parent / "data" / "coarse-grained"
    for name in (
        "voc_final.pkl",
        "idx2SMILES.pkl",
        "substructure_smiles.pkl",
        "smiles_rep.pkl",
        "ddi_mask_H.pkl",
        "ddi_A_final.pkl",
    ):
        if not (official_data / name).is_file():
            raise FileNotFoundError(f"official coarse feature is missing {name}")
    official_voc = dill.load((official_data / "voc_final.pkl").open("rb"))
    official_codes = _idx2word(official_voc["med_voc"])
    mapping = canonical_index_mapping(canonical_codes, official_codes)
    mapping_hash = mapping_checksum(canonical_codes, mapping)

    canonical_ddi = np.asarray(
        dill.load((snapshot_root / "ddi_A_final.pkl").open("rb")), dtype=np.float64
    )
    official_ddi = np.asarray(
        dill.load((official_data / "ddi_A_final.pkl").open("rb")), dtype=np.float64
    )
    remapped_ddi = remap_square(official_ddi, mapping)
    if not np.array_equal(remapped_ddi, canonical_ddi):
        raise RuntimeError("STOP_INVALID_RXEXPERT_ADAPTATION: DDI index order is not identical")

    official_mask = np.asarray(
        dill.load((official_data / "ddi_mask_H.pkl").open("rb")), dtype=np.float64
    )
    substructure_smiles = dill.load((official_data / "substructure_smiles.pkl").open("rb"))
    if official_mask.shape != (CANDIDATE_COUNT, len(substructure_smiles)):
        raise RuntimeError("official DDI substructure mask and substructure list are misaligned")
    canonical_mask = remap_rows(official_mask, mapping)

    drug_caption = dill.load((official_data / "smiles_rep.pkl").open("rb"))
    if not torch.is_tensor(drug_caption):
        drug_caption = torch.as_tensor(drug_caption)
    if tuple(drug_caption.shape) != (CANDIDATE_COUNT, 1024):
        raise RuntimeError("official smiles_rep.pkl is not the required [131, 1024] tensor")
    if not bool(torch.isfinite(drug_caption).all()):
        raise RuntimeError("official smiles_rep.pkl contains non-finite values")
    drug_caption = drug_caption[torch.as_tensor(mapping, dtype=torch.long)].contiguous()

    molecule = dill.load((official_data / "idx2SMILES.pkl").open("rb"))
    _valid_smiles_groups(molecule, canonical_codes)
    official_util = _load_official_util(official_root)
    canonical_molecule_index = {index: code for index, code in enumerate(canonical_codes)}
    average_projection, smiles_list = official_util.buildPrjSmiles(
        molecule, canonical_molecule_index
    )
    if next(iter(average_projection.shape)) != CANDIDATE_COUNT or not smiles_list:
        raise RuntimeError("official molecular projection could not cover all canonical drugs")
    molecule_graphs = official_util.graph_batch_from_smile(smiles_list)
    substructure_graphs = official_util.graph_batch_from_smile(substructure_smiles)
    observed_substructure_count = int(substructure_graphs.batch.max().item()) + 1
    if observed_substructure_count != len(substructure_smiles):
        raise RuntimeError("substructure graph batch is not aligned to ddi_mask_H columns")

    device = execution_device or torch.device("cuda", args.device)
    drug_data = {
        "substruct_data": {"batched_data": substructure_graphs.to(device)},
        "mol_data": {"batched_data": molecule_graphs.to(device)},
        "ddi_mask_H": torch.from_numpy(canonical_mask).to(device=device),
        "tensor_ddi_adj": torch.from_numpy(canonical_ddi).to(device=device),
        "average_projection": average_projection.to(device=device),
    }
    feature_audit = {
        "official_source_revision": source_revision(official_root),
        "official_data_root": str(official_data),
        "canonical_medication_codes": list(canonical_codes),
        "official_medication_codes": list(official_codes),
        "canonical_to_official_row_mapping": list(mapping),
        "mapping_sha256": mapping_hash,
        "mapping_is_identity": tuple(mapping) == tuple(range(CANDIDATE_COUNT)),
        "smiles_rep_shape": list(drug_caption.shape),
        "smiles_rep_dtype": str(drug_caption.dtype),
        "smiles_rep_provenance": "official repository coarse-grained/smiles_rep.pkl; fixed drug-description representation; no local regeneration",
        "idx2SMILES_sha256": _sha256(official_data / "idx2SMILES.pkl"),
        "substructure_smiles_sha256": _sha256(official_data / "substructure_smiles.pkl"),
        "ddi_mask_shape": list(canonical_mask.shape),
        "ddi_mask_sha256": _sha256(official_data / "ddi_mask_H.pkl"),
        "substructure_count": len(substructure_smiles),
        "molecular_smiles_count": len(smiles_list),
        "ddi_alignment_equal_to_canonical": True,
    }
    return Assets(
        records=records,
        voc=voc,
        ddi=canonical_ddi,
        drug_caption=drug_caption,
        drug_data=drug_data,
        feature_audit=feature_audit,
        canonical_codes=canonical_codes,
        train_examples=train_examples,
        dev_examples=dev_examples,
        train_targets=train_targets,
        dev_targets=dev_targets,
        dev_molerec_scores=dev_molerec_scores,
    )


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _make_model(
    model_class: type[nn.Module],
    assets: Assets,
    args: argparse.Namespace,
    device: torch.device,
) -> nn.Module:
    voc_size = (
        len(assets.voc["diag_voc"].idx2word),
        len(assets.voc["pro_voc"].idx2word),
        len(assets.voc["med_voc"].idx2word),
    )
    caption = assets.drug_caption
    global_para = {
        "num_layer": 4,
        "emb_dim": OFFICIAL_DIM,
        "graph_pooling": "mean",
        "drop_ratio": OFFICIAL_DROPOUT,
        "gnn_type": "gin",
        "virtual_node": False,
    }
    substruct_para = dict(global_para)
    return model_class(
        global_para=global_para,
        substruct_para=substruct_para,
        emb_dim=OFFICIAL_DIM,
        global_dim=OFFICIAL_DIM,
        substruct_dim=OFFICIAL_DIM,
        drug_caption=caption,
        substruct_num=int(assets.drug_data["ddi_mask_H"].shape[1]),
        voc_size=voc_size,
        device=device,
        dropout=OFFICIAL_DROPOUT,
    ).to(device)


def _target_tensors(
    target: Sequence[int], device: torch.device
) -> tuple[torch.Tensor, torch.Tensor]:
    bce_target = torch.zeros((1, CANDIDATE_COUNT), dtype=torch.float32, device=device)
    if target:
        bce_target[:, list(target)] = 1.0
    multi_target = torch.full((1, CANDIDATE_COUNT), -1, dtype=torch.long, device=device)
    if target:
        multi_target[0, : len(target)] = torch.as_tensor(target, dtype=torch.long, device=device)
    return bce_target, multi_target


class _CachedEncoder(nn.Module):
    """Replay one static official drug encoder result within an update batch."""

    def __init__(self, original: nn.Module, cached: torch.Tensor) -> None:
        super().__init__()
        self.original = original
        self.cached = cached

    def forward(self, *args: Any, **kwargs: Any) -> torch.Tensor:
        del args, kwargs
        return self.cached


@contextmanager
def _cached_static_drug_encoders(model: nn.Module, drug_data: dict[str, Any]) -> Any:
    """Cache only the patient-independent GIN branches for one optimizer step.

    The upstream source recomputes these fixed molecular graphs for every
    single-visit update.  Replaying one training-mode result for a short
    gradient-accumulation batch is a bounded execution optimization: the
    official modules, parameters, dropout, SAB, fusion, history attention,
    head, and loss remain unchanged.  The run record names this as a minor
    execution patch rather than claiming byte-for-byte upstream optimization
    semantics.
    """

    original_global = model.global_encoder
    original_substruct = model.substruct_encoder
    global_value = original_global(**drug_data["mol_data"])
    substruct_value = original_substruct(**drug_data["substruct_data"])
    model.global_encoder = _CachedEncoder(original_global, global_value)
    model.substruct_encoder = _CachedEncoder(original_substruct, substruct_value)
    try:
        yield
    finally:
        model.global_encoder = original_global
        model.substruct_encoder = original_substruct


def _train_epoch(
    model: nn.Module,
    examples: Sequence[Any],
    drug_data: dict[str, Any],
    device: torch.device,
) -> dict[str, float]:
    model.train()
    optimizer = _train_epoch.optimizer
    totals = {"bce": 0.0, "multilabel_margin": 0.0, "ddi": 0.0, "moe_aux": 0.0, "total": 0.0}
    for start in range(0, len(examples), EXECUTION_BATCH_SIZE):
        batch = examples[start : start + EXECUTION_BATCH_SIZE]
        optimizer.zero_grad(set_to_none=True)
        losses: list[torch.Tensor] = []
        with _cached_static_drug_encoders(model, drug_data):
            for _, _, prefix, target in batch:
                bce_target, multi_target = _target_tensors(target, device)
                result, loss_ddi, loss_aux = model(patient_data=prefix, **drug_data)
                sigmoid_result = torch.sigmoid(result)
                loss_bce = binary_cross_entropy_with_logits(result, bce_target)
                loss_multi = multilabel_margin_loss(sigmoid_result, multi_target)
                loss = 0.95 * loss_bce + 0.05 * loss_multi + loss_aux + loss_ddi
                if not bool(torch.isfinite(loss).all()):
                    raise RuntimeError("non-finite Rx-Expert training loss")
                losses.append(loss)
                totals["bce"] += float(loss_bce.detach().cpu())
                totals["multilabel_margin"] += float(loss_multi.detach().cpu())
                totals["ddi"] += float(loss_ddi.detach().cpu())
                totals["moe_aux"] += float(loss_aux.detach().cpu())
                totals["total"] += float(loss.detach().cpu())
            torch.stack(losses).mean().backward()
        optimizer.step()
    count = float(len(examples))
    return {key: value / count for key, value in totals.items()}


def _finite_forward_backward(
    model: nn.Module,
    example: Any,
    drug_data: dict[str, Any],
    device: torch.device,
) -> dict[str, Any]:
    model.train()
    _, _, prefix, target = example
    bce_target, multi_target = _target_tensors(target, device)
    model.zero_grad(set_to_none=True)
    result, loss_ddi, loss_aux = model(patient_data=prefix, **drug_data)
    loss_bce = binary_cross_entropy_with_logits(result, bce_target)
    loss_multi = multilabel_margin_loss(torch.sigmoid(result), multi_target)
    loss = 0.95 * loss_bce + 0.05 * loss_multi + loss_aux + loss_ddi
    loss.backward()
    finite_params = all(
        bool(torch.isfinite(parameter.grad).all())
        for parameter in model.parameters()
        if parameter.grad is not None
    )
    finite = (
        bool(torch.isfinite(result).all()) and bool(torch.isfinite(loss).all()) and finite_params
    )
    model.zero_grad(set_to_none=True)
    return {"finite": finite, "loss": float(loss.detach().cpu())}


def _predict(
    model: nn.Module,
    examples: Sequence[Any],
    drug_data: dict[str, Any],
    device: torch.device,
) -> tuple[np.ndarray, tuple[frozenset[int], ...]]:
    model.eval()
    logits: list[np.ndarray] = []
    predictions: list[frozenset[int]] = []
    with torch.no_grad():
        for _, _, prefix, _ in examples:
            output, _, _ = model(patient_data=prefix, **drug_data)
            row = output.detach().cpu().numpy()[0].astype(np.float32, copy=False)
            if row.shape != (CANDIDATE_COUNT,) or not np.isfinite(row).all():
                raise RuntimeError("Rx-Expert emitted a malformed or non-finite 131-logit row")
            logits.append(row.copy())
            predictions.append(threshold_set(row))
    return np.asarray(logits, dtype=np.float32), tuple(predictions)


def _router_diagnostic(
    model: nn.Module,
    examples: Sequence[Any],
    drug_data: dict[str, Any],
    device: torch.device,
    *,
    training: bool,
) -> dict[str, Any]:
    probe = RouterProbe()
    probe.attach(model)
    model.train(training)
    with torch.no_grad():
        for _, _, prefix, _ in examples[:8]:
            model(patient_data=prefix, **drug_data)
    result = probe.summary()
    probe.close()
    return result


class SharedNoMoE(nn.Module):
    """Matched control: retain the official four GRUs, remove patient routing."""

    def __init__(self, official_moe: nn.Module) -> None:
        super().__init__()
        # Keep the upstream gate in the module tree so parameter scale and
        # state-dict identity remain comparable; it is intentionally unused.
        self.gate = official_moe.gate
        self.experts = official_moe.experts
        self.loss_coef = official_moe.loss_coef

    def forward(self, inputs: torch.Tensor, **kwargs: Any) -> tuple[Any, ...]:
        output = self.experts(inputs)
        zero = inputs.new_zeros(())
        shape = inputs.shape[:2]
        indices = torch.zeros(shape, dtype=torch.long, device=inputs.device)
        return output, zero, indices, indices


def _replace_moe(model: nn.Module) -> None:
    model.GRUMoe1 = SharedNoMoE(model.GRUMoe1)
    model.GRUMoe2 = SharedNoMoE(model.GRUMoe2)


def _baseline_metrics(
    assets: Assets,
) -> tuple[dict[str, float], tuple[frozenset[int], ...]]:
    target_sets = tuple(
        frozenset(int(index) for index in np.flatnonzero(row > 0.5)) for row in assets.dev_targets
    )
    predictions = tuple(
        frozenset(int(index) for index in np.flatnonzero(row >= 0.0))
        for row in assets.dev_molerec_scores
    )
    return evaluate_sets(
        target_sets, predictions, assets.dev_molerec_scores, assets.ddi
    ), predictions


def _health(
    rx_metrics: dict[str, float],
    baseline: dict[str, float],
) -> dict[str, Any]:
    jaccard_threshold = 0.540
    direct = rx_metrics["jaccard"] >= jaccard_threshold
    pareto = (
        rx_metrics["jaccard"] >= baseline["jaccard"] - 0.001
        and rx_metrics["prauc"] >= baseline["prauc"] - 0.001
        and rx_metrics["ddi"] <= baseline["ddi"] - 0.010
    )
    return {
        "jaccard_threshold": jaccard_threshold,
        "direct_threshold_pass": direct,
        "material_accuracy_safety_pareto_pass": pareto,
        "healthy": direct or pareto,
        "pareto_definition": "Jaccard/PRAUC within 0.001 of MoleRec while DDI is at least 0.010 lower",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.epochs != DEFAULT_EPOCHS:
        raise ValueError("the bounded Rx-Expert screen fixes the official 50-epoch budget")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the canonical Rx-Expert screen")
    device = torch.device("cuda", args.device)
    _seed_everything(args.seed)
    source_root = args.official_source_root.resolve()
    actual_revision = source_revision(source_root)
    if actual_revision != EXPECTED_SOURCE_REVISION:
        raise RuntimeError(
            f"official Rx-Expert revision mismatch: expected {EXPECTED_SOURCE_REVISION}, got {actual_revision}"
        )
    model_class, source_load_audit = _load_official_model(source_root)
    assets = _load_assets(args)

    model = _make_model(model_class, assets, args, device)
    initial_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    model_params = parameter_count(model)
    pre_router = _router_diagnostic(
        model, assets.train_examples, assets.drug_data, device, training=True
    )
    finite_probe = _finite_forward_backward(
        model, assets.train_examples[0], assets.drug_data, device
    )
    if not finite_probe["finite"]:
        raise RuntimeError("STOP_INVALID_RXEXPERT_ADAPTATION: CUDA forward/backward was non-finite")
    # Diagnostic probes consume dropout/router randomness; reset the declared
    # primary seed before the actual 50-epoch run.
    _seed_everything(args.seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=OFFICIAL_LR)
    _train_epoch.optimizer = optimizer
    learning_curve: list[dict[str, Any]] = []
    epoch_losses: list[dict[str, float]] = []
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.perf_counter()
        loss = _train_epoch(model, assets.train_examples, assets.drug_data, device)
        loss["epoch"] = epoch
        loss["seconds"] = time.perf_counter() - epoch_start
        epoch_losses.append(loss)
        if epoch in CHECKPOINT_EPOCHS:
            dev_logits, dev_predictions = _predict(
                model, assets.dev_examples, assets.drug_data, device
            )
            target_sets = tuple(
                frozenset(int(index) for index in np.flatnonzero(row > 0.5))
                for row in assets.dev_targets
            )
            learning_curve.append(
                {
                    "epoch": epoch,
                    "train_loss": loss,
                    "dev_metrics": evaluate_sets(
                        target_sets, dev_predictions, dev_logits, assets.ddi
                    ),
                }
            )
    training_seconds = time.perf_counter() - start
    final_logits, final_predictions = _predict(model, assets.dev_examples, assets.drug_data, device)
    target_sets = tuple(
        frozenset(int(index) for index in np.flatnonzero(row > 0.5)) for row in assets.dev_targets
    )
    baseline_metrics, baseline_predictions = _baseline_metrics(assets)
    rx_metrics = evaluate_sets(target_sets, final_predictions, final_logits, assets.ddi)
    same_k_predictions = tuple(
        topk_set(score_row, len(base))
        for score_row, base in zip(final_logits, baseline_predictions)  # noqa: B905
    )
    same_k_metrics = evaluate_sets(target_sets, same_k_predictions, final_logits, assets.ddi)
    post_router = _router_diagnostic(
        model, assets.train_examples, assets.drug_data, device, training=True
    )
    if (
        post_router["effective_dead_expert_fraction"] >= 0.75
        and max(post_router["top1_utilization"]) >= 0.99
    ):
        fidelity = "RXEXPERT_ADAPTATION_FIDELITY_UNRESOLVED"
        terminal = "STOP_INVALID_RXEXPERT_ADAPTATION"
    else:
        fidelity = "RXEXPERT_MINOR_EXECUTION_PATCHES_ONLY"
        health = _health(rx_metrics, baseline_metrics)
        terminal = (
            "RXEXPERT_BACKBONE_HEALTHY" if health["healthy"] else "STOP_RXEXPERT_BACKBONE_RESET"
        )

    metrics = {
        "MoleRec": baseline_metrics,
        "RxExpert": rx_metrics,
        "RxExpert-MoleRecK": same_k_metrics,
    }
    result: dict[str, Any] = {
        "method": "Rx-Expert coarse-grained",
        "official_source_revision": actual_revision,
        "source_load_audit": source_load_audit,
        "seed": args.seed,
        "device": str(device),
        "device_name": torch.cuda.get_device_name(device),
        "config": {
            "hidden_dimension": OFFICIAL_DIM,
            "gru_experts_per_path": 4,
            "router_gate_count": 16,
            "router": "official learned Top2Gating",
            "top_k": 2,
            "second_policy_train": "random",
            "second_policy_eval": "random",
            "second_threshold_train": 0.2,
            "second_threshold_eval": 0.2,
            "capacity_factor_train": 1.25,
            "capacity_factor_eval": 2.0,
            "moe_auxiliary_coefficient": OFFICIAL_AUX_COEFFICIENT,
            "molecular_encoder": "4-layer GIN, mean pooling, no virtual node",
            "substructure_encoder": "4-layer GIN + 2-head SAB",
            "dropout": OFFICIAL_DROPOUT,
            "optimizer": "Adam",
            "learning_rate": OFFICIAL_LR,
            "weight_decay": 0.0,
            "ddi_coefficient": OFFICIAL_DDI_COEFFICIENT,
            "loss": "0.95 BCE + 0.05 multilabel-margin + MoE auxiliary + DDI penalty",
            "epochs": args.epochs,
            "execution_batch_size": EXECUTION_BATCH_SIZE,
            "execution_patch": "static patient-independent GIN results replayed within 256-visit gradient-accumulation batches",
            "threshold": 0.5,
            "inference": "sigmoid(logit) >= 0.5",
        },
        "split": {
            "train_patients": 4233,
            "train_visits": len(assets.train_examples),
            "gate01_dev_patients": len({patient_id for patient_id, _, _, _ in assets.dev_examples}),
            "gate01_dev_visits": len(assets.dev_examples),
            "held_out_resources_read": False,
            "current_target_masked": True,
            "history_assertion": "for each visit t, medication history equals visits < t",
        },
        "parameter_count": model_params,
        "training_seconds": training_seconds,
        "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated(device)),
        "finite_cuda_forward_backward": finite_probe,
        "router_utilization": {"pre_train": pre_router, "post_train": post_router},
        "feature_audit": assets.feature_audit,
        "metrics": metrics,
        "same_k_change": set_change_summary(baseline_predictions, same_k_predictions),
        "rxexpert_change": set_change_summary(baseline_predictions, final_predictions),
        "learning_curve": learning_curve,
        "epoch_losses": epoch_losses,
        "fidelity_verdict": fidelity,
        "terminal_verdict": terminal,
    }
    if fidelity in {"RXEXPERT_FAITHFUL", "RXEXPERT_MINOR_EXECUTION_PATCHES_ONLY"}:
        result["health"] = _health(rx_metrics, baseline_metrics)

    if (
        fidelity in {"RXEXPERT_FAITHFUL", "RXEXPERT_MINOR_EXECUTION_PATCHES_ONLY"}
        and result["health"]["healthy"]
    ):
        _seed_everything(args.seed)
        control = _make_model(model_class, assets, args, device)
        control.load_state_dict(initial_state)
        _replace_moe(control)
        control_optimizer = torch.optim.Adam(control.parameters(), lr=OFFICIAL_LR)
        _train_epoch.optimizer = control_optimizer
        control_losses: list[dict[str, float]] = []
        control_start = time.perf_counter()
        for epoch in range(1, args.epochs + 1):
            control_loss = _train_epoch(control, assets.train_examples, assets.drug_data, device)
            control_loss["epoch"] = epoch
            control_losses.append(control_loss)
        control_seconds = time.perf_counter() - control_start
        control_logits, control_predictions = _predict(
            control, assets.dev_examples, assets.drug_data, device
        )
        control_metrics = evaluate_sets(
            target_sets, control_predictions, control_logits, assets.ddi
        )
        delta_jaccard = rx_metrics["jaccard"] - control_metrics["jaccard"]
        delta_ddi = rx_metrics["ddi"] - control_metrics["ddi"]
        signal = (
            "PATIENT_CONDITIONAL_MOE_SIGNAL"
            if delta_jaccard >= 0.005 or (delta_jaccard >= 0.0 and delta_ddi <= -0.010)
            else "MOE_NOT_PRIMARY_SIGNAL"
        )
        result["RxExpert-NoMoE"] = {
            "metrics": control_metrics,
            "parameter_count": parameter_count(control),
            "training_seconds": control_seconds,
            "loss": control_losses,
            "delta_RxExpert_minus_NoMoE": {
                "jaccard": delta_jaccard,
                "f1": rx_metrics["f1"] - control_metrics["f1"],
                "prauc": rx_metrics["prauc"] - control_metrics["prauc"],
                "ddi": delta_ddi,
                "mean_medication_count": rx_metrics["mean_medication_count"]
                - control_metrics["mean_medication_count"],
            },
            "mechanism_verdict": signal,
        }
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--official-source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    args = parser.parse_args()
    result = run(args)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "official_source_revision",
                    "metrics",
                    "fidelity_verdict",
                    "terminal_verdict",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
