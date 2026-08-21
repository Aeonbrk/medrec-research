#!/bin/bash
# Universal Baseline Runner for SafeDrug repository baselines
# Supports: GAMENet, SafeDrug, Retain, Leap, DMNC, ECC, LR

set -eu

# ============================================================================
# Configuration
# ============================================================================
BASELINE_NAME="${1:-gamenet}"  # Default to gamenet if no argument
SAFEDRUG_ROOT="${SAFEDRUG_ROOT:-/root/zhb/SafeDrug}"
MIMIC_DATA_ROOT="${MIMIC_DATA_ROOT:-/root/zhb/Search/dataset/mimic-iii-1.4}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/root/zhb/medrec-data/baselines}"
CONDA_ENV="${CONDA_ENV:-medrec-gamenet}"

# Map baseline names to Python files
declare -A BASELINE_FILES=(
    ["gamenet"]="GAMENet.py"
    ["safedrug"]="SafeDrug.py"
    ["retain"]="Retain.py"
    ["leap"]="Leap.py"
    ["dmnc"]="DMNC.py"
    ["ecc"]="ECC.py"
    ["lr"]="LR.py"
)

BASELINE_FILE="${BASELINE_FILES[${BASELINE_NAME}]}"
if [ -z "${BASELINE_FILE}" ]; then
    echo "Error: Unknown baseline '${BASELINE_NAME}'"
    echo "Available baselines: ${!BASELINE_FILES[@]}"
    exit 1
fi

# Output paths
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_FILE="${OUTPUT_ROOT}/${BASELINE_NAME}_result.json"
LOG_FILE="${OUTPUT_ROOT}/${BASELINE_NAME}_${TIMESTAMP}.log"

echo "================================================"
echo "Baseline Runner: ${BASELINE_NAME}"
echo "================================================"
echo "SafeDrug root: ${SAFEDRUG_ROOT}"
echo "MIMIC data: ${MIMIC_DATA_ROOT}"
echo "Output: ${OUTPUT_FILE}"
echo "Log: ${LOG_FILE}"
echo "================================================"

# ============================================================================
# Step 1: Prepare data (shared by all baselines)
# ============================================================================
cd "${SAFEDRUG_ROOT}/data"

if [ ! -f "output/records_final.pkl" ]; then
    echo "[1/3] Processing data..."

    # Ensure input directory exists
    mkdir -p input

    # Link MIMIC-III data files
    cd input
    ln -sf "${MIMIC_DATA_ROOT}/PRESCRIPTIONS.csv.gz" . 2>/dev/null || true
    ln -sf "${MIMIC_DATA_ROOT}/DIAGNOSES_ICD.csv.gz" . 2>/dev/null || true
    ln -sf "${MIMIC_DATA_ROOT}/PROCEDURES_ICD.csv.gz" . 2>/dev/null || true

    # Decompress if needed
    if [ ! -f "PRESCRIPTIONS.csv" ]; then
        gunzip -k PRESCRIPTIONS.csv.gz
    fi
    if [ ! -f "DIAGNOSES_ICD.csv" ]; then
        gunzip -k DIAGNOSES_ICD.csv.gz
    fi
    if [ ! -f "PROCEDURES_ICD.csv" ]; then
        gunzip -k PROCEDURES_ICD.csv.gz
    fi

    cd ..

    # Run data processing
    source /root/anaconda3/etc/profile.d/conda.sh
    conda activate "${CONDA_ENV}"
    python processing.py 2>&1 | tee -a "${LOG_FILE}"
else
    echo "[1/3] Data already processed (records_final.pkl exists)"
fi

# ============================================================================
# Step 2: Train baseline
# ============================================================================
echo "[2/3] Training ${BASELINE_NAME}..."
cd "${SAFEDRUG_ROOT}/src"

source /root/anaconda3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV}"

# Run baseline training
python "${BASELINE_FILE}" 2>&1 | tee -a "${LOG_FILE}"

# ============================================================================
# Step 3: Extract metrics from log and create result.json
# ============================================================================
echo "[3/3] Extracting metrics from log..."

# Parse metrics from log file
# Expected formats:
# - "DDI Rate: X.XXXX, Jaccard: X.XXXX, PRAUC: X.XXXX, AVG_F1: X.XXXX"
# - "Test: DDI Rate: X.XXXX Jaccard: X.XXXX F1: X.XXXX PRAUC: X.XXXX"

JACCARD=$(grep -oP '(?:Jaccard|JA)[:\s]+\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
PRAUC=$(grep -oP 'PRAUC[:\s]+\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
F1=$(grep -oP '(?:AVG_F1|F1)[:\s]+\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
DDI_RATE=$(grep -oP 'DDI[:\s]+(?:Rate:)?\s*\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")

# Fallback: check if metrics are all 0.0, try alternative parsing
if [ "${JACCARD}" = "0.0" ] && [ "${PRAUC}" = "0.0" ]; then
    echo "Warning: Could not parse metrics from log, check format"
    echo "Last 30 lines of log:"
    tail -30 "${LOG_FILE}"
fi

# Create standardized result.json
cat > "${OUTPUT_FILE}" << EOF
{
  "baseline_id": "${BASELINE_NAME}",
  "dataset": "mimic-iii-1.4",
  "metrics": {
    "jaccard": ${JACCARD},
    "prauc": ${PRAUC},
    "f1": ${F1},
    "ddi_rate": ${DDI_RATE}
  },
  "training_info": {
    "source_repository": "https://github.com/ycq091044/SafeDrug",
    "source_revision": "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
    "baseline_file": "${BASELINE_FILE}",
    "conda_env": "${CONDA_ENV}"
  },
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "completed",
  "log_file": "${LOG_FILE}"
}
EOF

echo "================================================"
echo "✓ ${BASELINE_NAME} training completed"
echo "✓ Results saved to: ${OUTPUT_FILE}"
echo "✓ Full log: ${LOG_FILE}"
echo "================================================"

cat "${OUTPUT_FILE}"
