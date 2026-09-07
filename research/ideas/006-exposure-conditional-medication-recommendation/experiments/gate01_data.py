"""Idea 006 Gate 01: Data processing, causal active regimen, and task construction.

SSOT: research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc_comp
import pyarrow.csv as pc
import torch
from torch.utils.data import Dataset

SPLIT_SALT_OUTER = "exposure-reset-20260905"
SPLIT_SALT_INNER = "idea006-gate01-inner-20260907"
FROZEN_DDI_ASSET_SHA256 = "dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7"

ADMINISTRATION_EVENT_TYPES = frozenset(
    [
        "Administered",
        "Applied",
        "Inhaled",
        "Started",
        "Restarted",
        "Infused",
        "Given",
        "Delayed Administered",
        "Administered Bolus from IV Drip",
        "Administered in Other Location",
        "Started in Other Location",
        "Delayed Started",
        "Partial Administered",
        "Applied in Other Location",
        "Delayed Applied",
        "Delayed Restarted",
        "Restarted in Other Location",
        "Removed Existing / Applied New",
    ]
)


def classify_subject_outer(subject_id: str | int) -> str:
    """Classify patient into Discovery, Dev, or Holdout using frozen R0 salt."""
    token = f"{subject_id}|{SPLIT_SALT_OUTER}".encode()
    digest = hashlib.sha256(token).hexdigest()[:8]
    u = int(digest, 16) / 0xFFFFFFFF
    if u < 0.70:
        return "discovery"
    if u < 0.85:
        return "dev"
    return "holdout"


def classify_subject_inner(subject_id: str | int) -> str:
    """Classify Discovery patient into InnerTrain or InnerTune."""
    token = f"{subject_id}|{SPLIT_SALT_INNER}".encode()
    digest = hashlib.sha256(token).hexdigest()[:8]
    u = int(digest, 16) / 0xFFFFFFFF
    if u < 0.85:
        return "InnerTrain"
    return "InnerTune"


def classify_subject_gate01(subject_id: str | int) -> str:
    """Full Gate 01 partition classification.

    Returns:
        'InnerTrain', 'InnerTune', 'Dev', or 'Holdout'
    """
    outer = classify_subject_outer(subject_id)
    if outer == "discovery":
        return classify_subject_inner(subject_id)
    if outer == "dev":
        return "Dev"
    return "Holdout"


def load_frozen_ddi_asset(
    snapshot_dir: Path,
) -> tuple[dict[int, str], dict[str, int], np.ndarray, set[str], str]:
    """Load frozen DDI knowledge asset and verify SHA256 digest."""
    import dill

    voc_path = snapshot_dir / "voc_final.pkl"
    ddi_path = snapshot_dir / "ddi_A_final.pkl"

    with voc_path.open("rb") as f:
        voc = dill.load(f)
    with ddi_path.open("rb") as f:
        ddi_matrix = dill.load(f)

    med_voc: dict[int, str] = voc["med_voc"].idx2word
    n_concepts = len(med_voc)
    assert n_concepts == 131, f"Expected 131 concepts, got {n_concepts}"

    concept_to_idx = {c: i for i, c in med_voc.items()}

    raw_ddi_pairs = []
    canonical_ddi_pairs = set()
    ddi_concepts = set()

    for left in range(n_concepts):
        for right in range(left + 1, n_concepts):
            if ddi_matrix[left][right] == 1:
                c1, c2 = med_voc[left], med_voc[right]
                raw_ddi_pairs.append((c1, c2))
                canonical_ddi_pairs.add(tuple(sorted((c1, c2))))
                ddi_concepts.add(c1)
                ddi_concepts.add(c2)

    serialized = json.dumps(
        raw_ddi_pairs,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    asset_sha256 = hashlib.sha256(serialized.encode("ascii")).hexdigest()

    ddi_np = np.array(ddi_matrix, dtype=np.float32)

    return med_voc, concept_to_idx, ddi_np, ddi_concepts, asset_sha256


def build_ndc_mapping(
    ndc2atc_path: Path,
    kgd_mapping_path: Path,
) -> dict[str, str]:
    """Build combined NDC to ATC Level 4 map."""
    map_combined: dict[str, str] = {}

    df_safedrug = pd.read_csv(ndc2atc_path)
    for _, row in df_safedrug.iterrows():
        raw_ndc = str(row["NDC"]).strip()
        atc4 = str(row["ATC4"]).strip()[:4]
        clean = re.sub(r"[^0-9]", "", raw_ndc)
        if clean and len(atc4) == 4:
            map_combined[clean] = atc4
            map_combined[clean.zfill(11)] = atc4

    df_kgd = pd.read_csv(kgd_mapping_path)
    for _, row in df_kgd.iterrows():
        ndc_str = str(row["ndc"]).strip()
        atc4 = str(row["atc4"]).strip()[:4]
        if ndc_str and len(atc4) == 4 and atc4 != "nan":
            map_combined[ndc_str] = atc4
            map_combined[ndc_str.zfill(11)] = atc4

    return map_combined


def build_prescriptions_linkage(
    prescriptions_file: Path,
    map_combined: dict[str, str],
    vocab_131: set[str],
    disc_subjects_arr: pa.Array,
    allowed_subjects_arr: pa.Array,
) -> tuple[dict[Any, set[str]], dict[Any, str], dict[Any, set[int]]]:
    """Extract poe_id to ATC mapping, pharmacy_id to ATC mapping, and poe_id to pharmacy_id mapping."""
    rx_cols = ["subject_id", "poe_id", "pharmacy_id", "ndc", "formulary_drug_cd"]
    rx_tab = pc.read_csv(
        prescriptions_file, convert_options=pc.ConvertOptions(include_columns=rx_cols)
    )

    # 1. Filter to Discovery to build consensus formulary map
    disc_mask = pc_comp.is_in(rx_tab["subject_id"], value_set=disc_subjects_arr)
    disc_rx = rx_tab.filter(disc_mask)

    disc_ndcs = disc_rx["ndc"].to_pylist()
    disc_fcds = disc_rx["formulary_drug_cd"].to_pylist()

    form_to_atc: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for n, fcd in zip(disc_ndcs, disc_fcds, strict=False):
        s = str(n) if n is not None and n != 0 else ""
        atc = map_combined.get(s) or map_combined.get(s.zfill(11))
        if atc and atc in vocab_131 and fcd:
            form_to_atc[fcd][atc] += 1

    consensus_form_map: dict[str, str] = {}
    for fcd, cnts in form_to_atc.items():
        top_atc, top_cnt = cnts.most_common(1)[0]
        if top_cnt / sum(cnts.values()) >= 0.85:
            consensus_form_map[fcd] = top_atc

    # 2. Filter rx_tab to all allowed subjects (InnerTrain, InnerTune, Dev)
    allowed_mask = pc_comp.is_in(rx_tab["subject_id"], value_set=allowed_subjects_arr)
    allowed_rx = rx_tab.filter(allowed_mask)

    ndcs = allowed_rx["ndc"].to_pylist()
    fcds = allowed_rx["formulary_drug_cd"].to_pylist()
    poes = allowed_rx["poe_id"].to_pylist()
    pharms = allowed_rx["pharmacy_id"].to_pylist()

    poe_to_atcs: dict[Any, set[str]] = collections.defaultdict(set)
    pharm_to_atc: dict[Any, str] = {}
    poe_to_pharms: dict[Any, set[int]] = collections.defaultdict(set)

    for n, fcd, p, ph in zip(ndcs, fcds, poes, pharms, strict=False):
        s = str(n) if n is not None and n != 0 else ""
        atc = map_combined.get(s) or map_combined.get(s.zfill(11))
        if (not atc or atc not in vocab_131) and fcd in consensus_form_map:
            atc = consensus_form_map[fcd]

        if atc and atc in vocab_131:
            if p is not None and str(p).strip() != "":
                poe_to_atcs[p].add(atc)
                if ph is not None and ph != 0:
                    poe_to_pharms[p].add(ph)
            if ph is not None and ph != 0:
                pharm_to_atc[ph] = atc

    return poe_to_atcs, pharm_to_atc, poe_to_pharms


class BurstDataset(Dataset):
    """PyTorch Dataset for order-time medication bursts."""

    def __init__(self, bursts: list[dict[str, Any]]) -> None:
        self.bursts = bursts

    def __len__(self) -> int:
        return len(self.bursts)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        b = self.bursts[idx]
        return {
            "hist_meds": torch.tensor(b["hist_meds"], dtype=torch.long),
            "hist_types": torch.tensor(b["hist_types"], dtype=torch.long),
            "hist_elapsed": torch.tensor(b["hist_elapsed"], dtype=torch.float32),
            "active_regimen": torch.tensor(b["active_regimen"], dtype=torch.float32),
            "log_hours_since_admit": torch.tensor(
                [b["log_hours_since_admit"]], dtype=torch.float32
            ),
            "target_vec": torch.tensor(b["target_vec"], dtype=torch.float32),
            "in_q": b["in_q"],
            "patient_id": b["patient_id"],
            "target_indices": b["target_indices"],
            "active_indices": b["active_indices"],
            "burst_idx": idx,
        }


def collate_burst_batch(batch: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch collator for BurstDataset."""
    hist_meds = torch.stack([item["hist_meds"] for item in batch], dim=0)
    hist_types = torch.stack([item["hist_types"] for item in batch], dim=0)
    hist_elapsed = torch.stack([item["hist_elapsed"] for item in batch], dim=0)
    active_regimen = torch.stack([item["active_regimen"] for item in batch], dim=0)
    log_hours = torch.stack([item["log_hours_since_admit"] for item in batch], dim=0)
    target_vec = torch.stack([item["target_vec"] for item in batch], dim=0)
    in_q = torch.tensor([item["in_q"] for item in batch], dtype=torch.bool)
    patient_ids = [item["patient_id"] for item in batch]
    target_indices = [item["target_indices"] for item in batch]
    active_indices = [item["active_indices"] for item in batch]

    return {
        "hist_meds": hist_meds,
        "hist_types": hist_types,
        "hist_elapsed": hist_elapsed,
        "active_regimen": active_regimen,
        "log_hours_since_admit": log_hours,
        "target_vec": target_vec,
        "in_q": in_q,
        "patient_ids": patient_ids,
        "target_indices": target_indices,
        "active_indices": active_indices,
    }


