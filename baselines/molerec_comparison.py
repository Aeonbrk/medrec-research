#!/usr/bin/env python3
"""Target-free Comparison adapter for the pinned MoleRec embedding profile."""

from __future__ import annotations

import argparse
import contextlib
import json
import pickle
import sys
from pathlib import Path


def _threshold_indices(scores: object) -> list[int]:
    return [index for index, score in enumerate(scores) if float(score) >= 0.5]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    import dill
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
    upstream_src = str(args.upstream_root.resolve() / "src")
    if upstream_src not in sys.path:
        sys.path.insert(0, upstream_src)
    from modules import MoleRecModel
    from modules.gnn import graph_batch_from_smile
    from util import buildPrjSmiles

    bundle = pickle.load(args.features.resolve().open("rb"))
    vocabulary = tuple(bundle["medication_vocabulary"])
    voc_size = tuple(bundle["voc_size"])
    dataset_root = args.dataset_root.resolve()
    device = torch.device("cuda")
    ddi_adj = torch.from_numpy(dill.load((dataset_root / "ddi_A_final.pkl").open("rb"))).to(device)
    ddi_mask = torch.from_numpy(dill.load((dataset_root / "ddi_mask_H.pkl").open("rb"))).to(device)
    molecule = dill.load((dataset_root / "idx2SMILES.pkl").open("rb"))
    voc = dill.load((dataset_root / "voc_final.pkl").open("rb"))
    with contextlib.redirect_stdout(sys.stderr):
        projection, smiles = buildPrjSmiles(molecule, voc["med_voc"].idx2word)
        molecule_forward = {"batched_data": graph_batch_from_smile(smiles).to(device)}
    molecule_parameters = {
        "drop_ratio": 0.7,
        "emb_dim": 64,
        "gnn_type": "gin",
        "graph_pooling": "mean",
        "num_layer": 4,
        "virtual_node": False,
    }
    model = MoleRecModel(
        global_para=molecule_parameters,
        substruct_para=None,
        emb_dim=64,
        global_dim=64,
        substruct_dim=64,
        substruct_num=ddi_mask.shape[1],
        voc_size=voc_size,
        use_embedding=True,
        device=device,
        dropout=0.7,
    ).to(device)
    with args.checkpoint.resolve().open("rb") as stream:
        model.load_state_dict(torch.load(stream, map_location=device))
    model.eval()
    drug_data = {
        "average_projection": projection.to(device),
        "ddi_mask_H": ddi_mask,
        "mol_data": molecule_forward,
        "substruct_data": None,
        "tensor_ddi_adj": ddi_adj,
    }
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
            logits, _ = model(patient_data=[*history, current], **drug_data)
            probabilities = torch.sigmoid(logits)[0].detach().cpu().numpy()
            indices = _threshold_indices(probabilities)
            predictions.append(
                {
                    "patient_id": context["patient_id"],
                    "predicted_medications": [vocabulary[index] for index in indices],
                    "visit_id": context["visit_id"],
                    "vocabulary_scores": [
                        {"medication_code": code, "score": float(score)}
                        for code, score in zip(vocabulary, probabilities, strict=True)
                    ],
                }
            )
    json.dump(
        {"method_id": "molerec", "predictions": predictions, "schema_version": 2},
        sys.stdout,
        separators=(",", ":"),
        sort_keys=True,
    )


if __name__ == "__main__":
    main()
