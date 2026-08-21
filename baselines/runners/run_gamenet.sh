#!/bin/bash
# GAMENet Baseline Runner for 319-lab
# This script runs GAMENet baseline and outputs standardized result.json

set -eu

# ============================================================================
# Configuration
# ============================================================================
SAFEDRUG_ROOT="${SAFEDRUG_ROOT:-/root/zhb/SafeDrug}"
MIMIC_DATA_ROOT="${MIMIC_DATA_ROOT:-/root/zhb/Search/dataset/mimic-iii-1.4}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/root/zhb/medrec-data/baselines}"
CONDA_ENV="${CONDA_ENV:-medrec-gamenet}"

# Output paths
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_FILE="${OUTPUT_ROOT}/gamenet_result.json"
LOG_FILE="${OUTPUT_ROOT}/gamenet_${TIMESTAMP}.log"

echo "================================================"
echo "GAMENet Baseline Runner"
echo "================================================"
echo "SafeDrug root: ${SAFEDRUG_ROOT}"
echo "MIMIC data: ${MIMIC_DATA_ROOT}"
echo "Output: ${OUTPUT_FILE}"
echo "Log: ${LOG_FILE}"
echo "================================================"

# ============================================================================
# Step 1: Prepare data (if not already processed)
# ============================================================================
cd "${SAFEDRUG_ROOT}/data"

if [ ! -f "output/records_final.pkl" ]; then
    echo "[1/3] Data not processed, running processing.py..."

    # Link MIMIC-III data files
    mkdir -p input
    ln -sf "${MIMIC_DATA_ROOT}/PRESCRIPTIONS.csv.gz" input/PRESCRIPTIONS.csv.gz
    ln -sf "${MIMIC_DATA_ROOT}/DIAGNOSES_ICD.csv.gz" input/DIAGNOSES_ICD.csv.gz
    ln -sf "${MIMIC_DATA_ROOT}/PROCEDURES_ICD.csv.gz" input/PROCEDURES_ICD.csv.gz

    # Run data processing
    source /root/anaconda3/etc/profile.d/conda.sh
    conda activate "${CONDA_ENV}"
    python processing.py 2>&1 | tee -a "${LOG_FILE}"
else
    echo "[1/3] Data already processed, skipping..."
fi

# ============================================================================
# Step 2: Train GAMENet
# ============================================================================
echo "[2/3] Training GAMENet..."
cd "${SAFEDRUG_ROOT}/src"

source /root/anaconda3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV}"

# Run GAMENet training
python GAMENet.py \
    --model_name GAMENet \
    --target_ddi 0.06 \
    --lr 1e-4 \
    --cuda 0 \
    2>&1 | tee -a "${LOG_FILE}"

# ============================================================================
# Step 3: Extract final metrics and create result.json
# ============================================================================
echo "[3/3] Extracting metrics..."

# Parse last epoch metrics from log
# Expected format from GAMENet.py:
# epoch XX, loss: X.XXXX, One epoch time: X.XXs, Appro left time: X.XXh
# DDI Rate: X.XXXX, Jaccard: X.XXXX, PRAUC: X.XXXX, AVG_F1: X.XXXX, AVG_PRC: X.XXXX

# Extract metrics (this is a placeholder - actual parsing depends on GAMENet output format)
JACCARD=$(grep -oP 'Jaccard: \K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
PRAUC=$(grep -oP 'PRAUC: \K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
F1=$(grep -oP 'AVG_F1: \K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
DDI_RATE=$(grep -oP 'DDI Rate: \K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")

# Create standardized result.json
cat > "${OUTPUT_FILE}" << EOF
{
  "baseline_id": "gamenet",
  "dataset": "mimic-iii-1.4",
  "metrics": {
    "jaccard": ${JACCARD},
    "prauc": ${PRAUC},
    "f1": ${F1},
    "ddi_rate": ${DDI_RATE}
  },
  "training_info": {
    "source_revision": "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
    "conda_env": "${CONDA_ENV}",
    "target_ddi": 0.06,
    "learning_rate": 1e-4
  },
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "completed",
  "log_file": "${LOG_FILE}"
}
EOF

echo "================================================"
echo "✓ GAMENet training completed"
echo "✓ Results saved to: ${OUTPUT_FILE}"
echo "✓ Full log: ${LOG_FILE}"
echo "================================================"

cat "${OUTPUT_FILE}"
