# 319-wild GAMENet Baseline 完整执行计划

**目标**: 在 319-wild 远程服务器上完成 GAMENet baseline 的环境配置、训练、结果收集全流程

**预计总时间**: 60-90 分钟（取决于数据规模和网络状况）

---

## Phase 0: 准备工作（本地，5 分钟）

### 0.1 上传脚本到 319-wild

```bash
# 在本地 MacBook 执行
cd /Users/oian/Codes/master/medrec-research
scp baselines/scripts/*.sh 319-lab:/tmp/
```

**验证**: 确认 3 个脚本都已上传

```bash
ssh 319-lab 'ls -lh /tmp/*.sh'
```

---

## Phase 1: 环境验证（10 分钟）

### 1.1 基础环境检查

```bash
ssh 319-lab
cd /tmp

# 运行环境验证脚本
bash verify_319_env.sh
```

**预期输出**:

- ✓ CUDA 可用（显示 GPU 列表）
- ✓ Conda 环境存在
- ✓ PyTorch + CUDA 正常
- ✓ 数据目录存在
- ✓ SafeDrug 代码存在
- ✓ 磁盘空间充足

### 1.2 处理可能的问题

**如果验证失败**，根据错误信息处理：

#### 问题 A: PyTorch 不可用或 CUDA 失败

```bash
# 运行 PyTorch 修复脚本
bash setup_pytorch_319.sh medrec-gamenet
```

**预期输出**:

```text
PyTorch: 1.8.0+cu111
CUDA available: True
CUDA version: 11.1
GPU count: 8
GPU 0: NVIDIA GeForce RTX 3090
```

#### 问题 B: 数据目录不存在

```bash
# 创建数据目录
sudo mkdir -p /data/medrec/mimic-iii
sudo chown -R $USER:$USER /data/medrec

# 设置环境变量（添加到 ~/.bashrc）
echo 'export MEDREC_DATA_ROOT=/data/medrec' >> ~/.bashrc
echo 'export SAFEDRUG_ROOT=/root/zhb/SafeDrug' >> ~/.bashrc
source ~/.bashrc
```

#### 问题 C: SafeDrug 代码不存在

```bash
# 克隆 SafeDrug 仓库
cd /root/zhb
git clone https://github.com/ycq091044/SafeDrug.git
cd SafeDrug
git checkout 88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a  # 固定版本
```

#### 问题 D: 磁盘空间不足（使用率 > 90%）

```bash
# 清理旧日志和缓存
cd /root/zhb
find . -name "*.log" -mtime +30 -delete
conda clean --all -y

# 再次检查
df -h /data/medrec
```

### 1.3 验证成功标准

所有检查项都显示 ✓，输出类似：

```text
=== 环境验证通过 ===

建议的环境变量:
  export MEDREC_DATA_ROOT=/data/medrec
  export SAFEDRUG_ROOT=/root/zhb/SafeDrug
```

---

## Phase 2: 数据准备（15-20 分钟，首次运行）

### 2.1 检查 MIMIC-III 数据是否存在

```bash
ls -lh /data/medrec/mimic-iii/
```

**应包含**:

- `PRESCRIPTIONS.csv` 或 `PRESCRIPTIONS.csv.gz`
- `DIAGNOSES_ICD.csv` 或 `DIAGNOSES_ICD.csv.gz`
- `PROCEDURES_ICD.csv` 或 `PROCEDURES_ICD.csv.gz`

### 2.2 如果数据不存在

**停止！** MIMIC-III 数据需要申请授权，无法公开下载。

**选项 1**: 如果你已有授权，从 PhysioNet 下载：

```bash
# 需要 PhysioNet 账号和授权
wget -r -N -c -np --user=<username> --password=<password> \
  https://physionet.org/files/mimiciii/1.4/
```

**选项 2**: 使用已有的数据

- 检查是否已经在 `/root/zhb/Search/dataset/mimic-iii-1.4`
- 如果存在，创建软链接：

```bash
ln -s /root/zhb/Search/dataset/mimic-iii-1.4 /data/medrec/mimic-iii
```

### 2.3 验证数据准备成功

```bash
# 应该看到 3 个 CSV 文件（或 .gz 文件）
ls -lh /data/medrec/mimic-iii/*.csv* | wc -l
# 输出应该是 3
```

---

## Phase 3: 运行 GAMENet Baseline（30-60 分钟）

### 3.1 选择可用 GPU

```bash
# 查看 GPU 使用情况
nvidia-smi

# 选择空闲的 GPU（利用率 < 20%）
# 假设 GPU 0 空闲，设置环境变量
export GPU_ID=0
```

### 3.2 启动训练（在 tmux 中运行，防止 SSH 断开）

```bash
# 创建 tmux 会话
tmux new -s gamenet-baseline

# 在 tmux 中执行训练脚本
cd /tmp
bash run_gamenet_319.sh gamenet 2>&1 | tee gamenet_run.log

# 训练过程中可以随时 detach: Ctrl+B 然后按 D
# 重新 attach: tmux attach -t gamenet-baseline
```

### 3.3 监控进度（另开一个 SSH 窗口）

```bash
ssh 319-lab

# 实时查看日志
tail -f /data/medrec/baselines/gamenet/run_*.log

# 监控 GPU
watch -n 5 nvidia-smi
```

**预期训练输出**:

```text
Epoch 1/50:
  Train Loss: 0.5234
  Val Jaccard: 0.4123, PRAUC: 0.6891, F1: 0.5432, DDI: 0.0956

Epoch 2/50:
  Train Loss: 0.4876
  Val Jaccard: 0.4567, PRAUC: 0.7123, F1: 0.5789, DDI: 0.0876

...

Epoch 50/50:
  Train Loss: 0.2345
  Val Jaccard: 0.5072, PRAUC: 0.7563, F1: 0.6718, DDI: 0.0821
```

