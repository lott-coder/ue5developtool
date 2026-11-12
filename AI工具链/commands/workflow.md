---
description: "编程工作流管理（默认 brainstorm，--direct 快速，--unattended 无人值守；init/plan/archive/verify/validate/status）"
---

调用 Skill("workflow", args="$ARGUMENTS") 执行编程工作流管理。

**模式**：默认走 brainstorm 交互式流程（Phase 1=brainstorm-design、Phase 2=brainstorm-develop）；`/workflow plan --direct` 直接写文档；`/workflow plan --unattended` 自动决策（安全边界见 `开发规范/无人值守安全.md`）。

**引擎**：UE5（C++，Blueprint 仅装配）。引擎层检查项不在本命令内，见 `开发规范/`：
- 架构约束（含 BP 边界）→ `架构.md`
- 编码规范 → `编码约定.md`
- 模块与资源 → `工程与资源.md`
- 什么算证据 → `验证与门禁.md`
