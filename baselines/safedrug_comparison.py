#!/usr/bin/env python3
"""Target-free Comparison adapter for the pinned SafeDrug archived lineage."""

from __future__ import annotations

import argparse
import contextlib
import json
import pickle
import sys
from pathlib import Path

PROFILES = ("gamenet", "leap-safedrug", "retain", "safedrug")
THRESHOLDS = {"gamenet": 0.5, "retain": 0.4, "safedrug": 0.5}


def _wire_scores(vocabulary: tuple[str, ...], scores: object) -> list[dict[str, object]]:
    return [
        {"medication_code": code, "score": float(scores[index])}
        for index, code in enumerate(vocabulary)
    ]


def _threshold_indices(scores: object, threshold: float) -> list[int]:
    return [index for index, score in enumerate(scores) if float(score) >= threshold]


def _load_model(
    profile: str,
    upstream_root: Path,
    dataset_root: Path,
    features: Path,
    checkpoint: Path,
):
    import dill
    import torch

    upstream_src = str(upstream_root / "src")
    if upstream_src not in sys.path:
        sys.path.insert(0, upstream_src)
    from models import GAMENet, Leap, Retain, SafeDrugModel
    from util import buildMPNN, sequence_output_process

    bundle = pickle.load(features.open("rb"))
    voc_size = tuple(bundle["voc_size"])
    device = torch.device("cuda")
    if profile == "retain":
        model = Retain(voc_size, device=device)
    elif profile == "leap-safedrug":
        model = Leap(voc_size, device=device)
    elif profile == "gamenet":
        ehr_adj = dill.load((dataset_root / "ehr_adj_final.pkl").open("rb"))
        ddi_adj = dill.load((dataset_root / "ddi_A_final.pkl").open("rb"))
        model = GAMENet(voc_size, ehr_adj, ddi_adj, emb_dim=64, device=device, ddi_in_memory=True)
    else:
        ddi_adj = dill.load((dataset_root / "ddi_A_final.pkl").open("rb"))
        ddi_mask = dill.load((dataset_root / "ddi_mask_H.pkl").open("rb"))
        molecule = dill.load((dataset_root / "idx2drug.pkl").open("rb"))
        voc = dill.load((dataset_root / "voc_final.pkl").open("rb"))
        mpnn_set, fingerprints, projection = buildMPNN(molecule, voc["med_voc"].idx2word, 2, device)
        model = SafeDrugModel(
            voc_size,
            ddi_adj,
            ddi_mask,
            mpnn_set,
            fingerprints,
            projection,
            emb_dim=64,
            device=device,
        )
    with checkpoint.open("rb") as stream:
        model.load_state_dict(torch.load(stream, map_location=device))
    return model.to(device).eval(), bundle, sequence_output_process


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    import numpy as np
    import torch

    torch.manual_seed(1203)
    np.random.seed(2048)
    request = json.load(sys.stdin)
    if request != {
        "request": {"dataset_id": "molerec-table1-comparison-v1-1"},
        "schema_version": 2,
    }:
        raise ValueError("unexpected target-free adapter request")
    dataset_root = args.dataset_root.resolve()
    with contextlib.redirect_stdout(sys.stderr):
        model, bundle, sequence_output_process = _load_model(
            args.profile,
            args.upstream_root.resolve(),
            dataset_root,
            args.features.resolve(),
            args.checkpoint.resolve(),
        )
    vocabulary = tuple(bundle["medication_vocabulary"])
    medication_count = len(vocabulary)
    predictions = []
    with torch.no_grad():
        contexts = bundle["contexts"][:1] if args.smoke else bundle["contexts"]
        for context in contexts:
            history = [
                [list(admission[0]), list(admission[1]), list(admission[2])]
                for admission in context["history"]
            ]
            current = [
                list(context["current_diagnoses"]),
                list(context["current_procedures"]),
                [],
            ]
            if args.profile == "retain":
                output = model(history)
                probabilities = torch.sigmoid(output)[0].detach().cpu().numpy()
                indices = _threshold_indices(probabilities, THRESHOLDS[args.profile])
            elif args.profile == "leap-safedrug":
                output = model(current).detach().cpu().numpy()
                _, decoded = sequence_output_process(
                    output, [medication_count, medication_count + 1]
                )
                indices = list(decoded)
                probabilities = np.mean(output[:, :-2], axis=0)
            else:
                output = model([*history, current])
                logits = output[0] if isinstance(output, tuple) else output
                probabilities = torch.sigmoid(logits)[0].detach().cpu().numpy()
                indices = _threshold_indices(probabilities, THRESHOLDS[args.profile])
            predictions.append(
                {
                    "patient_id": context["patient_id"],
                    "predicted_medications": [vocabulary[index] for index in indices],
                    "visit_id": context["visit_id"],
                    "vocabulary_scores": _wire_scores(vocabulary, probabilities),
                }
            )
    json.dump(
        {"method_id": args.profile, "predictions": predictions, "schema_version": 2},
        sys.stdout,
        separators=(",", ":"),
        sort_keys=True,
    )


if __name__ == "__main__":
    main()
