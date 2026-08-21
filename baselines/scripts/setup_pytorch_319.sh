#!/bin/bash
# PyTorch 安装脚本 for 319-wild (CUDA 12.2 with PyTorch 1.8.0)
# 多种方式确保安装成功

set -euo pipefail

CONDA_ENV="${1:-medrec-gamenet}"

echo "=== PyTorch 安装脚本 ==="
echo "目标环境: $CONDA_ENV"

source /root/anaconda3/etc/profile.d/conda.sh
conda activate "$CONDA_ENV"

echo ""
echo "[1/3] 检查当前 PyTorch 状态..."
if python -c "import torch; print(torch.__version__); assert torch.cuda.is_available()" 2>/dev/null; then
    echo "✓ PyTorch 已安装且 CUDA 可用"
    python -c "import torch; print(f'  版本: {torch.__version__}'); print(f'  GPU 数量: {torch.cuda.device_count()}')"
    exit 0
fi

echo ""
echo "[2/3] 尝试方式 1: 官方 PyPI 源 (推荐)"
if pip install torch==1.8.0+cu111 torchvision==0.9.0+cu111 torchaudio==0.8.0 \
    -f https://download.pytorch.org/whl/torch_stable.html \
    --timeout 60 2>/dev/null; then
    echo "✓ 方式 1 成功"
else
    echo "✗ 方式 1 失败，尝试方式 2..."

    echo ""
    echo "[2/3] 尝试方式 2: 清华镜像"
    pip install torch==1.8.0 torchvision==0.9.0 \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --timeout 60 || {
        echo "✗ 方式 2 也失败"
        echo ""
        echo "建议手动安装:"
        echo "  1. 下载: wget https://download.pytorch.org/whl/cu111/torch-1.8.0%2Bcu111-cp38-cp38-linux_x86_64.whl"
        echo "  2. 安装: pip install torch-1.8.0+cu111-cp38-cp38-linux_x86_64.whl"
        exit 1
    }
fi

echo ""
echo "[3/3] 验证安装..."
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'GPU 0: {torch.cuda.get_device_name(0)}')
else:
    print('ERROR: CUDA not available!')
    exit(1)
"

echo ""
echo "✓ PyTorch 安装成功"
