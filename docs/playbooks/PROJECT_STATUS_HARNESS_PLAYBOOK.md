# Project Status Harness Playbook

本 playbook 用于发布公开安全 Project Status Snapshot，并在 Mac Harness Terminal 查看阻塞项或生成 Action Request。它不运行实验。

## 1. 发布前确认 authority

确认 program、六个 audit、registry、Selection Result 与 Comparison Scope 来自预期版本。Comparison Scope 必须固定 protocol version、Dataset Manifest digest 和 Adaptation Budget digest。显式提供的 Human Review 若已漂移，CLI 退出 `2` 且不写状态文件。

运行 `status-publish`。输出通过临时文件和原子替换写入，stdout 返回 `snapshot_sha256`。相同 authority、scope 与注入时钟产生相同字节。生产 CLI 使用 UTC 当前时间，状态默认只有短 freshness 窗口。

## 2. 启动只读 harness

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research harness \
  --status /tmp/medrec-status.json \
  --port 0
```

服务固定绑定 `127.0.0.1`，stdout 给出实际 URL。CLI 不提供 `--host`、command、argv、environment、SSH 或 remote-path 输入。未提供 Authority Bundle 时动作接口关闭，页面仍可查看阶段、首要 blocker、下一步和公开 evidence links。

## 3. 启用动作请求

Action Authorization 与 Remote Preflight 必须由对应 authority 在仓库外产生，并组成严格、内容寻址的 Authority Bundle。启动时通过 `--authority-bundle` 显式注入。Bundle 必须绑定当前项目、status snapshot、Comparison Scope、动作、`319-wild` profile、immutable remote revision、issuer/source 与有效期。

Web 和 `action-evaluate` 调用同一个纯 `evaluate_action`。允许时只生成 Action Request；拒绝时写 Action Decision 并退出 `2`。两者都不调用 subprocess、shell、SSH、Conda、ARIS job submission 或任何远端接口。ARIS 是否执行该请求属于后续独立授权和 remote preflight 流程。

## 4. 恢复与失效

- 状态过期：重新校验 authority 后运行 `status-publish`，不要改时间戳或 digest。
- authority 漂移：重新发布 selection/status，并重新签发绑定新 digest 的 Authorization 和 Preflight。
- Human Review 失效：回到四候选 review gate；旧记录保留作 provenance，不得改写。
- 状态文件损坏或不可读：harness 返回固定公开安全错误并关闭动作；从 source-of-truth 重新发布。
- 端口占用：使用 `--port 0` 获取新的 loopback 端口。

恢复过程不得从 Web 写回 registry、audit、review、qualification 或实验记录。
