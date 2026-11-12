---
description: "首次导入初始化：问清模块分类 / 权威模式 / 门禁命令 / BP 边界，落盘配置并自检"
---

调用 Skill("project-setup", args="$ARGUMENTS") 执行首次导入初始化。

**作用**：把本工具链装进新项目后，问清只有你知道的四个决策（模块分类 / 权威模式 / 门禁命令 / Blueprint 边界），同步写入 `开发规范/架构.md`、`change/versions.json`、`开发规范/验证与门禁.md` 与项目主文件（`CLAUDE.md` / `AGENTS.md`），最后跑 `check-modules` 自检。

**用法**：
- `/setup` —— 走完整四问
- `/setup core,data,economy` —— 直接给定模块，跳过第一问
- `/setup --auto` —— 全部用推荐值，产物标【默认待确认】

**前置**：已按 `适配说明.md` 完成解包（`change/`、`spec/`、`knowledge/`、`模板/` 在项目根）。

新项目部署完工具链后**第一步**运行；改模块或调整 BP 边界后可重跑（幂等）。
