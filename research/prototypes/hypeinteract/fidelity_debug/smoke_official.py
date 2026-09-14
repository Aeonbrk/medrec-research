#!/usr/bin/env python3
"""One-batch CUDA forward/backward smoke for the official HypeMed decoder."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from run_official_fidelity import _idx2word, _load, _official_imports, _prepare_batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--compat-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--cuda", type=int, default=0)
    args = parser.parse_args()
    modules = _official_imports(args.official_root.resolve(), args.compat_root.resolve())
    torch = modules["torch"]
    dill = __import__("dill")
    snapshot = args.snapshot_root.resolve()
    data = _load(snapshot / "records_final.pkl", dill)
    vocabulary = _load(snapshot / "voc_final.pkl", dill)
    train_data = data[: int(len(data) * 2 / 3)]
    voc_size = {
        "diag": len(_idx2word(vocabulary["diag_voc"])),
        "proc": len(_idx2word(vocabulary["pro_voc"])),
        "med": len(_idx2word(vocabulary["med_voc"])),
    }
    adjacency = modules["construct_graphs"](train_data, nums_dict=voc_size)
    n_edges = int(adjacency["diag"].shape[1])
    embedding_path = (
        args.official_root.resolve()
        / "pretrain"
        / "embed"
        / "hgt"
        / "hgt_embed_mimic_3_3.pkl"
    )
    embeddings = torch.load(str(embedding_path), map_location="cpu")
    device = torch.device(f"cuda:{args.cuda}" if torch.cuda.is_available() else "cpu")
    model = modules["HGTDecoder"](
        embedding_dim=64,
        n_heads=4,
        dropout=0.3,
        n_ehr_edges=n_edges,
        voc_size_dict=voc_size,
        padding_dict=voc_size,
        device=device,
        X_hat=embeddings["X"],
        E_mem=embeddings["E"],
        ddi_adj=torch.from_numpy(
            np.asarray(_load(snapshot / "ddi_A_final.pkl", dill), dtype=np.float32)
        ),
        top_n=10,
    ).to(device)
    dataset = modules["MIMICDataset"](train_data)
    loader = modules["DataLoader"](
        dataset,
        batch_size=2,
        collate_fn=modules["collate_fn"],
        shuffle=False,
    )
    batch = next(iter(loader))
    records, masks, targets, visit2edge, valid, bsz, max_visit = _prepare_batch(
        batch, modules, device, voc_size
    )
    output, _side = model(records, masks, valid, visit2edge)
    target = targets["loss_bce_target"].reshape(bsz * max_visit, -1)[valid]
    loss = torch.nn.functional.binary_cross_entropy_with_logits(output, target)
    loss.backward()
    if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(output).all()):
        raise RuntimeError("official decoder CUDA smoke produced a non-finite value")
    print(
        f"official CUDA smoke passed: device={device}, visits={int(output.shape[0])}, "
        f"loss={float(loss.detach().cpu()):.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
