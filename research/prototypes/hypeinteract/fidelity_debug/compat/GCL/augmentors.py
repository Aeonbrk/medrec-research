class Compose:
    def __init__(self, augmentors):
        self.augmentors = augmentors

    def __call__(self, x, edge_index, edge_weight=None):
        for augmentor in self.augmentors:
            x, edge_index, edge_weight = augmentor(x, edge_index, edge_weight)
        return x, edge_index, edge_weight


class EdgeRemoving:
    def __init__(self, pe=0.0):
        self.pe = pe

    def __call__(self, x, edge_index, edge_weight=None):
        return x, edge_index, edge_weight


class FeatureDropout:
    def __init__(self, pf=0.0):
        self.pf = pf

    def __call__(self, x, edge_index, edge_weight=None):
        return x, edge_index, edge_weight


class NodeDropping:
    def __init__(self, pn=0.0):
        self.pn = pn

    def __call__(self, x, edge_index, edge_weight=None):
        return x, edge_index, edge_weight
