"""Small local InfoNCE implementation matching the official call surface."""

import torch
import torch.nn.functional as F


class InfoNCE:
    def __init__(self, reduction="mean", temperature=0.1, **_kwargs):
        self.reduction = reduction
        self.temperature = temperature

    def __call__(self, query, positive_key, negative_keys=None):
        query = F.normalize(query, dim=-1)
        positive_key = F.normalize(positive_key, dim=-1)
        if negative_keys is None:
            logits = query @ positive_key.transpose(0, 1) / self.temperature
            labels = torch.arange(logits.shape[0], device=logits.device)
            return F.cross_entropy(logits, labels, reduction=self.reduction)
        positive = (query * positive_key).sum(dim=-1, keepdim=True)
        if negative_keys.ndim == 2:
            negative_keys = negative_keys.unsqueeze(0).expand(query.shape[0], -1, -1)
        negative = torch.bmm(negative_keys, query.unsqueeze(-1)).squeeze(-1)
        logits = torch.cat((positive, negative), dim=-1) / self.temperature
        labels = torch.zeros(query.shape[0], dtype=torch.long, device=query.device)
        return F.cross_entropy(logits, labels, reduction=self.reduction)
