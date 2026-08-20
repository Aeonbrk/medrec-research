from __future__ import annotations

import pytest

from medrec_research import MoleRecArtifactBundle, ProtocolValidationError


def _bundle() -> MoleRecArtifactBundle:
    return MoleRecArtifactBundle.create(
        variant="molerec-default",
        checkpoint_sha256="a" * 64,
        vocabulary_sha256="b" * 64,
        preprocessing_sha256="c" * 64,
        ddi_sha256="d" * 64,
        brics_sha256="e" * 64,
    )


def test_molerec_bundle_round_trip_and_exact_digest() -> None:
    bundle = _bundle()
    assert MoleRecArtifactBundle.from_json(bundle.to_json()) == bundle
    assert bundle.is_current()
    assert bundle.vocabulary_sha256 == "b" * 64
    assert bundle.preprocessing_sha256 == "c" * 64

    with pytest.raises(ProtocolValidationError, match="artifact identity"):
        MoleRecArtifactBundle(
            variant=bundle.variant,
            checkpoint_sha256="f" * 64,
            vocabulary_order_sha256=bundle.vocabulary_order_sha256,
            preprocessing_artifact_sha256=bundle.preprocessing_artifact_sha256,
            ddi_artifact_sha256=bundle.ddi_artifact_sha256,
            brics_artifact_sha256=bundle.brics_artifact_sha256,
            bundle_sha256=bundle.bundle_sha256,
        )
