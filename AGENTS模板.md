# 〈项目名〉— 工程纪律（AGENTS.md 工作区）

> **用法**：复制本文件到项目根并改名为 `AGENTS.md`，填掉所有 `〈…〉`。
> 适用宿主：DSH、ZCode 等「只靠 `AGENTS.md` 自动加载」的助手；Claude Code 项目无需本文件（它直接加载 `.claude/rules/`）。
> **本文件是 AI 每天看到的规范浓缩版**——它与 `docs/rules/` 必须自洽；冲突时以 `docs/rules/` 为准，并回头修本文件。

---

## 项目上下文

- **引擎**：Unreal Engine 〈5.4 / 5.5〉
- **语言/框架**：C++（四模块：`GameCore` / `GameFramework` / `GameServices` / `GameUI`+`GamePlay`）+ 原生 Gameplay Framework
- **权威模式**：〈Standalone / Dedicated Server〉（见 `docs/rules/架构.md §2`）；**不允许 Listen Server**
- **数据**：〈`USaveGame` + `SchemaVersion` / 后端〉；**载入失败必须显性失败，禁止默认值开局**
- **Blueprint 边界**：**只做装配**（清单见 `docs/rules/架构.md §7`）；业务规则进 BP = 阻断
- **模块**：〈core / data / economy / progression / ui / audio / _misc〉
- **门禁**：G1 编译 → `Build.bat <Target> Win64 Development -Project="<p>.uproject"`；G3 Automation → `UnrealEditor-Cmd.exe "<p>.uproject" -ExecCmds="Automation RunTests Project; Quit" -nullrhi -unattended`（完整 G1–G9 见 `docs/rules/验证与门禁.md §3`）
- **真相源**：`change/`（这次改了什么）→ `spec/`（现在必须怎样，**只读**）→ `knowledge/`（怎么做/踩过什么坑）

---

## 规范索引（按需查阅，不要全量读入）

| 主题 | 文件 |
|---|---|
| 四模块 / 权威 / 复制 / 数据 / BP 边界 | `docs/rules/架构.md` |
| C++ 命名、反射宏、Tick 纪律、禁用 API | `docs/rules/编码约定.md` |
| Build.cs 依赖、资产引用、重定向器、UPM 替代 | `docs/rules/工程与资源.md` |
| 证据等级 / 质量分级 / 数值门禁 / UI 验收 | `docs/rules/验证与门禁.md` |
| 阶段门禁与红线 | `docs/rules/工作流执行.md` |
| 无人值守边界（默认仅 `GameCore`） | `docs/rules/无人值守安全.md` |
| 人机协作纪律 | `docs/rules/AI协作纪律.md` |
| 多会话独占资源 | `docs/rules/多会话与独占资源.md` |
| 批量删改 | `docs/rules/代码清理.md` |
| 上下文预算 | `docs/rules/上下文效率.md` |
| 技能/代理怎么用 | `docs/rules/技能与代理使用.md` |

> 每篇末行有 `<!-- 已读到文末: X -->`。声称"符合某规范"却报不出该标记 → 按"未读"处理。

---

## 技能索引（8 个，用 skill 工具按名加载）

| 技能 | 何时用 |
|---|---|
| `workflow` | 走完整迭代（init / plan / verify / validate / archive / status） |
| `project-setup` | 首次导入配置、改模块/权威/BP 边界 |
| `brainstorm-design` | 需求模糊，先澄清 |
| `brainstorm-develop` | 需求明确，定技术方案 |
| `knowledge-get` | 查某模块现状（spec + knowledge） |
| `knowledge-set` | 沉淀踩坑与设计理由 |
| `systematic-debugging` | Bug 难复现 |
| `verification-before-completion` | 准备说"完成/修好"之前 |

---

## 命令别名（DSH 的 `/` 菜单不含这些，按本表转成技能调用）

| 用户说 | 动作 |
|---|---|
| `/workflow init <type> <module> <sub>` | 加载 `workflow`，args=`init …` |
| `/workflow plan [--prd <p>] [--direct] [--unattended]` | 加载 `workflow`，args=`plan …` |
| `/workflow verify <phase>` / `validate` / `status` | 同上 |
| `/workflow archive [sub]` | 同上 |
| `/setup` | 加载 `project-setup` |
| `/brainstorm-design <主题>` | 加载 `brainstorm-design` |
| `/brainstorm-develop <需求>` | 加载 `brainstorm-develop` |

---

## 子代理（`agents/*.md` 不是可加载单元，按需 Read 后拼进 prompt）

| 文件 | 角色 | 何时派 |
|---|---|---|
| `agents/prd-reader.md` | 读 PRD（图/PDF）转结构化需求 | Phase 0 |
| `agents/plan-reviewer.md` | 独立审需求/设计/计划 | Phase 1–3 后 |
| `agents/code-reviewer.md` | 独立审 C++ 变更（**不看 BP**） | Phase 4 后 |
| `agents/ue5-systems-engineer.md` | 模块落位/复制/可测性/BP 边界 | Phase 2（可选） |
| `agents/experience-designer.md` | 留存/变现/体验评审 | Phase 1（可选） |

调用方式：`subagent({ description, prompt: "<该文件正文>\n\n---\n任务: …\n文档: …" })`。
**审阅类 agent 的结论必须落盘**（`change/{module}/_tmp/04-review-report.md`）；BP 改动它审不了，会明确说"需人工 M2 检查"。

---

## 关键红线（UE5）

- ❌ `UObject*` 成员缺 `UPROPERTY()`（GC 悬空）
- ❌ `new` / `delete` 管理 `UObject`
- ❌ Server RPC 缺 `WithValidation` / `HasAuthority()` 守卫
- ❌ `UPROPERTY` 改名无 Core Redirect（静默丢数据）
- ❌ 业务规则写进 Blueprint
- ❌ `Tick` 内查找/分配/同步加载
- ❌ 写死 `TEXT("/Game/...")` 路径
- ❌ 改测试以通过门禁
- ❌ 未拿到新鲜证据就说"完成"

---

## 工作流速查

```
/workflow init patch <模块> <子分类>   → 建迭代
/workflow plan [--direct]               → Phase 0–3
/workflow verify <phase>                → 单独触发审核
/workflow validate                      → 归档前校验（C1–C9）
/workflow archive <子分类>              → 归档 + delta 合并进 spec/
```

**硬规则**：每阶段「产物 → 独立 agent 审核 → 用户确认」三拍，缺一不可进下一阶段；`spec/` 禁止手改。

---

## 真相源与工具

- `change/{module}/_tmp/` 进行中 → `change/{module}/{sub}/` 已归档
- `spec/{module}.md` 只读；`knowledge/{module}.md` 可写
- 归档与校验由工具执行，**不要手工合并**：

```bash
python tools/spec_tool.py validate --module <m>
python tools/spec_tool.py archive --module <m> --version vX.Y.Z --subcategory <s> --apply
python tools/spec_tool.py check-modules --module <m>
```

`spec/` 初始为空是正常的——第一轮 `archive` 后才会生成基线。
