"""Additive MICA-Core intrinsic controls for Stage -1C.

The controls deliberately reuse the historical ``MICA`` implementation.  They
change only the named internal capacity/readout seam; no input, medication
identity, loss, decoder, or information source is added.
"""

from __future__ import annotations

import torch
from torch import nn

try:
    from mica import DIM, MICA
except ModuleNotFoundError:  # pragma: no cover - useful when run from checkout root
    from research.prototypes.mica.mica import DIM, MICA


class ConsolidationMICA(MICA):
    """MICA-Core plus one of the three predeclared intrinsic simplifications."""

    CONTROLS = ("core", "one_clinical_block", "no_post_read_conditioner", "simplified_head")

    def __init__(self, diagnosis_count: int, procedure_count: int, control: str = "core") -> None:
        if control not in self.CONTROLS:
            raise ValueError(f"control must be one of {self.CONTROLS}")
        super().__init__(diagnosis_count, procedure_count, variant="drug_query")
        self.control = control
        if control == "one_clinical_block":
            # Keep the first of the current blocks and remove the second.  The
            # retained block has exactly the historical initialization.
            self.blocks = nn.ModuleList([self.blocks[0]])
        elif control == "no_post_read_conditioner":
            # No parameters remain on this seam; medication-specific attention
            # still supplies the context consumed by the prediction head.
            self.conditioner = None
        elif control == "simplified_head":
            # The medication bias remains a separate learned scalar in
            # MICA.forward; the head sees only [c, e, c*e].
            self.head = nn.Linear(3 * DIM, 1)
            nn.init.xavier_uniform_(self.head.weight)
            nn.init.zeros_(self.head.bias)

    def condition_context(self, context: torch.Tensor, drugs: torch.Tensor) -> torch.Tensor:
        if self.control == "no_post_read_conditioner":
            return context
        return super().condition_context(context, drugs)
