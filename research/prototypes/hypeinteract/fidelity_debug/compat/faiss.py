"""Exact FAISS-compatible L2 shim used when the environment lacks faiss-gpu.

CUDA tensors stay on the selected device so the official retrieval loop keeps
the same squared-L2/top-k semantics without turning every batch into a CPU
NumPy operation.
"""

import numpy as np
import torch


class StandardGpuResources:
    pass


class GpuIndexFlatL2:
    def __init__(self, _resources, dimension):
        self.dimension = int(dimension)
        self._memory = None

    def add(self, values):
        if torch.is_tensor(values):
            if values.ndim != 2 or values.shape[1] != self.dimension:
                raise ValueError("FAISS shim received an invalid memory shape")
            self._memory = values.detach()
            return
        array = np.asarray(values)
        if array.ndim != 2 or array.shape[1] != self.dimension:
            raise ValueError("FAISS shim received an invalid memory shape")
        self._memory = np.asarray(array, dtype=np.float32)

    def search(self, queries, k):
        if self._memory is None:
            raise RuntimeError("FAISS shim index has no memory")
        if torch.is_tensor(queries):
            memory = self._memory
            if not torch.is_tensor(memory):
                memory = torch.from_numpy(memory).to(device=queries.device)
            else:
                memory = memory.to(device=queries.device)
            query = queries.detach()
            distances = (
                query.square().sum(dim=1, keepdim=True)
                + memory.square().sum(dim=1).unsqueeze(0)
                - 2.0 * query.matmul(memory.transpose(0, 1))
            ).clamp_min_(0.0)
            return torch.topk(distances, int(k), dim=1, largest=False, sorted=True)
        array = np.asarray(queries)
        memory = self._memory.detach().cpu().numpy() if torch.is_tensor(self._memory) else self._memory
        distances = ((array[:, None, :] - memory[None, :, :]) ** 2).sum(axis=-1)
        order = np.argsort(distances, axis=1, kind="mergesort")[:, : int(k)]
        selected = np.take_along_axis(distances, order, axis=1)
        return torch.from_numpy(selected.astype(np.float32)), torch.from_numpy(order.astype(np.int64))
