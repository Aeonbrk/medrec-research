class WithinEmbedContrast:
    def __init__(self, loss=None, **_kwargs):
        self.loss = loss

    def __call__(self, first, second):
        return self.loss(first, second) if self.loss is not None else first.sum() * 0.0
