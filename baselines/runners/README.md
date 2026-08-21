# Baseline Runners

Universal runner for SafeDrug repository baselines.

## Available Baselines

All baselines are from the [SafeDrug repository](https://github.com/ycq091044/SafeDrug):

- **GAMENet**: Graph Augmented Memory Networks
- **SafeDrug**: Dual Molecular Graph Encoders (the main method)
- **Retain**: Reverse Time Attention Model
- **Leap**: LEAP baseline
- **DMNC**: Differentiable Memory Neural Computer
- **ECC**: ECC baseline
- **LR**: Logistic Regression baseline

## Usage

```bash
# Run a specific baseline
bash baselines/runners/run_baseline.sh gamenet

# Or with custom paths
SAFEDRUG_ROOT=/path/to/SafeDrug \
MIMIC_DATA_ROOT=/path/to/mimic \
OUTPUT_ROOT=/path/to/output \
bash baselines/runners/run_baseline.sh safedrug
```

## Data Processing

The script handles data processing automatically:

1. Links MIMIC-III files from data root
2. Runs `data/processing.py` if `records_final.pkl` doesn't exist
3. All baselines share the same processed data

## Output Format

Each run produces:

- `{baseline}_result.json` - Standardized metrics (jaccard, prauc, f1, ddi_rate)
- `{baseline}_{timestamp}.log` - Full training log

## Prerequisites

- Conda environment with: `python=3.8`, `rdkit`, `torch`, `dill`, `numpy`, `pandas`, `scikit-learn`
- MIMIC-III dataset downloaded and extracted
- SafeDrug repository cloned
