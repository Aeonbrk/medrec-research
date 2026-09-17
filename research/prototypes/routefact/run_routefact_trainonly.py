#!/usr/bin/env python3
"""Execute the frozen RouteFact screen with strictly Train-only route supervision.

This wrapper fixes one mechanical contract mismatch in ``run_routefact.py``:
the original runner expected a Dev route-target array even though the frozen
RouteFact design intentionally derives route vocabulary, support, and route
supervision from Train prescription rows only.  The training/evaluation loop is
otherwise unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

import run_routefact as base


def _validate_train_only_route_assets(
    route_root: Path, source_revision: str
) -> Tuple[np.ndarray, None, np.ndarray, Tuple[str, ...], Dict[str, Any]]:
    metadata_path = route_root / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "complete" or metadata.get("profile_id") != base.PROFILE_ID:
        raise RuntimeError("route target metadata does not match RouteFact profile")
    if metadata.get("source_revision") != source_revision:
        raise RuntimeError("route targets were not built from the run source revision")
    if metadata.get("route_vocabulary_source") != "Train only":
        raise RuntimeError("route vocabulary is not Train-only frozen")
    if metadata.get("medication_route_support_mask_source") != "Train only":
        raise RuntimeError("medication-route support mask is not Train-only frozen")
    if metadata.get("raw_route_scope") != "Train admissions only; Dev raw route labels not read":
        raise RuntimeError("route target metadata does not prove strict Train-only raw-route scope")

    assets = metadata.get("assets", {})
    expected_assets = {
        "train_route_targets.npy",
        "allowed_route_mask.npy",
        "route_vocabulary.json",
    }
    if set(assets) != expected_assets:
        raise RuntimeError("route target asset set differs from the frozen Train-only contract")
    if (route_root / "dev_route_targets.npy").exists():
        raise RuntimeError("Dev route targets must not exist for the frozen RouteFact screen")

    for name, expected in assets.items():
        path = route_root / name
        if (
            not path.is_file()
            or path.stat().st_size != expected.get("bytes")
            or base._sha256(path) != expected.get("sha256")
        ):
            raise RuntimeError("route asset integrity failed: " + name)

    train_route = np.load(route_root / "train_route_targets.npy", mmap_mode="r")
    allowed = np.asarray(
        np.load(route_root / "allowed_route_mask.npy", mmap_mode="r"), dtype=np.uint8
    )
    route_payload = json.loads(
        (route_root / "route_vocabulary.json").read_text(encoding="utf-8")
    )
    routes = tuple(str(value) for value in route_payload["routes"])
    if train_route.shape != (10489, base.MEDICATIONS, len(routes)):
        raise RuntimeError("Train route target shape mismatch")
    if allowed.shape != (base.MEDICATIONS, len(routes)):
        raise RuntimeError("allowed route mask shape mismatch")
    if np.any(allowed.sum(axis=1) < 1):
        raise RuntimeError("each medication must retain at least one Train-supported route coordinate")
    if not np.isin(allowed, (0, 1)).all():
        raise RuntimeError("allowed route mask is not binary")

    return train_route, None, allowed, routes, metadata


def main() -> None:
    base._validate_route_assets = _validate_train_only_route_assets
    base.main()


if __name__ == "__main__":
    main()