def build_burst_datasets(
    mimic_dir: Path,
    ddi_snapshot_dir: Path,
    mapping_dir: Path,
    cache_dir: Path | None = None,
    max_subjects: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Extract and construct 10-minute bursts across InnerTrain, InnerTune, and Dev."""
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Check if pre-cached bursts exist
        all_cached = True
        cached_data = {}
        for part in ["InnerTrain", "InnerTune", "Dev"]:
            cache_file = cache_dir / f"bursts_{part}.pt"
            if cache_file.exists():
                cached_data[part] = torch.load(cache_file)
            else:
                all_cached = False
                break
        if all_cached:
            print("Loaded all partitions from cache:", {k: len(v) for k, v in cached_data.items()})
            return cached_data

    t0 = time.time()
    # 1. Read patients and classify first
    patients_file = (
        mimic_dir / "patients.csv.gz"
        if (mimic_dir / "patients.csv.gz").exists()
        else mimic_dir / "patients.csv"
    )
    pat_tab = pc.read_csv(
        patients_file, convert_options=pc.ConvertOptions(include_columns=["subject_id"])
    )
    all_sids = pat_tab["subject_id"].to_pylist()

    subject_to_part: dict[int, str] = {}
    allowed_subjects: set[int] = set()
    disc_subjects: set[int] = set()

    for sid in all_sids:
        part = classify_subject_gate01(sid)
        if part != "Holdout":
            subject_to_part[sid] = part
            allowed_subjects.add(sid)
            if classify_subject_outer(sid) == "discovery":
                disc_subjects.add(sid)
            if max_subjects is not None and len(allowed_subjects) >= max_subjects:
                break

    allowed_subjects_arr = pa.array(list(allowed_subjects))
    disc_subjects_arr = pa.array(list(disc_subjects))
    print(f"Allowed subjects for Gate 01: {len(allowed_subjects)} (Holdout strictly quarantined)")

    # 2. Load DDI asset and vocabulary
    med_voc, concept_to_idx, ddi_np, _ddi_concepts, _asset_sha256 = load_frozen_ddi_asset(
        ddi_snapshot_dir
    )
    vocab_131 = set(med_voc.values())
    has_ddi_relation = ddi_np.sum(axis=1) > 0  # (131,) bool

    # 3. Load mappings and prescriptions linkage
    ndc2atc_p = mapping_dir / "ndc2atc_level4.csv"
    kgd_p = mapping_dir / "drug_codes_mapping.csv"
    map_combined = build_ndc_mapping(ndc2atc_p, kgd_p)

    rx_file = (
        mimic_dir / "prescriptions.csv.gz"
        if (mimic_dir / "prescriptions.csv.gz").exists()
        else mimic_dir / "prescriptions.csv"
    )
    poe_to_atcs, _pharm_to_atc, poe_to_pharms = build_prescriptions_linkage(
        rx_file, map_combined, vocab_131, disc_subjects_arr, allowed_subjects_arr
    )
    print(
        f"Built prescription linkages in {time.time() - t0:.2f}s: mapped poe_ids={len(poe_to_atcs)}"
    )

    # 4. Read admissions (filtered to allowed subjects)
    adm_file = (
        mimic_dir / "admissions.csv.gz"
        if (mimic_dir / "admissions.csv.gz").exists()
        else mimic_dir / "admissions.csv"
    )
    adm_tab = pc.read_csv(
        adm_file,
        convert_options=pc.ConvertOptions(include_columns=["subject_id", "hadm_id", "admittime"]),
    )
    adm_filtered = adm_tab.filter(
        pc_comp.is_in(adm_tab["subject_id"], value_set=allowed_subjects_arr)
    )

    adm_sids = adm_filtered["subject_id"].to_pylist()
    adm_hids = adm_filtered["hadm_id"].to_pylist()
    adm_times = adm_filtered["admittime"].cast(pa.int64()).to_pylist()

    hadm_to_admit: dict[int, tuple[int, int]] = {}
    for sid, hid, at in zip(adm_sids, adm_hids, adm_times, strict=False):
        if hid is not None:
            hadm_to_admit[hid] = (sid, at)

    # 5. Read POE medication orders (filtered to allowed subjects and valid transaction types)
    poe_file = (
        mimic_dir / "poe.csv.gz" if (mimic_dir / "poe.csv.gz").exists() else mimic_dir / "poe.csv"
    )
    poe_cols = [
        "poe_id",
        "subject_id",
        "hadm_id",
        "ordertime",
        "order_type",
        "transaction_type",
        "discontinue_of_poe_id",
    ]
    poe_tab = pc.read_csv(poe_file, convert_options=pc.ConvertOptions(include_columns=poe_cols))

    med_mask = pc_comp.equal(poe_tab["order_type"], "Medications")
    type_mask = pc_comp.is_in(
        poe_tab["transaction_type"], value_set=pa.array(["New", "Change", "D/C"])
    )
    sid_mask = pc_comp.is_in(poe_tab["subject_id"], value_set=allowed_subjects_arr)
    poe_filtered = poe_tab.filter(pc_comp.and_(pc_comp.and_(med_mask, type_mask), sid_mask))

    poe_hids = poe_filtered["hadm_id"].to_pylist()
    poe_ids = poe_filtered["poe_id"].to_pylist()
    poe_times = poe_filtered["ordertime"].cast(pa.int64()).to_pylist()
    poe_types = poe_filtered["transaction_type"].to_pylist()
    poe_disc_ids = poe_filtered["discontinue_of_poe_id"].to_pylist()

    hadm_to_poe_events: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for hid, pid, ot, tt, dt in zip(
        poe_hids, poe_ids, poe_times, poe_types, poe_disc_ids, strict=False
    ):
        if hid is None:
            continue
        hadm_to_poe_events[hid].append(
            {
                "poe_id": pid,
                "ordertime": ot,
                "transaction_type": tt,
                "discontinue_of_poe_id": dt,
            }
        )

    print(
        f"Collected POE events for {len(hadm_to_poe_events)} hospitalizations in {time.time() - t0:.2f}s"
    )

    # 6. Read eMAR administrations (filtered to allowed subjects and admin types)
    emar_file = (
        mimic_dir / "emar.csv.gz"
        if (mimic_dir / "emar.csv.gz").exists()
        else mimic_dir / "emar.csv"
    )
    emar_cols = [
        "subject_id",
        "hadm_id",
        "poe_id",
        "pharmacy_id",
        "charttime",
        "event_txt",
    ]
    emar_tab = pc.read_csv(emar_file, convert_options=pc.ConvertOptions(include_columns=emar_cols))

    admin_mask = pc_comp.is_in(
        emar_tab["event_txt"], value_set=pa.array(list(ADMINISTRATION_EVENT_TYPES))
    )
    emar_sid_mask = pc_comp.is_in(emar_tab["subject_id"], value_set=allowed_subjects_arr)
    emar_filtered = emar_tab.filter(pc_comp.and_(admin_mask, emar_sid_mask))

    emar_hids = emar_filtered["hadm_id"].to_pylist()
    emar_poes = emar_filtered["poe_id"].to_pylist()
    emar_pharms = emar_filtered["pharmacy_id"].to_pylist()
    emar_times = emar_filtered["charttime"].cast(pa.int64()).to_pylist()

    hadm_to_admins: dict[int, list[tuple[int, Any, Any]]] = collections.defaultdict(list)
    for hid, pid, ph, ct in zip(emar_hids, emar_poes, emar_pharms, emar_times, strict=False):
        if hid is not None:
            hadm_to_admins[hid].append((ct, pid, ph))

    print(
        f"Collected eMAR admin events for {len(hadm_to_admins)} hospitalizations in {time.time() - t0:.2f}s"
    )

    # 7. Construct 10-minute bursts and causal active regimen
    bursts_by_part: dict[str, list[dict[str, Any]]] = {
        "InnerTrain": [],
        "InnerTune": [],
        "Dev": [],
    }

    n_total_bursts = 0
    n_q_bursts = 0

    for hid, poe_events in hadm_to_poe_events.items():
        if hid not in hadm_to_admit:
            continue
        sid, admittime = hadm_to_admit[hid]
        partition = subject_to_part[sid]

        # Sort all POE events by ordertime, then poe_id
        poe_events.sort(key=lambda x: (x["ordertime"], str(x["poe_id"])))

        # Administrations for this hadm
        admins = hadm_to_admins.get(hid, [])
        # Index administrations by poe_id and pharmacy_id with timestamps
        admin_poe_times = collections.defaultdict(list)
        admin_pharm_times = collections.defaultdict(list)
        for ct, pid, ph in admins:
            if pid is not None:
                admin_poe_times[pid].append(ct)
            if ph is not None:
                admin_pharm_times[ph].append(ct)

        # Filter positive target orders
        positive_orders = [
            ev
            for ev in poe_events
            if ev["transaction_type"] in ("New", "Change") and ev["poe_id"] in poe_to_atcs
        ]

        if not positive_orders:
            continue

        assigned_indices: set[int] = set()

        for idx, base_order in enumerate(positive_orders):
            if idx in assigned_indices:
                continue

            decision_t = base_order["ordertime"]
            burst_end = decision_t + 600  # 10 minutes = 600 seconds

            # Collect positive orders in [decision_t, burst_end)
            burst_positive_orders = []
            target_concepts: set[str] = set()

            for j in range(idx, len(positive_orders)):
                cand_order = positive_orders[j]
                cand_t = cand_order["ordertime"]
                if cand_t >= burst_end:
                    break
                burst_positive_orders.append(cand_order)
                assigned_indices.add(j)
                for c in poe_to_atcs[cand_order["poe_id"]]:
                    target_concepts.add(c)

            if not target_concepts:
                continue

            target_indices = [concept_to_idx[c] for c in target_concepts]
            target_vec = np.zeros(131, dtype=np.float32)
            target_vec[target_indices] = 1.0

            # Causal Historical sequence strictly < decision_t
            hist_events = [ev for ev in poe_events if ev["ordertime"] < decision_t]
            # Take last 64 transactions
            hist_events_64 = hist_events[-64:]

            hist_meds = np.zeros(64, dtype=np.int64)
            hist_types = np.zeros(64, dtype=np.int64)
            hist_elapsed = np.zeros(64, dtype=np.float32)

            prev_time = None
            for step, ev in enumerate(hist_events_64):
                tt = ev["transaction_type"]
                tt_code = 1 if tt == "New" else (2 if tt == "Change" else 3)
                ev_t = ev["ordertime"]

                if tt in ("New", "Change"):
                    concepts = poe_to_atcs.get(ev["poe_id"], set())
                    c_idx = (concept_to_idx[sorted(concepts)[0]] + 1) if concepts else 0
                else:  # D/C
                    disc_poe = ev["discontinue_of_poe_id"]
                    concepts = poe_to_atcs.get(disc_poe, set())
                    c_idx = (concept_to_idx[sorted(concepts)[0]] + 1) if concepts else 0

                elapsed_hours = (ev_t - prev_time) / 3600.0 if prev_time is not None else 0.0
                elapsed_feat = math.log1p(max(0.0, elapsed_hours))

                hist_meds[step] = c_idx
                hist_types[step] = tt_code
                hist_elapsed[step] = elapsed_feat
                prev_time = ev_t

            # Causal active regimen A_t
            # An order o is active at decision_t iff:
            # 1. ordertime < decision_t
            # 2. at least one administration before decision_t
            # 3. not discontinued before decision_t
            dc_discontinued_poes = {
                ev["discontinue_of_poe_id"]
                for ev in hist_events
                if ev["transaction_type"] == "D/C" and ev["discontinue_of_poe_id"] is not None
            }

            active_concepts: set[str] = set()
            for ev in hist_events:
                if ev["transaction_type"] not in ("New", "Change"):
                    continue
                o_pid = ev["poe_id"]
                if o_pid not in poe_to_atcs:
                    continue
                if o_pid in dc_discontinued_poes:
                    continue

                # Check administration evidence before decision_t
                has_admin = False
                for ct in admin_poe_times.get(o_pid, []):
                    if ct < decision_t:
                        has_admin = True
                        break
                if not has_admin:
                    # Check linked pharmacy_ids
                    for ph in poe_to_pharms.get(o_pid, []):
                        for ct in admin_pharm_times.get(ph, []):
                            if ct < decision_t:
                                has_admin = True
                                break
                        if has_admin:
                            break

                if has_admin:
                    for c in poe_to_atcs[o_pid]:
                        active_concepts.add(c)

            active_indices = [concept_to_idx[c] for c in active_concepts]
            active_vec = np.zeros(131, dtype=np.float32)
            active_vec[active_indices] = 1.0

            # log hours since admission
            hours_since_admit = max(0.0, (decision_t - admittime) / 3600.0)
            log_hours = math.log1p(hours_since_admit)

            # Primary universe Q: |A_t| > 0 and exists a in A_t, m in V: D_ma = 1
            has_active_ddi = any(has_ddi_relation[idx] for idx in active_indices)
            in_q = bool(len(active_indices) > 0 and has_active_ddi)

            burst_dict = {
                "hadm_id": hid,
                "patient_id": sid,
                "decision_t": decision_t,
                "hist_meds": hist_meds.tolist(),
                "hist_types": hist_types.tolist(),
                "hist_elapsed": hist_elapsed.tolist(),
                "active_regimen": active_vec.tolist(),
                "active_indices": active_indices,
                "log_hours_since_admit": float(log_hours),
                "target_vec": target_vec.tolist(),
                "target_indices": target_indices,
                "in_q": in_q,
            }

            bursts_by_part[partition].append(burst_dict)
            n_total_bursts += 1
            if in_q:
                n_q_bursts += 1

    print(
        f"Constructed {n_total_bursts} bursts ({n_q_bursts} in Q) in {time.time() - t0:.2f}s: "
        f"InnerTrain={len(bursts_by_part['InnerTrain'])}, "
        f"InnerTune={len(bursts_by_part['InnerTune'])}, "
        f"Dev={len(bursts_by_part['Dev'])}"
    )

    if cache_dir is not None:
        for part, b_list in bursts_by_part.items():
            cache_file = cache_dir / f"bursts_{part}.pt"
            torch.save(b_list, cache_file)
            print(f"Saved {len(b_list)} bursts to {cache_file}")

    return bursts_by_part
