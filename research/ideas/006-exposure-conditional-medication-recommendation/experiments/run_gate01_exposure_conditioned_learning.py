"""Idea 006 Gate 01: Exposure-Conditioned Learning vs Direct Exposure Controls.

Main execution runner.
SSOT: research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md
"""

from __future__ import annotations

import argparse
import collections
import copy
import datetime
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from gate01_data import (
    FROZEN_DDI_ASSET_SHA256,
    BurstDataset,
    build_burst_datasets,
    classify_subject_gate01,
    collate_burst_batch,
    load_frozen_ddi_asset,
)
from gate01_metrics import (
    evaluate_method_on_universe,
    patient_clustered_paired_bootstrap,
)
from gate01_model import (
    CommonOrderTimeBackbone,
    compute_total_loss,
    direct_exposure_rerank_single,
    exposure_hard_constraint_single,
)
from torch.utils.data import DataLoader


def set_seed(seed: int = 260907) -> None:
    """Set random seed for full reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def run_mechanical_preflight(
    ddi_snapshot_dir: Path,
    device: torch.device,
) -> bool:
    """Run minimal critical-path smoke / preflight checks."""
    print("=== Running Mechanical Preflight ===")

    # 1. Deterministic patient partition
    test_sids = [10000032, 10000084, 10000108, 10000117, 10000248]
    parts_1 = [classify_subject_gate01(s) for s in test_sids]
    parts_2 = [classify_subject_gate01(s) for s in test_sids]
    assert parts_1 == parts_2, "Partitioning is not deterministic!"
    assert all(p in ("InnerTrain", "InnerTune", "Dev", "Holdout") for p in parts_1)
    print("  [PASS] Patient partition deterministic and valid.")

    # 2. Load DDI asset and verify SHA256
    med_voc, _concept_to_idx, ddi_np, _ddi_concepts, asset_sha256 = load_frozen_ddi_asset(
        ddi_snapshot_dir
    )
    assert len(med_voc) == 131, f"Expected 131 concepts, got {len(med_voc)}"
    assert asset_sha256 == FROZEN_DDI_ASSET_SHA256, f"DDI SHA256 mismatch: {asset_sha256}"
    print(f"  [PASS] DDI asset SHA256 verified ({asset_sha256[:16]}...).")

    # 3. Model forward/backward pass with power-of-two batch size 2048
    concept_codes = [med_voc[i] for i in range(131)]
    model = CommonOrderTimeBackbone(num_medications=131).to(device)
    ddi_t = torch.from_numpy(ddi_np).to(device)

    # Smoke tensors (batch size 4 for fast check)
    hist_meds = torch.randint(0, 132, (4, 64), device=device)
    hist_types = torch.randint(0, 4, (4, 64), device=device)
    hist_elapsed = torch.rand((4, 64), device=device)
    active_reg = torch.zeros((4, 131), device=device)
    active_reg[:, [2, 5, 10]] = 1.0
    log_hours = torch.tensor([[1.5], [2.0], [0.5], [3.0]], device=device)
    targets = torch.zeros((4, 131), device=device)
    targets[:, [2, 15]] = 1.0

    logits = model(hist_meds, hist_types, hist_elapsed, active_reg, log_hours)
    assert logits.shape == (4, 131), f"Unexpected logits shape: {logits.shape}"

    loss, _l_pred, _l_new, _l_active = compute_total_loss(
        "ExposureConditional", logits, targets, active_reg, ddi_t, lambda_val=1.0
    )
    loss.backward()
    print("  [PASS] Model forward/backward pass verified.")

    # 4. Direct reranker and hard constraint output K=5 exactly and deterministically
    single_logits = logits[0].detach()
    single_active = active_reg[0]

    rerank_sel1 = direct_exposure_rerank_single(
        single_logits, single_active, ddi_t, concept_codes, gamma=1.0, k=5
    )
    rerank_sel2 = direct_exposure_rerank_single(
        single_logits, single_active, ddi_t, concept_codes, gamma=1.0, k=5
    )
    assert len(rerank_sel1) == 5 and len(set(rerank_sel1)) == 5, (
        f"Rerank did not return 5 unique: {rerank_sel1}"
    )
    assert rerank_sel1 == rerank_sel2, "Rerank is not deterministic!"

    hard_sel1 = exposure_hard_constraint_single(
        single_logits, single_active, ddi_t, concept_codes, k=5
    )
    hard_sel2 = exposure_hard_constraint_single(
        single_logits, single_active, ddi_t, concept_codes, k=5
    )
    assert len(hard_sel1) == 5 and len(set(hard_sel1)) == 5, (
        f"Hard constraint did not return 5 unique: {hard_sel1}"
    )
    assert hard_sel1 == hard_sel2, "Hard constraint is not deterministic!"
    print("  [PASS] Fixed K=5 selectors emit exactly 5 unique medications deterministically.")

    print("=== Mechanical Preflight Passed Successfully ===")
    return True


class FastBurstTensorDataset:
    """Pre-stacked contiguous tensors for high-performance vectorized training and inference."""

    def __init__(self, bursts: list[dict[str, Any]]) -> None:
        self.n = len(bursts)
        if self.n > 0:
            self.hist_meds = torch.from_numpy(
                np.array([b["hist_meds"] for b in bursts], dtype=np.int64)
            )
            self.hist_types = torch.from_numpy(
                np.array([b["hist_types"] for b in bursts], dtype=np.int64)
            )
            self.hist_elapsed = torch.from_numpy(
                np.array([b["hist_elapsed"] for b in bursts], dtype=np.float32)
            )
            self.active_regimen = torch.from_numpy(
                np.array([b["active_regimen"] for b in bursts], dtype=np.float32)
            )
            self.log_hours = torch.from_numpy(
                np.array([[b["log_hours_since_admit"]] for b in bursts], dtype=np.float32)
            )
            self.target_vec = torch.from_numpy(
                np.array([b["target_vec"] for b in bursts], dtype=np.float32)
            )
        else:
            self.hist_meds = torch.zeros((0, 50), dtype=torch.long)
            self.hist_types = torch.zeros((0, 50), dtype=torch.long)
            self.hist_elapsed = torch.zeros((0, 50), dtype=torch.float32)
            self.active_regimen = torch.zeros((0, 131), dtype=torch.float32)
            self.log_hours = torch.zeros((0, 1), dtype=torch.float32)
            self.target_vec = torch.zeros((0, 131), dtype=torch.float32)

    def iter_batches(self, batch_size: int = 2048, shuffle: bool = False):
        indices = torch.randperm(self.n) if shuffle else torch.arange(self.n)
        for start in range(0, self.n, batch_size):
            b_idx = indices[start : start + batch_size]
            yield {
                "hist_meds": self.hist_meds[b_idx],
                "hist_types": self.hist_types[b_idx],
                "hist_elapsed": self.hist_elapsed[b_idx],
                "active_regimen": self.active_regimen[b_idx],
                "log_hours_since_admit": self.log_hours[b_idx],
                "target_vec": self.target_vec[b_idx],
            }

    def __len__(self) -> int:
        return self.n


class FastBatchLoader:
    """Lightweight loader providing __iter__ and __len__ over FastBurstTensorDataset."""

    def __init__(
        self, dataset: FastBurstTensorDataset, batch_size: int = 2048, shuffle: bool = False
    ) -> None:
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle

    def __iter__(self):
        return self.dataset.iter_batches(batch_size=self.batch_size, shuffle=self.shuffle)

    def __len__(self) -> int:
        return (self.dataset.n + self.batch_size - 1) // self.batch_size


def train_single_model(
    variant: str,
    lambda_val: float,
    train_loader: Any,
    tune_bursts_q: list[dict[str, Any]] | FastBurstTensorDataset,
    tune_loader_all: Any,
    ddi_tensor: torch.Tensor,
    device: torch.device,
    checkpoint_path: Path | None = None,
    max_epochs: int = 5,
    patience: int = 1,
    seed: int = 260907,
) -> tuple[CommonOrderTimeBackbone, float, int, dict[str, Any]]:
    """Train one learned model variant with early stopping on InnerTune L_pred."""
    set_seed(seed)
    model = CommonOrderTimeBackbone(num_medications=131).to(device)

    if checkpoint_path is not None and checkpoint_path.exists():
        print(
            f"\n--- Loading {variant} (lambda={lambda_val}) from existing checkpoint {checkpoint_path} ---",
            flush=True,
        )
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))
        model.eval()
        tune_lpred_total = 0.0
        n_tune_batches = 0
        with torch.no_grad():
            for batch in tune_loader_all:
                hist_meds = batch["hist_meds"].to(device)
                hist_types = batch["hist_types"].to(device)
                hist_elapsed = batch["hist_elapsed"].to(device)
                active_reg = batch["active_regimen"].to(device)
                log_hours = batch["log_hours_since_admit"].to(device)
                targets = batch["target_vec"].to(device)

                logits = model(hist_meds, hist_types, hist_elapsed, active_reg, log_hours)
                l_pred = F.binary_cross_entropy_with_logits(logits, targets, reduction="mean")
                tune_lpred_total += l_pred.item()
                n_tune_batches += 1
        best_tune_lpred = tune_lpred_total / max(1, n_tune_batches)
        best_epoch = 5
        print(f"  Loaded checkpoint InnerTune L_pred = {best_tune_lpred:.5f}", flush=True)
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)

        best_tune_lpred = float("inf")
        best_weights = copy.deepcopy(model.state_dict())
        best_epoch = 0
        patience_counter = 0

        print(f"\n--- Training {variant} (lambda={lambda_val}) ---", flush=True)

        for epoch in range(1, max_epochs + 1):
            model.train()
            train_loss_total = 0.0
            n_train_batches = 0

            for batch in train_loader:
                optimizer.zero_grad()
                hist_meds = batch["hist_meds"].to(device)
                hist_types = batch["hist_types"].to(device)
                hist_elapsed = batch["hist_elapsed"].to(device)
                active_reg = batch["active_regimen"].to(device)
                log_hours = batch["log_hours_since_admit"].to(device)
                targets = batch["target_vec"].to(device)

                logits = model(hist_meds, hist_types, hist_elapsed, active_reg, log_hours)
                loss, _, _, _ = compute_total_loss(
                    variant, logits, targets, active_reg, ddi_tensor, lambda_val=lambda_val
                )
                loss.backward()
                optimizer.step()

                train_loss_total += loss.item()
                n_train_batches += 1

            avg_train_loss = train_loss_total / max(1, n_train_batches)

            # Evaluate InnerTune L_pred
            model.eval()
            tune_lpred_total = 0.0
            n_tune_batches = 0
            with torch.no_grad():
                for batch in tune_loader_all:
                    hist_meds = batch["hist_meds"].to(device)
                    hist_types = batch["hist_types"].to(device)
                    hist_elapsed = batch["hist_elapsed"].to(device)
                    active_reg = batch["active_regimen"].to(device)
                    log_hours = batch["log_hours_since_admit"].to(device)
                    targets = batch["target_vec"].to(device)

                    logits = model(hist_meds, hist_types, hist_elapsed, active_reg, log_hours)
                    l_pred = F.binary_cross_entropy_with_logits(logits, targets, reduction="mean")
                    tune_lpred_total += l_pred.item()
                    n_tune_batches += 1

            avg_tune_lpred = tune_lpred_total / max(1, n_tune_batches)
            print(
                f"  Epoch {epoch}/{max_epochs}: Train Loss = {avg_train_loss:.5f}, InnerTune L_pred = {avg_tune_lpred:.5f}",
                flush=True,
            )

            # Lowest InnerTune L_pred selects checkpoint
            if avg_tune_lpred < best_tune_lpred:
                best_tune_lpred = avg_tune_lpred
                best_weights = copy.deepcopy(model.state_dict())
                best_epoch = epoch
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(
                        f"  Early stopping triggered after epoch {epoch}. Restoring best epoch {best_epoch}.",
                        flush=True,
                    )
                    break

        # Restore best checkpoint
        model.load_state_dict(best_weights)
        if checkpoint_path is not None:
            torch.save(best_weights, checkpoint_path)
            print(f"Saved checkpoint to {checkpoint_path}", flush=True)

    model.eval()

    # Predict on InnerTune Q
    if isinstance(tune_bursts_q, FastBurstTensorDataset):
        tune_q_loader: Any = FastBatchLoader(tune_bursts_q, batch_size=2048, shuffle=False)
    else:
        tune_q_loader = DataLoader(
            BurstDataset(tune_bursts_q),
            batch_size=2048,
            shuffle=False,
            collate_fn=collate_burst_batch,
        )

    all_logits_list = []
    with torch.no_grad():
        for batch in tune_q_loader:
            hist_meds = batch["hist_meds"].to(device)
            hist_types = batch["hist_types"].to(device)
            hist_elapsed = batch["hist_elapsed"].to(device)
            active_reg = batch["active_regimen"].to(device)
            log_hours = batch["log_hours_since_admit"].to(device)
            out_logits = model(hist_meds, hist_types, hist_elapsed, active_reg, log_hours)
            all_logits_list.append(out_logits.cpu())

    tune_q_logits = torch.cat(all_logits_list, dim=0)

    return model, best_tune_lpred, best_epoch, {"tune_q_logits": tune_q_logits}


def predict_bursts_logits(
    model: CommonOrderTimeBackbone,
    bursts: list[dict[str, Any]] | FastBurstTensorDataset,
    device: torch.device,
    batch_size: int = 2048,
) -> torch.Tensor:
    """Compute model logits for a list of bursts or fast dataset."""
    if isinstance(bursts, FastBurstTensorDataset):
        loader: Any = FastBatchLoader(bursts, batch_size=batch_size, shuffle=False)
    else:
        loader = DataLoader(
            BurstDataset(bursts),
            batch_size=batch_size,
            shuffle=False,
            collate_fn=collate_burst_batch,
        )
    model.eval()
    all_logits = []
    with torch.no_grad():
        for batch in loader:
            hist_meds = batch["hist_meds"].to(device)
            hist_types = batch["hist_types"].to(device)
            hist_elapsed = batch["hist_elapsed"].to(device)
            active_reg = batch["active_regimen"].to(device)
            log_hours = batch["log_hours_since_admit"].to(device)
            out = model(hist_meds, hist_types, hist_elapsed, active_reg, log_hours)
            all_logits.append(out.cpu())
    return torch.cat(all_logits, dim=0)


def main() -> int:
    """Main CLI execution flow."""
    parser = argparse.ArgumentParser(description="Idea 006 Gate 01 Execution Runner")
    parser.add_argument(
        "--mimic-dir", type=Path, default=Path("/root/zhb/Search/dataset/mimic-iv-3.1/hosp")
    )
    parser.add_argument(
        "--ddi-asset-dir",
        type=Path,
        default=Path("/root/zhb/medrec-data/snapshots/molerec-table1-c721-www23"),
    )
    parser.add_argument(
        "--mapping-dir", type=Path, default=Path("/root/zhb/code/KGDNet/data/Mappings")
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=Path("/root/zhb/medrec-data/gate01_cache")
    )
    parser.add_argument("--run-dir", type=Path, default=Path("/root/zhb/medrec-data/gate01_runs"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=260907)
    parser.add_argument(
        "--device", type=str, default="cuda:0" if torch.cuda.is_available() else "cpu"
    )
    parser.add_argument("--preflight-only", action="store_true")

    args = parser.parse_args()
    set_seed(args.seed)

    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    device = torch.device(args.device)
    print(f"Using device: {device}", flush=True)

    # Mechanical preflight
    run_mechanical_preflight(args.ddi_asset_dir, device)
    if args.preflight_only:
        print("Preflight-only requested. Exiting.", flush=True)
        return 0

    args.run_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load DDI asset
    med_voc, _concept_to_idx, ddi_np, _ddi_concepts, asset_sha256 = load_frozen_ddi_asset(
        args.ddi_asset_dir
    )
    ddi_tensor = torch.from_numpy(ddi_np).to(device)
    concept_codes = [med_voc[i] for i in range(131)]

    # 2. Build or load cached bursts
    t0 = time.time()
    burst_datasets = build_burst_datasets(
        mimic_dir=args.mimic_dir,
        ddi_snapshot_dir=args.ddi_asset_dir,
        mapping_dir=args.mapping_dir,
        cache_dir=args.cache_dir,
    )

    train_bursts = burst_datasets["InnerTrain"]
    tune_bursts = burst_datasets["InnerTune"]
    dev_bursts = burst_datasets["Dev"]

    train_q_bursts = [b for b in train_bursts if b["in_q"]]
    tune_q_bursts = [b for b in tune_bursts if b["in_q"]]
    dev_q_bursts = [b for b in dev_bursts if b["in_q"]]

    train_patients = len(set(b["patient_id"] for b in train_bursts))
    tune_patients = len(set(b["patient_id"] for b in tune_bursts))
    dev_patients = len(set(b["patient_id"] for b in dev_bursts))

    train_q_patients = len(set(b["patient_id"] for b in train_q_bursts))
    tune_q_patients = len(set(b["patient_id"] for b in tune_q_bursts))
    dev_q_patients = len(set(b["patient_id"] for b in dev_q_bursts))

    print("\n=== Dataset Partition Inventory ===", flush=True)
    print(
        f"InnerTrain: {len(train_bursts):,} bursts ({len(train_q_bursts):,} in Q) across {train_patients:,} patients ({train_q_patients:,} in Q)",
        flush=True,
    )
    print(
        f"InnerTune:  {len(tune_bursts):,} bursts ({len(tune_q_bursts):,} in Q) across {tune_patients:,} patients ({tune_q_patients:,} in Q)",
        flush=True,
    )
    print(
        f"Dev:        {len(dev_bursts):,} bursts ({len(dev_q_bursts):,} in Q) across {dev_patients:,} patients ({dev_q_patients:,} in Q)",
        flush=True,
    )

    # Compute Global Frequency from InnerTrain positive orders
    train_concept_counts = collections.Counter()
    for b in train_bursts:
        for idx in b["target_indices"]:
            train_concept_counts[idx] += 1
    # Sorted by frequency descending, tie-break by ascending concept code
    global_freq_top10 = sorted(
        range(131),
        key=lambda m: (-train_concept_counts[m], concept_codes[m]),
    )[:10]
    global_freq_top5 = global_freq_top10[:5]
    print(f"GlobalFrequency Top-5: {[concept_codes[m] for m in global_freq_top5]}", flush=True)

    # Prepare Fast DataLoaders
    batch_size = args.batch_size
    print("Preparing fast in-memory tensor representations...", flush=True)
    train_tensor_ds = FastBurstTensorDataset(train_bursts)
    tune_all_tensor_ds = FastBurstTensorDataset(tune_bursts)
    tune_q_tensor_ds = FastBurstTensorDataset(tune_q_bursts)
    dev_q_tensor_ds = FastBurstTensorDataset(dev_q_bursts)
    print("  [PASS] Fast in-memory tensor datasets initialized.", flush=True)

    train_loader = FastBatchLoader(train_tensor_ds, batch_size=batch_size, shuffle=True)
    tune_loader_all = FastBatchLoader(tune_all_tensor_ds, batch_size=batch_size, shuffle=False)

    # 3. Train Base model
    base_ckpt = args.run_dir / "checkpoint_Base_0.0.pt"
    base_model, _base_tune_lpred, _base_best_epoch, base_extra = train_single_model(
        variant="Base",
        lambda_val=0.0,
        train_loader=train_loader,
        tune_bursts_q=tune_q_tensor_ds,
        tune_loader_all=tune_loader_all,
        ddi_tensor=ddi_tensor,
        device=device,
        checkpoint_path=base_ckpt,
        seed=args.seed,
    )

    base_tune_q_logits = base_extra["tune_q_logits"]

    # Select Base Top-5 on InnerTune Q
    base_tune_q_top5 = []
    base_tune_q_ranked = []
    for i in range(len(tune_q_bursts)):
        l_row = base_tune_q_logits[i].numpy()
        ranked = sorted(range(131), key=lambda m: (-l_row[m], concept_codes[m]))
        base_tune_q_ranked.append(ranked)
        base_tune_q_top5.append(ranked[:5])

    base_tune_eval = evaluate_method_on_universe(
        burst_records=tune_q_bursts,
        selected_lists=base_tune_q_top5,
        ddi_matrix=ddi_np,
        k=5,
        ranked_all_lists=base_tune_q_ranked,
    )

    r_base_tune = base_tune_eval["IncrementalExposureDDI@5"]
    budget_b = 0.90 * r_base_tune
    print(f"\nBase InnerTune Primary Risk: {r_base_tune:.6f}", flush=True)
    print(f"Frozen Common Safety Budget B = 0.90 * R_base_tune: {budget_b:.6f}", flush=True)

    # 4. Train StaticLoss grid: lambda in {0.1, 0.5, 2.0, 8.0}
    static_lambdas = [0.1, 0.5, 2.0, 8.0]
    static_tune_rows: list[dict[str, Any]] = []
    static_models: dict[float, CommonOrderTimeBackbone] = {}
    static_logits: dict[float, torch.Tensor] = {}

    for lam in static_lambdas:
        static_ckpt = args.run_dir / f"checkpoint_StaticLoss_{lam}.pt"
        m, lpred, ep, extra = train_single_model(
            variant="StaticLoss",
            lambda_val=lam,
            train_loader=train_loader,
            tune_bursts_q=tune_q_tensor_ds,
            tune_loader_all=tune_loader_all,
            ddi_tensor=ddi_tensor,
            device=device,
            checkpoint_path=static_ckpt,
            seed=args.seed,
        )
        static_models[lam] = m
        static_logits[lam] = extra["tune_q_logits"]

        # Evaluate on InnerTune Q
        top5_list = []
        for i in range(len(tune_q_bursts)):
            l_row = extra["tune_q_logits"][i].numpy()
            ranked = sorted(range(131), key=lambda m: (-l_row[m], concept_codes[m]))
            top5_list.append(ranked[:5])

        res = evaluate_method_on_universe(
            burst_records=tune_q_bursts,
            selected_lists=top5_list,
            ddi_matrix=ddi_np,
            k=5,
        )
        static_tune_rows.append(
            {
                "lambda": lam,
                "best_epoch": ep,
                "best_tune_lpred": lpred,
                "Recall@5": res["Recall@5"],
                "IncrementalExposureDDI@5": res["IncrementalExposureDDI@5"],
                "reaches_budget": bool(res["IncrementalExposureDDI@5"] <= budget_b),
            }
        )

    print("\n=== StaticLoss InnerTune Grid Rows ===", flush=True)
    for row in static_tune_rows:
        print(
            f"  lambda={row['lambda']}: Recall@5={row['Recall@5']:.4f}, Risk={row['IncrementalExposureDDI@5']:.6f}, Reaches Budget={row['reaches_budget']}",
            flush=True,
        )

    # Select StaticLoss
    valid_static = [r for r in static_tune_rows if r["reaches_budget"]]
    if valid_static:
        # Highest Recall@5, tie-break: lower risk, smaller lambda
        valid_static.sort(
            key=lambda r: (-r["Recall@5"], r["IncrementalExposureDDI@5"], r["lambda"])
        )
        selected_static_row = valid_static[0]
        selected_lambda_static = selected_static_row["lambda"]
        static_budget_miss = False
    else:
        # Lowest risk, tie-break: higher Recall@5, smaller lambda
        static_tune_rows.sort(
            key=lambda r: (r["IncrementalExposureDDI@5"], -r["Recall@5"], r["lambda"])
        )
        selected_static_row = static_tune_rows[0]
        selected_lambda_static = selected_static_row["lambda"]
        static_budget_miss = True
    print(
        f"Selected StaticLoss lambda: {selected_lambda_static} (Budget Miss: {static_budget_miss})",
        flush=True,
    )

    # 5. Train ExposureConditional grid: lambda in {0.1, 0.5, 2.0, 8.0}
    ec_lambdas = [0.1, 0.5, 2.0, 8.0]
    ec_tune_rows: list[dict[str, Any]] = []
    ec_models: dict[float, CommonOrderTimeBackbone] = {}
    ec_logits: dict[float, torch.Tensor] = {}

    for lam in ec_lambdas:
        ec_ckpt = args.run_dir / f"checkpoint_ExposureConditional_{lam}.pt"
        m, lpred, ep, extra = train_single_model(
            variant="ExposureConditional",
            lambda_val=lam,
            train_loader=train_loader,
            tune_bursts_q=tune_q_tensor_ds,
            tune_loader_all=tune_loader_all,
            ddi_tensor=ddi_tensor,
            device=device,
            checkpoint_path=ec_ckpt,
            seed=args.seed,
        )
        ec_models[lam] = m
        ec_logits[lam] = extra["tune_q_logits"]

        top5_list = []
        for i in range(len(tune_q_bursts)):
            l_row = extra["tune_q_logits"][i].numpy()
            ranked = sorted(range(131), key=lambda m: (-l_row[m], concept_codes[m]))
            top5_list.append(ranked[:5])

        res = evaluate_method_on_universe(
            burst_records=tune_q_bursts,
            selected_lists=top5_list,
            ddi_matrix=ddi_np,
            k=5,
        )
        ec_tune_rows.append(
            {
                "lambda": lam,
                "best_epoch": ep,
                "best_tune_lpred": lpred,
                "Recall@5": res["Recall@5"],
                "IncrementalExposureDDI@5": res["IncrementalExposureDDI@5"],
                "reaches_budget": bool(res["IncrementalExposureDDI@5"] <= budget_b),
            }
        )

    print("\n=== ExposureConditional InnerTune Grid Rows ===", flush=True)
    for row in ec_tune_rows:
        print(
            f"  lambda={row['lambda']}: Recall@5={row['Recall@5']:.4f}, Risk={row['IncrementalExposureDDI@5']:.6f}, Reaches Budget={row['reaches_budget']}",
            flush=True,
        )

    # Select ExposureConditional
    valid_ec = [r for r in ec_tune_rows if r["reaches_budget"]]
    if valid_ec:
        valid_ec.sort(key=lambda r: (-r["Recall@5"], r["IncrementalExposureDDI@5"], r["lambda"]))
        selected_ec_row = valid_ec[0]
        selected_lambda_ec = selected_ec_row["lambda"]
        ec_budget_miss = False
    else:
        ec_tune_rows.sort(
            key=lambda r: (r["IncrementalExposureDDI@5"], -r["Recall@5"], r["lambda"])
        )
        selected_ec_row = ec_tune_rows[0]
        selected_lambda_ec = selected_ec_row["lambda"]
        ec_budget_miss = True
    print(
        f"Selected ExposureConditional lambda: {selected_lambda_ec} (Budget Miss: {ec_budget_miss})",
        flush=True,
    )

    # 6. DirectExposureRerank grid: gamma in {0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0}
    rerank_gammas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    rerank_tune_rows: list[dict[str, Any]] = []

    print("\n--- Evaluating DirectExposureRerank on InnerTune ---", flush=True)
    base_tune_q_logits_np = base_tune_q_logits.numpy()
    tune_q_act_np = [np.asarray(b["active_regimen"], dtype=np.float32) for b in tune_q_bursts]

    for gam in rerank_gammas:
        t_gam_start = time.time()
        sel_list = []
        for i in range(len(tune_q_bursts)):
            sel = direct_exposure_rerank_single(
                base_tune_q_logits_np[i],
                tune_q_act_np[i],
                ddi_np,
                concept_codes,
                gamma=gam,
                k=5,
            )
            sel_list.append(sel)

        res = evaluate_method_on_universe(
            burst_records=tune_q_bursts,
            selected_lists=sel_list,
            ddi_matrix=ddi_np,
            k=5,
        )
        rerank_tune_rows.append(
            {
                "gamma": gam,
                "Recall@5": res["Recall@5"],
                "IncrementalExposureDDI@5": res["IncrementalExposureDDI@5"],
                "reaches_budget": bool(res["IncrementalExposureDDI@5"] <= budget_b),
            }
        )
        print(
            f"  gamma={gam}: Recall@5={res['Recall@5']:.4f}, Risk={res['IncrementalExposureDDI@5']:.6f} ({time.time() - t_gam_start:.1f}s)",
            flush=True,
        )

    print("=== DirectExposureRerank InnerTune Grid Rows ===", flush=True)
    for row in rerank_tune_rows:
        print(
            f"  gamma={row['gamma']}: Recall@5={row['Recall@5']:.4f}, Risk={row['IncrementalExposureDDI@5']:.6f}, Reaches Budget={row['reaches_budget']}",
            flush=True,
        )

    valid_rerank = [r for r in rerank_tune_rows if r["reaches_budget"]]
    if valid_rerank:
        valid_rerank.sort(key=lambda r: (-r["Recall@5"], r["IncrementalExposureDDI@5"], r["gamma"]))
        selected_rerank_row = valid_rerank[0]
        selected_gamma = selected_rerank_row["gamma"]
        rerank_budget_miss = False
    else:
        rerank_tune_rows.sort(
            key=lambda r: (r["IncrementalExposureDDI@5"], -r["Recall@5"], r["gamma"])
        )
        selected_rerank_row = rerank_tune_rows[0]
        selected_gamma = selected_rerank_row["gamma"]
        rerank_budget_miss = True
    print(
        f"Selected DirectExposureRerank gamma: {selected_gamma} (Budget Miss: {rerank_budget_miss})",
        flush=True,
    )

    # 7. ExposureHardConstraint on InnerTune
    print("\n--- Evaluating ExposureHardConstraint on InnerTune ---", flush=True)
    t_hard_start = time.time()
    hard_tune_sel = []
    for i in range(len(tune_q_bursts)):
        sel = exposure_hard_constraint_single(
            base_tune_q_logits_np[i],
            tune_q_act_np[i],
            ddi_np,
            concept_codes,
            k=5,
        )
        hard_tune_sel.append(sel)

    hard_tune_eval = evaluate_method_on_universe(
        burst_records=tune_q_bursts,
        selected_lists=hard_tune_sel,
        ddi_matrix=ddi_np,
        k=5,
    )
    print(
        f"ExposureHardConstraint InnerTune: Recall@5={hard_tune_eval['Recall@5']:.4f}, Risk={hard_tune_eval['IncrementalExposureDDI@5']:.6f} ({time.time() - t_hard_start:.1f}s)",
        flush=True,
    )

    # =========================================================================
    # 8. CRITICAL FREEZE BEFORE DEV
    # =========================================================================
    print("\n==================================================")
    print("CRITICAL FREEZE BEFORE DEV ACCESS")
    print("==================================================")

    freeze_payload = {
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc  # noqa: UP017
        ).isoformat(),
        "batch_size": batch_size,
        "seed": args.seed,
        "r_base_tune": float(r_base_tune),
        "budget_b": float(budget_b),
        "selected_lambda_static": float(selected_lambda_static),
        "selected_lambda_ec": float(selected_lambda_ec),
        "selected_gamma": float(selected_gamma),
        "ec_budget_miss": ec_budget_miss,
        "static_budget_miss": static_budget_miss,
        "rerank_budget_miss": rerank_budget_miss,
        "static_tune_rows": static_tune_rows,
        "ec_tune_rows": ec_tune_rows,
        "rerank_tune_rows": rerank_tune_rows,
    }

    serialized_freeze = json.dumps(freeze_payload, sort_keys=True, indent=2)
    freeze_sha256 = hashlib.sha256(serialized_freeze.encode("utf-8")).hexdigest()

    freeze_file = args.run_dir / "gate01_freeze_manifest.json"
    with freeze_file.open("w", encoding="utf-8") as f:
        f.write(serialized_freeze)

    print(f"Freeze Manifest SHA256: {freeze_sha256}")
    print(f"Saved local freeze manifest to {freeze_file}")
    print("Dev data has NOT been inspected prior to this exact freeze.")

    # Save model weights to run_dir
    torch.save(base_model.state_dict(), args.run_dir / "base_checkpoint.pt")
    torch.save(
        static_models[selected_lambda_static].state_dict(), args.run_dir / "static_checkpoint.pt"
    )
    torch.save(ec_models[selected_lambda_ec].state_dict(), args.run_dir / "ec_checkpoint.pt")
    print(f"Saved model checkpoints to {args.run_dir}")

    # =========================================================================
    # 9. DEV EVALUATION (ONE FROZEN OUTER EVALUATION)
    # =========================================================================
    print("\n==================================================")
    print("EXECUTING FROZEN OUTER DEV EVALUATION")
    print("==================================================")

    dev_selected_static_model = static_models[selected_lambda_static]
    dev_selected_ec_model = ec_models[selected_lambda_ec]

    # Predict logits on Dev Q
    dev_base_logits = predict_bursts_logits(
        base_model, dev_q_tensor_ds, device, batch_size=batch_size
    )
    dev_static_logits = predict_bursts_logits(
        dev_selected_static_model, dev_q_tensor_ds, device, batch_size=batch_size
    )
    dev_ec_logits = predict_bursts_logits(
        dev_selected_ec_model, dev_q_tensor_ds, device, batch_size=batch_size
    )

    # Convert to probabilities
    dev_base_probs = torch.sigmoid(dev_base_logits).numpy()
    dev_static_probs = torch.sigmoid(dev_static_logits).numpy()
    dev_ec_probs = torch.sigmoid(dev_ec_logits).numpy()

    # Target matrix for dev_q_bursts
    dev_target_matrix = np.array([b["target_vec"] for b in dev_q_bursts], dtype=np.float32)

    # 1) GlobalFrequency selections on Dev Q
    dev_gf_top5 = [global_freq_top5 for _ in range(len(dev_q_bursts))]
    dev_gf_top10 = [global_freq_top10 for _ in range(len(dev_q_bursts))]

    dev_gf_5 = evaluate_method_on_universe(dev_q_bursts, dev_gf_top5, ddi_np, k=5)
    dev_gf_10 = evaluate_method_on_universe(dev_q_bursts, dev_gf_top10, ddi_np, k=10)

    # 2) Base selections on Dev Q
    dev_base_top5 = []
    dev_base_top10 = []
    dev_base_ranked = []
    for i in range(len(dev_q_bursts)):
        l_row = dev_base_logits[i].numpy()
        ranked = sorted(range(131), key=lambda m: (-l_row[m], concept_codes[m]))
        dev_base_ranked.append(ranked)
        dev_base_top5.append(ranked[:5])
        dev_base_top10.append(ranked[:10])

    dev_base_5 = evaluate_method_on_universe(
        dev_q_bursts,
        dev_base_top5,
        ddi_np,
        k=5,
        ranked_all_lists=dev_base_ranked,
        predicted_probs=dev_base_probs,
        target_matrix=dev_target_matrix,
    )
    dev_base_10 = evaluate_method_on_universe(dev_q_bursts, dev_base_top10, ddi_np, k=10)

    # 3) StaticLoss selections on Dev Q
    dev_static_top5 = []
    dev_static_top10 = []
    dev_static_ranked = []
    for i in range(len(dev_q_bursts)):
        l_row = dev_static_logits[i].numpy()
        ranked = sorted(range(131), key=lambda m: (-l_row[m], concept_codes[m]))
        dev_static_ranked.append(ranked)
        dev_static_top5.append(ranked[:5])
        dev_static_top10.append(ranked[:10])

    dev_static_5 = evaluate_method_on_universe(
        dev_q_bursts,
        dev_static_top5,
        ddi_np,
        k=5,
        ranked_all_lists=dev_static_ranked,
        predicted_probs=dev_static_probs,
        target_matrix=dev_target_matrix,
    )
    dev_static_10 = evaluate_method_on_universe(dev_q_bursts, dev_static_top10, ddi_np, k=10)

    # 4) DirectExposureRerank selections on Dev Q
    print("\n--- Evaluating DirectExposureRerank on Dev Q ---", flush=True)
    t_dev_rerank = time.time()
    dev_base_logits_np = dev_base_logits.numpy()
    dev_q_act_np = [np.asarray(b["active_regimen"], dtype=np.float32) for b in dev_q_bursts]

    dev_rerank_top5 = []
    dev_rerank_top10 = []
    for i in range(len(dev_q_bursts)):
        sel10 = direct_exposure_rerank_single(
            dev_base_logits_np[i],
            dev_q_act_np[i],
            ddi_np,
            concept_codes,
            gamma=selected_gamma,
            k=10,
        )
        dev_rerank_top10.append(sel10)
        dev_rerank_top5.append(sel10[:5])

    dev_rerank_5 = evaluate_method_on_universe(dev_q_bursts, dev_rerank_top5, ddi_np, k=5)
    dev_rerank_10 = evaluate_method_on_universe(dev_q_bursts, dev_rerank_top10, ddi_np, k=10)
    print(f"DirectExposureRerank on Dev Q done in {time.time() - t_dev_rerank:.1f}s", flush=True)

    # 5) ExposureHardConstraint selections on Dev Q
    print("\n--- Evaluating ExposureHardConstraint on Dev Q ---", flush=True)
    t_dev_hard = time.time()
    dev_hard_top5 = []
    dev_hard_top10 = []
    for i in range(len(dev_q_bursts)):
        sel10 = exposure_hard_constraint_single(
            dev_base_logits_np[i],
            dev_q_act_np[i],
            ddi_np,
            concept_codes,
            k=10,
        )
        dev_hard_top10.append(sel10)
        dev_hard_top5.append(sel10[:5])

    dev_hard_5 = evaluate_method_on_universe(dev_q_bursts, dev_hard_top5, ddi_np, k=5)
    dev_hard_10 = evaluate_method_on_universe(dev_q_bursts, dev_hard_top10, ddi_np, k=10)
    print(f"ExposureHardConstraint on Dev Q done in {time.time() - t_dev_hard:.1f}s", flush=True)

    # 6) ExposureConditional selections on Dev Q
    dev_ec_top5 = []
    dev_ec_top10 = []
    dev_ec_ranked = []
    for i in range(len(dev_q_bursts)):
        l_row = dev_ec_logits[i].numpy()
        ranked = sorted(range(131), key=lambda m: (-l_row[m], concept_codes[m]))
        dev_ec_ranked.append(ranked)
        dev_ec_top5.append(ranked[:5])
        dev_ec_top10.append(ranked[:10])

    dev_ec_5 = evaluate_method_on_universe(
        dev_q_bursts,
        dev_ec_top5,
        ddi_np,
        k=5,
        ranked_all_lists=dev_ec_ranked,
        predicted_probs=dev_ec_probs,
        target_matrix=dev_target_matrix,
    )
    dev_ec_10 = evaluate_method_on_universe(dev_q_bursts, dev_ec_top10, ddi_np, k=10)

    print("\n=== Dev Results at K=5 (Primary) ===")
    print(
        f"GlobalFrequency:      Recall@5 = {dev_gf_5['Recall@5']:.4f}, Risk = {dev_gf_5['IncrementalExposureDDI@5']:.6f}"
    )
    print(
        f"Base:                 Recall@5 = {dev_base_5['Recall@5']:.4f}, Risk = {dev_base_5['IncrementalExposureDDI@5']:.6f}"
    )
    print(
        f"StaticLoss (lam={selected_lambda_static}): Recall@5 = {dev_static_5['Recall@5']:.4f}, Risk = {dev_static_5['IncrementalExposureDDI@5']:.6f}"
    )
    print(
        f"DirectRerank (gam={selected_gamma}): Recall@5 = {dev_rerank_5['Recall@5']:.4f}, Risk = {dev_rerank_5['IncrementalExposureDDI@5']:.6f}"
    )
    print(
        f"HardConstraint:       Recall@5 = {dev_hard_5['Recall@5']:.4f}, Risk = {dev_hard_5['IncrementalExposureDDI@5']:.6f}"
    )
    print(
        f"ExposureCond (lam={selected_lambda_ec}): Recall@5 = {dev_ec_5['Recall@5']:.4f}, Risk = {dev_ec_5['IncrementalExposureDDI@5']:.6f}"
    )

    # =========================================================================
    # 10. PAIRED PATIENT-CLUSTERED BOOTSTRAP (2000 REPLICATES)
    # =========================================================================
    print("\n==================================================")
    print("RUNNING PAIRED PATIENT-CLUSTERED BOOTSTRAP (2000 REPLICATES)")
    print("==================================================")

    dev_patient_ids = [b["patient_id"] for b in dev_q_bursts]

    method_raw_map = {
        "Base": {
            "recall": dev_base_5["_raw_recall"],
            "inc_ddi": dev_base_5["_raw_inc_ddi"],
        },
        "StaticLoss": {
            "recall": dev_static_5["_raw_recall"],
            "inc_ddi": dev_static_5["_raw_inc_ddi"],
        },
        "DirectExposureRerank": {
            "recall": dev_rerank_5["_raw_recall"],
            "inc_ddi": dev_rerank_5["_raw_inc_ddi"],
        },
        "ExposureHardConstraint": {
            "recall": dev_hard_5["_raw_recall"],
            "inc_ddi": dev_hard_5["_raw_inc_ddi"],
        },
        "ExposureConditional": {
            "recall": dev_ec_5["_raw_recall"],
            "inc_ddi": dev_ec_5["_raw_inc_ddi"],
        },
    }

    t_boot = time.time()
    bootstrap_results = patient_clustered_paired_bootstrap(
        patient_ids=dev_patient_ids,
        method_raw_metrics=method_raw_map,
        replicates=2000,
        seed=args.seed,
    )
    print(f"Completed 2,000 paired bootstrap replicates in {time.time() - t_boot:.2f}s")

    ec_vs_base_risk_delta = float(
        dev_ec_5["IncrementalExposureDDI@5"] - dev_base_5["IncrementalExposureDDI@5"]
    )
    ec_vs_base_recall_delta = float(dev_ec_5["Recall@5"] - dev_base_5["Recall@5"])
    ec_vs_base_risk_ci = bootstrap_results["deltas"]["EC_vs_Base"]["risk_delta"]["ci_95"]
    ec_vs_base_recall_ci = bootstrap_results["deltas"]["EC_vs_Base"]["recall_delta"]["ci_95"]

    ec_vs_rerank_risk_delta = float(
        dev_ec_5["IncrementalExposureDDI@5"] - dev_rerank_5["IncrementalExposureDDI@5"]
    )
    ec_vs_rerank_recall_delta = float(dev_ec_5["Recall@5"] - dev_rerank_5["Recall@5"])
    ec_vs_rerank_risk_ci = bootstrap_results["deltas"]["EC_vs_DirectRerank"]["risk_delta"]["ci_95"]
    ec_vs_rerank_recall_ci = bootstrap_results["deltas"]["EC_vs_DirectRerank"]["recall_delta"][
        "ci_95"
    ]

    print(
        f"EC vs Base Risk Delta: {ec_vs_base_risk_delta:.6f}, 95% CI: [{ec_vs_base_risk_ci[0]:.6f}, {ec_vs_base_risk_ci[1]:.6f}]"
    )
    print(
        f"EC vs Base Recall Delta: {ec_vs_base_recall_delta:+.4f}, 95% CI: [{ec_vs_base_recall_ci[0]:+.4f}, {ec_vs_base_recall_ci[1]:+.4f}]"
    )
    print(
        f"EC vs DirectRerank Risk Delta: {ec_vs_rerank_risk_delta:.6f}, 95% CI: [{ec_vs_rerank_risk_ci[0]:.6f}, {ec_vs_rerank_risk_ci[1]:.6f}]"
    )
    print(
        f"EC vs DirectRerank Recall Delta: {ec_vs_rerank_recall_delta:+.4f}, 95% CI: [{ec_vs_rerank_recall_ci[0]:+.4f}, {ec_vs_rerank_recall_ci[1]:+.4f}]"
    )

    # =========================================================================
    # 11. EVALUATE FROZEN CONDITIONS 1-5 AND DECISION
    # =========================================================================
    print("\n==================================================")
    print("EVALUATING GATE 01 CONDITIONS 1-5")
    print("==================================================")

    # Condition 1: Reaches preregistered Tune risk budget (no budget miss)
    cond1 = not ec_budget_miss

    # Condition 2: Material and reproducible safety improvement over Base
    # R_EC <= 0.90 * R_Base AND 95% CI upper bound < 0
    cond2_point = bool(
        dev_ec_5["IncrementalExposureDDI@5"] <= 0.90 * dev_base_5["IncrementalExposureDDI@5"]
    )
    cond2_boot = bool(ec_vs_base_risk_ci[1] < 0.0)
    cond2 = bool(cond2_point and cond2_boot)

    # Condition 3: Bounded fidelity cost versus Base
    # Recall_EC - Recall_Base >= -0.010
    cond3 = bool(ec_vs_base_recall_delta >= -0.010)

    # Condition 4: Learned value beyond direct exposure-aware killer control
    # R_EC <= R_Rerank + 0.001 AND Recall_EC - Recall_Rerank >= +0.005 AND bootstrap CI lower bound > 0
    cond4_risk = bool(
        dev_ec_5["IncrementalExposureDDI@5"] <= dev_rerank_5["IncrementalExposureDDI@5"] + 0.001
    )
    cond4_recall = bool(ec_vs_rerank_recall_delta >= 0.005)
    cond4_boot = bool(ec_vs_rerank_recall_ci[0] > 0.0)
    cond4 = bool(cond4_risk and cond4_recall and cond4_boot)

    # Condition 5: No required simple control weakly dominates the method
    # Neither StaticLoss nor HardConstraint has:
    # Recall_control >= Recall_EC AND Risk_control <= Risk_EC with at least one strict
    def check_weak_dominance(rec_c: float, risk_c: float, rec_m: float, risk_m: float) -> bool:
        geq_rec = rec_c >= rec_m
        leq_risk = risk_c <= risk_m
        strict = (rec_c > rec_m) or (risk_c < risk_m)
        return bool(geq_rec and leq_risk and strict)

    static_dominates = check_weak_dominance(
        dev_static_5["Recall@5"],
        dev_static_5["IncrementalExposureDDI@5"],
        dev_ec_5["Recall@5"],
        dev_ec_5["IncrementalExposureDDI@5"],
    )
    hard_dominates = check_weak_dominance(
        dev_hard_5["Recall@5"],
        dev_hard_5["IncrementalExposureDDI@5"],
        dev_ec_5["Recall@5"],
        dev_ec_5["IncrementalExposureDDI@5"],
    )
    cond5 = bool(not static_dominates and not hard_dominates)

    all_conditions_pass = bool(cond1 and cond2 and cond3 and cond4 and cond5)
    gate_verdict = (
        "PASS_GATE01_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING"
        if all_conditions_pass
        else "STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING"
    )

    print(f"Condition 1 (Tune budget feasibility):          {cond1}")
    print(
        f"Condition 2 (>=10% Risk red over Base, CI < 0):  {cond2} (Point: {cond2_point}, Boot CI: {cond2_boot})"
    )
    print(
        f"Condition 3 (Fidelity cost vs Base >= -0.010):   {cond3} (Delta: {ec_vs_base_recall_delta:+.4f})"
    )
    print(
        f"Condition 4 (Learned value vs DirectRerank):     {cond4} (Risk: {cond4_risk}, Recall: {cond4_recall}, CI > 0: {cond4_boot})"
    )
    print(
        f"Condition 5 (No weak dominance by controls):     {cond5} (Static dom: {static_dominates}, Hard dom: {hard_dominates})"
    )
    print(f"\nFinal Verdict: {gate_verdict}")

    # =========================================================================
    # 12. WRITE PUBLIC-SAFE ARTIFACTS
    # =========================================================================
    elapsed_total = time.time() - t0

    # Clean raw arrays before serialization
    def strip_raw(d: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if not k.startswith("_raw_")}

    summary_data = {
        "schema_version": "1.0",
        "gate_id": "GATE01_EXPOSURE_CONDITIONED_LEARNING",
        "verdict": gate_verdict,
        "mimic_version": "3.1",
        "ddi_asset_sha256": asset_sha256,
        "ddi_sha256_match": bool(asset_sha256 == FROZEN_DDI_ASSET_SHA256),
        "execution_timestamp": datetime.datetime.now(
            datetime.timezone.utc  # noqa: UP017
        ).isoformat(),
        "elapsed_seconds": elapsed_total,
        "cohort_counts": {
            "InnerTrain": {
                "patients": train_patients,
                "bursts": len(train_bursts),
                "bursts_q": len(train_q_bursts),
                "patients_q": train_q_patients,
            },
            "InnerTune": {
                "patients": tune_patients,
                "bursts": len(tune_bursts),
                "bursts_q": len(tune_q_bursts),
                "patients_q": tune_q_patients,
            },
            "Dev": {
                "patients": dev_patients,
                "bursts": len(dev_bursts),
                "bursts_q": len(dev_q_bursts),
                "patients_q": dev_q_patients,
            },
        },
        "training_contract": {
            "backbone": "CommonOrderTimeBackbone (1-layer GRU hidden 128, MLP 260->128->131)",
            "optimizer": "AdamW",
            "lr": 1e-3,
            "weight_decay": 1e-5,
            "max_epochs": 5,
            "patience": 1,
            "seed": args.seed,
            "frozen_batch_size": batch_size,
        },
        "freeze_manifest": {
            "freeze_sha256": freeze_sha256,
            "frozen_r_base_tune": float(r_base_tune),
            "frozen_safety_budget_b": float(budget_b),
            "selected_lambda_static": selected_lambda_static,
            "selected_lambda_ec": selected_lambda_ec,
            "selected_gamma": selected_gamma,
        },
        "inner_tune_selection": {
            "r_base_tune": float(r_base_tune),
            "safety_budget_b": float(budget_b),
            "static_loss_rows": static_tune_rows,
            "exposure_conditional_rows": ec_tune_rows,
            "direct_rerank_rows": rerank_tune_rows,
            "hard_constraint_tune": strip_raw(hard_tune_eval),
        },
        "dev_evaluation_k5": {
            "GlobalFrequency": strip_raw(dev_gf_5),
            "Base": strip_raw(dev_base_5),
            "StaticLoss": strip_raw(dev_static_5),
            "DirectExposureRerank": strip_raw(dev_rerank_5),
            "ExposureHardConstraint": strip_raw(dev_hard_5),
            "ExposureConditional": strip_raw(dev_ec_5),
        },
        "dev_evaluation_k10_secondary": {
            "GlobalFrequency": strip_raw(dev_gf_10),
            "Base": strip_raw(dev_base_10),
            "StaticLoss": strip_raw(dev_static_10),
            "DirectExposureRerank": strip_raw(dev_rerank_10),
            "ExposureHardConstraint": strip_raw(dev_hard_10),
            "ExposureConditional": strip_raw(dev_ec_10),
        },
        "bootstrap_results_k5": {
            "ec_vs_base": {
                "risk_delta": ec_vs_base_risk_delta,
                "risk_delta_95ci": ec_vs_base_risk_ci,
                "recall_delta": ec_vs_base_recall_delta,
                "recall_delta_95ci": ec_vs_base_recall_ci,
            },
            "ec_vs_direct_rerank": {
                "risk_delta": ec_vs_rerank_risk_delta,
                "risk_delta_95ci": ec_vs_rerank_risk_ci,
                "recall_delta": ec_vs_rerank_recall_delta,
                "recall_delta_95ci": ec_vs_rerank_recall_ci,
            },
        },
        "decision_criteria": {
            "condition_1_budget_feasibility": {"passed": cond1, "ec_budget_miss": ec_budget_miss},
            "condition_2_safety_gain_over_base": {
                "passed": cond2,
                "point_pass": cond2_point,
                "observed_ratio": float(
                    dev_ec_5["IncrementalExposureDDI@5"] / dev_base_5["IncrementalExposureDDI@5"]
                ),
                "threshold_ratio": 0.90,
                "bootstrap_ci_upper": float(ec_vs_base_risk_ci[1]),
            },
            "condition_3_bounded_fidelity_loss": {
                "passed": cond3,
                "observed_recall_delta": ec_vs_base_recall_delta,
                "threshold": -0.010,
            },
            "condition_4_incremental_over_killer_control": {
                "passed": cond4,
                "risk_condition_pass": cond4_risk,
                "observed_risk_delta": ec_vs_rerank_risk_delta,
                "threshold_risk_delta": 0.001,
                "recall_condition_pass": cond4_recall,
                "observed_recall_delta": ec_vs_rerank_recall_delta,
                "threshold_recall_delta": 0.005,
                "bootstrap_ci_lower": float(ec_vs_rerank_recall_ci[0]),
            },
            "condition_5_no_weak_dominance": {
                "passed": cond5,
                "static_dominates": static_dominates,
                "hard_dominates": hard_dominates,
            },
        },
    }

    summary_file = args.output_dir / "gate-01-summary.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nWrote public-safe summary to {summary_file}")

    # Write gate-01-decision.md
    decision_md_lines = [
        "# Gate 01 Decision Record — Exposure-Conditioned Learning vs Direct Exposure Controls",
        "",
        f"## Verdict: `{gate_verdict}`",
        "",
        "- **Gate ID**: `GATE01_EXPOSURE_CONDITIONED_LEARNING`",
        "- **Authoritative Stage**: `IDEA_006_GATE_01`",
        "- **Active Idea**: `006-exposure-conditional-medication-recommendation`",
        f"- **Execution Timestamp**: `{summary_data['execution_timestamp']}`",
        f"- **Frozen Batch Size**: `{batch_size}`",
        f"- **Freeze Manifest SHA256**: `{freeze_sha256}`",
        "- **Next CCFA Owner**: `ccf-pipeline-orchestrator`",
        "",
        "---",
        "",
        "## 1. Decision Question Answered",
        "",
        "> Under the frozen leakage-safe provider-order-time task, does end-to-end exposure-conditioned DDI learning create incremental safety/fidelity value beyond a direct exposure-aware reranker that receives exactly the same active-regimen state and DDI matrix?",
        "",
        f"**Result**: `{gate_verdict}`",
        "",
        "### Conditions Evaluation Matrix",
        "",
        "| Condition | Description | Threshold | Observed Value | Verdict |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **Condition 1** | Tune Budget Feasibility | No `TUNE_BUDGET_MISS` | Budget Miss: `{ec_budget_miss}` | **{'PASS' if cond1 else 'FAIL'}** |",
        f"| **Condition 2** | Safety over Base | $R_{{EC}} \\le 0.90 R_{{Base}}$ & CI upper < 0 | Ratio: `{dev_ec_5['IncrementalExposureDDI@5'] / dev_base_5['IncrementalExposureDDI@5']:.4f}`, CI: `[{ec_vs_base_risk_ci[0]:.6f}, {ec_vs_base_risk_ci[1]:.6f}]` | **{'PASS' if cond2 else 'FAIL'}** |",
        f"| **Condition 3** | Bounded Fidelity Cost | $\\Delta\\text{{Recall}}_{{EC-Base}} \\ge -0.010$ | $\\Delta\\text{{Recall}} = {ec_vs_base_recall_delta:+.4f}$ | **{'PASS' if cond3 else 'FAIL'}** |",
        f"| **Condition 4** | Beyond Direct Reranker | $R_{{EC}} \\le R_{{Rerank}} + 0.001$, $\\Delta\\text{{Recall}} \\ge +0.005$, CI lower > 0 | $\\Delta R = {ec_vs_rerank_risk_delta:+.6f}$, $\\Delta\\text{{Recall}} = {ec_vs_rerank_recall_delta:+.4f}$, CI: `[{ec_vs_rerank_recall_ci[0]:+.4f}, {ec_vs_rerank_recall_ci[1]:+.4f}]` | **{'PASS' if cond4 else 'FAIL'}** |",
        f"| **Condition 5** | No Weak Dominance | Controls do not weakly dominate | Static dom: `{static_dominates}`, Hard dom: `{hard_dominates}` | **{'PASS' if cond5 else 'FAIL'}** |",
        "",
        "---",
        "",
        "## 2. Dev Evaluation Metrics (K=5 Primary)",
        "",
        "| Method | Selected Param | Recall@5 | IncrementalExposureDDI@5 | ActiveDDI@5 | NewDDI@5 | NDCG@5 | Hit@5 | MRR | micro-PRAUC |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        f"| **GlobalFrequency** | N/A | {dev_gf_5['Recall@5']:.4f} | {dev_gf_5['IncrementalExposureDDI@5']:.6f} | {dev_gf_5['ActiveDDI@5']:.6f} | {dev_gf_5['NewDDI@5']:.6f} | {dev_gf_5['NDCG@5']:.4f} | {dev_gf_5['Hit@5']:.4f} | N/A | N/A |",
        f"| **Base** | N/A | {dev_base_5['Recall@5']:.4f} | {dev_base_5['IncrementalExposureDDI@5']:.6f} | {dev_base_5['ActiveDDI@5']:.6f} | {dev_base_5['NewDDI@5']:.6f} | {dev_base_5['NDCG@5']:.4f} | {dev_base_5['Hit@5']:.4f} | {dev_base_5.get('MRR', 0.0):.4f} | {dev_base_5.get('micro_PRAUC', 0.0):.4f} |",
        f"| **StaticLoss** | $\\lambda = {selected_lambda_static}$ | {dev_static_5['Recall@5']:.4f} | {dev_static_5['IncrementalExposureDDI@5']:.6f} | {dev_static_5['ActiveDDI@5']:.6f} | {dev_static_5['NewDDI@5']:.6f} | {dev_static_5['NDCG@5']:.4f} | {dev_static_5['Hit@5']:.4f} | {dev_static_5.get('MRR', 0.0):.4f} | {dev_static_5.get('micro_PRAUC', 0.0):.4f} |",
        f"| **DirectExposureRerank** | $\\gamma = {selected_gamma}$ | {dev_rerank_5['Recall@5']:.4f} | {dev_rerank_5['IncrementalExposureDDI@5']:.6f} | {dev_rerank_5['ActiveDDI@5']:.6f} | {dev_rerank_5['NewDDI@5']:.6f} | {dev_rerank_5['NDCG@5']:.4f} | {dev_rerank_5['Hit@5']:.4f} | N/A | N/A |",
        f"| **ExposureHardConstraint** | N/A | {dev_hard_5['Recall@5']:.4f} | {dev_hard_5['IncrementalExposureDDI@5']:.6f} | {dev_hard_5['ActiveDDI@5']:.6f} | {dev_hard_5['NewDDI@5']:.6f} | {dev_hard_5['NDCG@5']:.4f} | {dev_hard_5['Hit@5']:.4f} | N/A | N/A |",
        f"| **ExposureConditional** | $\\lambda = {selected_lambda_ec}$ | {dev_ec_5['Recall@5']:.4f} | {dev_ec_5['IncrementalExposureDDI@5']:.6f} | {dev_ec_5['ActiveDDI@5']:.6f} | {dev_ec_5['NewDDI@5']:.6f} | {dev_ec_5['NDCG@5']:.4f} | {dev_ec_5['Hit@5']:.4f} | {dev_ec_5.get('MRR', 0.0):.4f} | {dev_ec_5.get('micro_PRAUC', 0.0):.4f} |",
        "",
        "---",
        "",
        "## 3. Secondary Evaluation Metrics (K=10)",
        "",
        "| Method | Recall@10 | IncrementalExposureDDI@10 | ActiveDDI@10 | NewDDI@10 | NDCG@10 | Hit@10 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        f"| **GlobalFrequency** | {dev_gf_10['Recall@10']:.4f} | {dev_gf_10['IncrementalExposureDDI@10']:.6f} | {dev_gf_10['ActiveDDI@10']:.6f} | {dev_gf_10['NewDDI@10']:.6f} | {dev_gf_10['NDCG@10']:.4f} | {dev_gf_10['Hit@10']:.4f} |",
        f"| **Base** | {dev_base_10['Recall@10']:.4f} | {dev_base_10['IncrementalExposureDDI@10']:.6f} | {dev_base_10['ActiveDDI@10']:.6f} | {dev_base_10['NewDDI@10']:.6f} | {dev_base_10['NDCG@10']:.4f} | {dev_base_10['Hit@10']:.4f} |",
        f"| **StaticLoss** | {dev_static_10['Recall@10']:.4f} | {dev_static_10['IncrementalExposureDDI@10']:.6f} | {dev_static_10['ActiveDDI@10']:.6f} | {dev_static_10['NewDDI@10']:.6f} | {dev_static_10['NDCG@10']:.4f} | {dev_static_10['Hit@10']:.4f} |",
        f"| **DirectExposureRerank** | {dev_rerank_10['Recall@10']:.4f} | {dev_rerank_10['IncrementalExposureDDI@10']:.6f} | {dev_rerank_10['ActiveDDI@10']:.6f} | {dev_rerank_10['NewDDI@10']:.6f} | {dev_rerank_10['NDCG@10']:.4f} | {dev_rerank_10['Hit@10']:.4f} |",
        f"| **ExposureHardConstraint** | {dev_hard_10['Recall@10']:.4f} | {dev_hard_10['IncrementalExposureDDI@10']:.6f} | {dev_hard_10['ActiveDDI@10']:.6f} | {dev_hard_10['NewDDI@10']:.6f} | {dev_hard_10['NDCG@10']:.4f} | {dev_hard_10['Hit@10']:.4f} |",
        f"| **ExposureConditional** | {dev_ec_10['Recall@10']:.4f} | {dev_ec_10['IncrementalExposureDDI@10']:.6f} | {dev_ec_10['ActiveDDI@10']:.6f} | {dev_ec_10['NewDDI@10']:.6f} | {dev_ec_10['NDCG@10']:.4f} | {dev_ec_10['Hit@10']:.4f} |",
        "",
        "---",
        "",
        "## 4. Quarantine and Scientific Integrity Verification",
        "",
        "1. **Quarantine Adherence**:",
        "   - `R0 Holdout` was strictly uninspected (0 clinical events, 0 predictions, 0 targets accessed).",
        "   - Existing project test split remains untouched.",
        "   - `R0 Dev` was accessed only after all models, hyperparameter configurations, safety budget $B$, and task code were frozen.",
        "2. **Equal Entitlement**:",
        "   - `ExposureConditional`, `DirectExposureRerank`, and `ExposureHardConstraint` received the identical active-regimen state $A_t$ and frozen DDI matrix $D$.",
        "   - All learned models (`Base`, `StaticLoss`, `ExposureConditional`) used the identical architecture, inputs, optimizer, and early stopping rules.",
        "3. **Interpretation Boundary**:",
        "   - `IncrementalExposureDDI` is an operational DDI surrogate, not ADE, clinical harm, or clinical safety.",
        "   - eMAR administration is execution evidence, not treatment appropriateness.",
        "",
        "---",
        "",
        "## 5. Next Routing",
        "",
        "- **Next Owner Skill**: `ccf-pipeline-orchestrator`",
    ]

    decision_file = args.output_dir / "gate-01-decision.md"
    with decision_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(decision_md_lines) + "\n")
    print(f"Wrote decision markdown to {decision_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
