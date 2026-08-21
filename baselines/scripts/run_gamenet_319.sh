#!/bin/bash
# GAMENet Baseline 运行脚本 for 319-wild
# 包含完整的数据准备、训练、结果提取流程

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================
BASELINE_NAME="${1:-gamenet}"
SAFEDRUG_ROOT="${SAFEDRUG_ROOT:-/root/zhb/SafeDrug}"
MEDREC_DATA_ROOT="${MEDREC_DATA_ROOT:-/data/medrec}"
CONDA_ENV="${CONDA_ENV:-medrec-gamenet}"
GPU_ID="${GPU_ID:-0}"

# 输出路径
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="${MEDREC_DATA_ROOT}/baselines/${BASELINE_NAME}"
RESULT_FILE="${OUTPUT_DIR}/result.json"
LOG_FILE="${OUTPUT_DIR}/run_${TIMESTAMP}.log"

mkdir -p "$OUTPUT_DIR"

echo "================================================"
echo "GAMENet Baseline Runner"
echo "================================================"
echo "SafeDrug 根目录: ${SAFEDRUG_ROOT}"
echo "数据根目录: ${MEDREC_DATA_ROOT}"
echo "Conda 环境: ${CONDA_ENV}"
echo "GPU: ${GPU_ID}"
echo "输出目录: ${OUTPUT_DIR}"
echo "日志文件: ${LOG_FILE}"
echo "================================================"
echo ""

# ============================================================================
# Phase 1: 环境激活
# ============================================================================
echo "[Phase 1/4] 激活 Conda 环境..."
source /root/anaconda3/etc/profile.d/conda.sh
conda activate "$CONDA_ENV"
echo "✓ 环境已激活: $(which python)"
echo ""

# ============================================================================
# Phase 2: 数据准备
# ============================================================================
echo "[Phase 2/4] 检查数据..."

# 检查 records_final.pkl 是否存在
RECORDS_FILE="${SAFEDRUG_ROOT}/data/output/records_final.pkl"
if [ -f "$RECORDS_FILE" ]; then
    echo "✓ 数据已准备: ${RECORDS_FILE}"
else
    echo "⚠ 数据未处理，开始数据预处理..."

    cd "${SAFEDRUG_ROOT}/data"

    # 确保 input 目录存在
    mkdir -p input

    # 链接 MIMIC-III 数据文件（假设在 MEDREC_DATA_ROOT/mimic-iii）
    MIMIC_DIR="${MEDREC_DATA_ROOT}/mimic-iii"
    if [ ! -d "$MIMIC_DIR" ]; then
        echo "✗ MIMIC-III 数据目录不存在: ${MIMIC_DIR}"
        echo "  请将 MIMIC-III 数据放到该目录，包含:"
        echo "    - PRESCRIPTIONS.csv"
        echo "    - DIAGNOSES_ICD.csv"
        echo "    - PROCEDURES_ICD.csv"
        exit 1
    fi

    cd input
    for file in PRESCRIPTIONS.csv DIAGNOSES_ICD.csv PROCEDURES_ICD.csv; do
        if [ ! -f "$file" ]; then
            if [ -f "${MIMIC_DIR}/${file}.gz" ]; then
                echo "  解压 ${file}.gz..."
                gunzip -c "${MIMIC_DIR}/${file}.gz" > "$file"
            elif [ -f "${MIMIC_DIR}/${file}" ]; then
                echo "  链接 ${file}..."
                ln -sf "${MIMIC_DIR}/${file}" .
            else
                echo "✗ 找不到 ${file}"
                exit 1
            fi
        fi
    done
    cd ..

    echo "  运行数据处理脚本..."
    python processing.py 2>&1 | tee -a "${LOG_FILE}"

    if [ ! -f "$RECORDS_FILE" ]; then
        echo "✗ 数据处理失败"
        exit 1
    fi
    echo "✓ 数据处理完成"
fi
echo ""

# ============================================================================
# Phase 3: 训练 GAMENet
# ============================================================================
echo "[Phase 3/4] 训练 GAMENet..."
cd "${SAFEDRUG_ROOT}/src"

# 设置 GPU
export CUDA_VISIBLE_DEVICES="$GPU_ID"

echo "  开始训练（日志: ${LOG_FILE}）..."
python GAMENet.py --cuda 0 2>&1 | tee -a "${LOG_FILE}"

echo "✓ 训练完成"
echo ""

# ============================================================================
# Phase 4: 提取结果
# ============================================================================
echo "[Phase 4/4] 提取结果..."

# 从日志提取指标
JACCARD=$(grep -oP 'Jaccard[:\s]+\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
PRAUC=$(grep -oP 'PRAUC[:\s]+\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
F1=$(grep -oP '(?:AVG_F1|F1)[:\s]+\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")
DDI_RATE=$(grep -oP 'DDI[:\s]+(?:Rate:)?\s*\K[0-9.]+' "${LOG_FILE}" | tail -1 || echo "0.0")

if [ "$JACCARD" = "0.0" ] && [ "$PRAUC" = "0.0" ]; then
    echo "⚠ 警告: 无法从日志提取指标，请检查训练输出"
    echo "  日志最后 20 行:"
    tail -20 "${LOG_FILE}"
fi

# 生成结果 JSON
cat > "$RESULT_FILE" << EOF
{
  "baseline_id": "${BASELINE_NAME}",
  "dataset": "mimic-iii",
  "metrics": {
    "jaccard": ${JACCARD},
    "prauc": ${PRAUC},
    "f1": ${F1},
    "ddi_rate": ${DDI_RATE}
  },
  "training_info": {
    "source_repository": "https://github.com/ycq091044/SafeDrug",
    "conda_env": "${CONDA_ENV}",
    "gpu": ${GPU_ID},
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "files": {
    "log": "${LOG_FILE}",
    "output_dir": "${OUTPUT_DIR}"
  },
  "status": "completed"
}
EOF

echo "✓ 结果已保存"
echo ""
echo "================================================"
echo "运行完成"
echo "================================================"
echo "结果文件: ${RESULT_FILE}"
echo ""
cat "$RESULT_FILE"
echo ""
echo "如需查看完整日志:"
echo "  cat ${LOG_FILE}"