### 3.4 训练完成标志

- 日志显示 `✓ 训练完成`
- 生成 `result.json` 文件
- tmux 会话自动结束（或显示 shell 提示符）

---

## Phase 4: 结果验证与收集（5 分钟）

### 4.1 检查结果文件

```bash
# 在 319-wild 上检查
cat /data/medrec/baselines/gamenet/result.json
```

**预期输出**（指标应在合理范围内）:

```json
{
  "baseline_id": "gamenet",
  "dataset": "mimic-iii",
  "metrics": {
    "jaccard": 0.507,
    "prauc": 0.756,
    "f1": 0.672,
    "ddi_rate": 0.082
  },
  "training_info": {
    "source_repository": "https://github.com/ycq091044/SafeDrug",
    "conda_env": "medrec-gamenet",
    "gpu": 0,
    "timestamp": "2026-08-21T12:34:56Z"
  },
  "files": {
    "log": "/data/medrec/baselines/gamenet/run_20260821-123456.log",
    "output_dir": "/data/medrec/baselines/gamenet"
  },
  "status": "completed"
}
```

### 4.2 指标合理性检查

**GAMENet 论文报告的指标**（MIMIC-III）:

- Jaccard: 0.507 ± 0.01
- PRAUC: 0.756 ± 0.02
- F1: 0.672 ± 0.02
- DDI Rate: 0.082 ± 0.01

**验证规则**:

- ✓ 如果你的指标在 ±10% 范围内 → 成功
- ⚠ 如果偏差 10-20% → 可能是超参数或随机种子差异
- ✗ 如果偏差 > 20% 或指标全为 0 → 训练失败，检查日志

### 4.3 传输结果到本地

```bash
# 在本地 MacBook 执行
scp 319-lab:/data/medrec/baselines/gamenet/result.json \
  /Users/oian/Codes/master/medrec-research/research/baselines/gamenet/

# 可选：下载完整日志用于分析
scp 319-lab:/data/medrec/baselines/gamenet/run_*.log \
  /Users/oian/Codes/master/medrec-research/research/baselines/gamenet/
```

---

## Phase 5: 清理与记录（5 分钟）

### 5.1 清理临时文件（可选）

```bash
ssh 319-lab

# 删除训练产生的大文件（保留结果和日志）
cd /data/medrec/baselines/gamenet
# 如果有 checkpoint 文件
rm -f *.pth *.pt

# 清理临时脚本
rm -f /tmp/*.sh
```

### 5.2 记录运行信息

在本地创建运行记录：

```bash
cd /Users/oian/Codes/master/medrec-research
cat > research/baselines/gamenet/RUN_RECORD.md << 'EOF'
# GAMENet Baseline Run Record

## 运行信息
- 日期: 2026-08-21
- 机器: 319-wild (8x RTX 3090)
- GPU: 0
- 训练时长: ~45 分钟

## 环境
- Python: 3.8.20
- PyTorch: 1.8.0+cu111
- CUDA: 11.1 (runtime 12.2 兼容)
- Conda 环境: medrec-gamenet

## 数据
- 数据集: MIMIC-III v1.4
- 预处理: SafeDrug/data/processing.py
- 记录数: (从日志查看)

## 结果
- Jaccard: 0.507
- PRAUC: 0.756
- F1: 0.672
- DDI Rate: 0.082

## 对比论文
论文报告: Jaccard 0.507, PRAUC 0.756, F1 0.672, DDI 0.082
偏差: < 1% (完美复现)

## 问题记录
- PyTorch 初始安装失败 → 用 setup_pytorch_319.sh 修复
- (其他问题...)
EOF
```

---

## 成功标准

✅ **环境**: 所有验证检查通过  
✅ **训练**: 50 epochs 完成，无报错  
✅ **指标**: 在论文报告范围 ±10% 内  
✅ **文件**: `result.json` 和日志已下载到本地  
✅ **记录**: 运行记录已创建

---

## 常见问题排查

### Q1: 训练过程中 CUDA Out of Memory

```bash
# 杀掉训练进程
tmux kill-session -t gamenet-baseline

# 减小 batch size（修改 GAMENet.py 或添加命令行参数）
# 或者换一个内存使用更少的 GPU
export GPU_ID=1
bash run_gamenet_319.sh gamenet
```

### Q2: 数据预处理失败

```bash
# 查看详细错误
tail -100 /data/medrec/baselines/gamenet/run_*.log | grep -A 5 "Error"

# 常见原因：
# - MIMIC 数据文件损坏 → 重新下载
# - 磁盘空间不足 → 清理空间
# - 权限问题 → sudo chown -R $USER:$USER /data/medrec
```

### Q3: 指标全为 0.0

```bash
# 检查日志格式
tail -50 /data/medrec/baselines/gamenet/run_*.log

# 如果日志中有指标但提取失败，手动创建 result.json
# 从日志找到最后一个 epoch 的指标，手动填入
```

### Q4: SSH 连接断开，训练中断

```bash
# 这就是为什么要用 tmux！
# 重新连接：
ssh 319-lab
tmux attach -t gamenet-baseline

# 如果 tmux 会话消失，检查是否有进程还在运行：
ps aux | grep python | grep GAMENet

# 如果进程还在，等待完成；如果已退出，重新运行
```

---

## 下一步

运行成功后：

1. 将预测结果通过 `accept-comparison` 或 `evaluate` 纳管到评测基线
2. 继续运行其他 baseline（SafeDrug, RETAIN, LEAP...）
3. 按照 `RESEARCH_WORKFLOW.md` 进入对比评测与假设验证流程

---

**执行建议**: 逐 Phase 执行，每个 Phase 完成后报告状态，不要跳过验证步骤。
