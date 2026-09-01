# SafeDrug archived shared-source preflight

The active SafeDrug-family source is `ycq091044/SafeDrug@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`. One source provides the GAMENet, SafeDrug, RETAIN, and LEAP model lanes plus their shared paper-reproduction preprocessing, split, and evaluation code.

The upstream README identifies this branch as the IJCAI paper reproduction path and declares Python 3.7, PyTorch 1.4.0, SciPy 1.5.2, pandas 1.1.3, and NumPy 1.19.2. License disposition remains unresolved.

The checked-in entrypoints are not directly trainable through their CLI defaults: all four define `--Test` as `store_true` with `default=True`, and no inverse flag selects training. The active reproduction plan therefore requires one harness-owned mechanical adaptation before launch. That adaptation may select the existing training branch but may not import SafeDrug-main code or change model, data, split, optimizer, checkpoint, prediction, or evaluation behavior.

No archived lane is ready until preprocessing produces 6,350 patients, 14,995 visits, 131 medications, 448 DDI pairs, and 491 molecular substructures and the 319 environment and adaptation smoke pass.
