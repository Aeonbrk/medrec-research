# V0 Overengineered Code Archive

归档日期：2026-08-20

## 为什么归档

这些代码是为"未来可能的问题"设计的过早优化：
- Web 控制台（6,394 行）：还没用过
- H1/H2 审批门：为多人协作设计，但只有 1 人
- Execution Orchestrator：复杂的容错恢复，实际不需要
- ARIS 集成：等需要自动化时再接回来

## 归档内容

- `web/`：整个前端（React + Vite，35 个组件）
- `src_web/`：后端静态打包资产
- `backend/`：23 个过度设计的 Python 模块
- `tests/`：与归档模块直接对应的单元与集成测试

## 可复用的部分

如果将来需要，这些模块可以参考：
- `reproduction_contract.py`：研究契约的数据结构（可简化复用）
- `execution_orchestrator.py`：远程执行的编排逻辑
- `agent_team_bridge.py`：多智能体协作的早期设计

## 替代方案

- Web 控制台 → 命令行 + 简单的状态文件
- H1/H2 审批 → Git commit + 研究契约 JSON
- Execution Orchestrator → RemoteExecutor (SSH + tmux)
- ARIS 集成 → 将来用 team-composition-patterns 重新集成
