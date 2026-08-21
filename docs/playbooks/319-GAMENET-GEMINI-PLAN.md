# 319-wild GAMENet Baseline 执行计划（Gemini 版本）

**交给 Gemini 执行的简化版本，已由 Claude 预先优化所有脚本**

---

## 🎯 目标

在 319-wild 上完成 GAMENet baseline 训练，获得可复现的结果

---

## 📦 前置条件

- 你有 319-lab SSH 访问权限
- MIMIC-III 数据已存在于服务器某处
- SafeDrug 代码仓库已克隆

---

## 🚀 执行步骤（逐步执行，每步完成后报告）

### Step 1: 上传脚本（本地 MacBook）

```bash
cd /Users/oian/Codes/master/medrec-research
scp baselines/scripts/*.sh 319-lab:/tmp/
```

**验证**: 
```bash
ssh 319-lab 'ls -lh /tmp/*.sh'
```
应该看到 3 个脚本。

---

### Step 2: 环境验证

```bash
ssh 319-lab
cd /tmp
bash verify_319_env.sh
```

**预期**: 所有检查显示 ✓

**如果失败**，根据错误信息：

- **PyTorch 失败** → 运行 `bash setup_pytorch_319.sh medrec-gamenet`
- **数据目录不存在** → 运行：
  ```bash
  sudo mkdir -p /data/medrec/mimic-iii
  sudo chown -R $USER:$USER /data/medrec
  ```
- **SafeDrug 不存在** → 运行：
  ```bash
  cd /root/zhb
  git clone https://github.com/ycq091044/SafeDrug.git
  ```

修复后重新运行 `verify_319_env.sh`，直到全部通过。

---

### Step 3: 检查 MIMIC-III 数据

```bash
ls -lh /data/medrec/mimic-iii/
```

**需要包含**:
- `PRESCRIPTIONS.csv` (或 .gz)
- `DIAGNOSES_ICD.csv` (或 .gz)
- `PROCEDURES_ICD.csv` (或 .gz)

**如果不存在**，检查是否在其他位置：
```bash
find /root/zhb -name "PRESCRIPTIONS.csv*" 2>/dev/null
```

**找到后创建软链接**：
```bash
# 假设数据在 /root/zhb/Search/dataset/mimic-iii-1.4
ln -s /root/zhb/Search/dataset/mimic-iii-1.4 /data/medrec/mimic-iii
```

**再次验证**：
```bash
ls -lh /data/medrec/mimic-iii/*.csv* | wc -l
# 应该输出 3
```

---

### Step 4: 选择空闲 GPU

```bash
nvidia-smi
```

**查看 GPU 利用率**，选择利用率 < 20% 的 GPU（假设是 GPU 0）。

设置环境变量：
```bash
export GPU_ID=0
```

---

### Step 5: 启动训练（在 tmux 中）

```bash
# 创建 tmux 会话（防止 SSH 断开）
tmux new -s gamenet-baseline

# 在 tmux 中运行训练
cd /tmp
bash run_gamenet_319.sh gamenet

# 训练期间可以 detach: Ctrl+B 然后按 D
# 重新连接: tmux attach -t gamenet-baseline
```

**预期时长**: 30-60 分钟

**监控进度**（另开一个 SSH 窗口）：
```bash
ssh 319-lab
tail -f /data/medrec/baselines/gamenet/run_*.log
```

---

### Step 6: 等待训练完成

**完成标志**：
- 日志显示 `✓ 训练完成`
- 输出 JSON 结果
- tmux 回到 shell 提示符

**如果中途失败**：
- 检查日志最后 50 行：`tail -50 /data/medrec/baselines/gamenet/run_*.log`
- 常见问题：
  - **OOM (内存不足)** → 选择另一个 GPU 或等待当前 GPU 空闲
  - **数据文件损坏** → 检查 MIMIC-III 文件完整性
  - **磁盘满** → 清理空间 `df -h /data/medrec`

---

### Step 7: 验证结果

```bash
cat /data/medrec/baselines/gamenet/result.json
```

**检查指标是否合理**（GAMENet 论文报告）：
- Jaccard: 0.507 ± 0.05
- PRAUC: 0.756 ± 0.05
- F1: 0.672 ± 0.05
- DDI Rate: 0.082 ± 0.02

**如果指标偏差 > 20% 或全为 0**，训练失败，需要检查日志。

---

### Step 8: 下载结果（本地 MacBook）

```bash
# 下载 JSON 结果
scp 319-lab:/data/medrec/baselines/gamenet/result.json \
  /Users/oian/Codes/master/medrec-research/research/baselines/gamenet/

# 下载日志（可选）
scp 319-lab:/data/medrec/baselines/gamenet/run_*.log \
  /Users/oian/Codes/master/medrec-research/research/baselines/gamenet/
```

---

### Step 9: 清理（可选）

```bash
ssh 319-lab

# 删除临时脚本
rm -f /tmp/*.sh

# 删除大的 checkpoint 文件（保留结果和日志）
cd /data/medrec/baselines/gamenet
rm -f *.pth *.pt
```

---

## ✅ 成功标准

- [ ] 环境验证全部通过
- [ ] 训练完成 50 epochs 无错误
- [ ] `result.json` 指标在合理范围内
- [ ] 结果已下载到本地
- [ ] tmux 会话已退出或清理

---

## 📋 报告格式

每完成一个 Step，报告：

```
Step X: [步骤名称]
状态: ✓ 成功 / ✗ 失败 / ⚠ 警告
输出: [关键输出摘要]
问题: [如果有]
耗时: [实际耗时]
```

最终报告：
```
=== GAMENet Baseline 训练完成 ===
指标:
  Jaccard: 0.XXX
  PRAUC: 0.XXX
  F1: 0.XXX
  DDI Rate: 0.XXX

与论文对比:
  [偏差分析]

总耗时: XX 分钟
```

---

## 🆘 紧急情况

**如果完全卡住**，提供以下信息给 Claude：
1. 当前 Step 编号
2. 错误日志最后 50 行
3. `nvidia-smi` 输出
4. `df -h /data/medrec` 输出
5. `conda list | grep torch` 输出

---

**开始执行吧！逐步进行，报告每一步的结果。**
