#!/bin/bash
# 319-wild 环境验证脚本
# 在运行实验前检查所有必要条件

set -euo pipefail

echo "=== 319-wild 环境验证 ==="
echo ""

# 1. 检查 CUDA
echo "[1/6] 检查 CUDA..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "✗ nvidia-smi 不可用"
    exit 1
fi
nvidia-smi --query-gpu=index,name,memory.total,memory.free,utilization.gpu --format=csv,noheader | head -2
echo "✓ CUDA 可用"
echo ""

# 2. 检查 Conda
echo "[2/6] 检查 Conda..."
source /root/anaconda3/etc/profile.d/conda.sh
conda env list | grep medrec-gamenet || {
    echo "✗ medrec-gamenet 环境不存在"
    exit 1
}
echo "✓ Conda 环境存在"
echo ""

# 3. 检查 PyTorch
echo "[3/6] 检查 PyTorch..."
conda activate medrec-gamenet
python -c "
import torch
assert torch.cuda.is_available(), 'CUDA not available'
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA: {torch.version.cuda}')
print(f'  GPUs: {torch.cuda.device_count()}')
" || {
    echo "✗ PyTorch 或 CUDA 不可用"
    exit 1
}
echo "✓ PyTorch + CUDA 正常"
echo ""

# 4. 检查数据目录
echo "[4/6] 检查数据目录..."
DATA_ROOT="${MEDREC_DATA_ROOT:-/data/medrec}"
if [ ! -d "$DATA_ROOT" ]; then
    echo "✗ 数据目录不存在: $DATA_ROOT"
    echo "  请设置 MEDREC_DATA_ROOT 环境变量或创建 /data/medrec"
    exit 1
fi
echo "  数据根目录: $DATA_ROOT"
echo "✓ 数据目录存在"
echo ""

# 5. 检查 SafeDrug 代码
echo "[5/6] 检查 SafeDrug 代码..."
SAFEDRUG_ROOT="${SAFEDRUG_ROOT:-/root/zhb/SafeDrug}"
if [ ! -d "$SAFEDRUG_ROOT" ]; then
    echo "✗ SafeDrug 目录不存在: $SAFEDRUG_ROOT"
    exit 1
fi
if [ ! -f "$SAFEDRUG_ROOT/src/GAMENet.py" ]; then
    echo "✗ GAMENet.py 不存在"
    exit 1
fi
echo "  SafeDrug 根目录: $SAFEDRUG_ROOT"
echo "✓ SafeDrug 代码存在"
echo ""

# 6. 检查磁盘空间
echo "[6/6] 检查磁盘空间..."
df -h "$DATA_ROOT" | tail -1
USAGE=$(df -h "$DATA_ROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -gt 90 ]; then
    echo "⚠ 磁盘使用率 > 90%，可能空间不足"
else
    echo "✓ 磁盘空间充足"
fi
echo ""

echo "=== 环境验证通过 ==="
echo ""
echo "建议的环境变量:"
echo "  export MEDREC_DATA_ROOT=$DATA_ROOT"
echo "  export SAFEDRUG_ROOT=$SAFEDRUG_ROOT"
