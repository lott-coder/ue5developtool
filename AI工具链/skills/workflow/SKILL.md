---
name: workflow
description: 引擎无关的编程工作流管理。默认 brainstorm 交互式流程（Phase 1=brainstorm-design、Phase 2=brainstorm-develop），--direct 快速写文档，--unattended 无人值守。覆盖规划（Phase 0–3）、执行（Phase 4）、沉淀（Phase 5）、审核、归档、活规格（spec/）维护。引擎层检查项见 开发规范/ 对应文档。
user-invocable: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(git *)
version: 1.0.0
---

# Workflow 工作流管理技能

> **移植说明**：本 SKILL 由 Roblox/Knit 版移植而来，**流程内核与引擎无关**。
> 引擎相关的检查项不在本文件里，而在：
> - 架构约束 → `开发规范/架构.md`
> - 编码规范 → `开发规范/编码约定.md`
> - 资源与依赖 → `开发规范/工程与资源.md`
> - **什么算证据** → `开发规范/验证与门禁.md`
> - 阶段细则 → `开发规范/工作流执行.md`
>
> 换引擎只换这几篇，**不改本文件的阶段与门禁**。

---

## 三种规划模式

| 模式 | Phase 1 | Phase 2 | 适用 |
|---|---|---|---|
| **默认（brainstorm）** | brainstorm-design 问答 → 分块展示 | brainstorm-develop 技术方案 | 新功能、需求/方案不明确 |
| **`--direct`** | 直接写 `01-requirements.md` | 直接写 `02-design.md` | 小改动、需求已明确 |
| **`--unattended`** | 自动生成（默认标准方案） | 自动生成（默认扩展现有模块） | 需求已明确、信任自动决策 |

三种模式的 Phase 0、Phase 3–5 一致（`--unattended` 审核自动决策、不自动归档）。

---

## 子命令

| 子命令 | 用途 |
|---|---|
| `init <type> [module] [subCategory]` | 初始化迭代（type = major/minor/patch） |
| `plan [--prd <路径>] [--direct] [--unattended] [--cron]` | 执行 Phase 0–3 |
| `archive [subCategory]` | 归档 + delta 合并进 `spec/` |
| `verify <phase>` | 手动触发审核（requirements/design/plan） |
| `validate` | 校验 `07-spec-delta.md` 格式与引用 |
| `spec-diff` | 渲染「本次 delta vs 当前 spec」对照（只读） |
| `status` | 查询当前状态 |

---

## 三层真相源（本工具链的核心）

```
spec/{module}.md        当前真相源 = 「系统现在必须是什么行为」(what)
                        只读；唯一更新入口 = /workflow archive 的 delta 合并
knowledge/{module}.md   「怎么做 / 踩过什么坑」(how)
                        随迭代更新，人可读可改
change/{module}/...     「这次改了什么 / 为什么」(what changed & why)
                        _tmp/ 进行中 → {subCategory}/ 归档后
```

**为什么必须分开**：
- 混在一起 → 文档越写越长，"现在到底该怎样"没人说得清
- 只有 `change/` → 每次都要读历史才能知道现状
- 只有 `spec/` → 不知道为何这么设计，容易重复踩坑

**硬规则**：`spec/` 禁止手改。绕过 delta 直接编辑 = 真相源被旁路污染，后续所有迭代建立在假前提上。

---

## 目录结构

```
change/
  {module}/                     ← 大分类（业务域）
    _tmp/                       ← 进行中的迭代（同时只允许一组）
      00-prd-analysis.md        ← Phase 0（可选）
      01-requirements.md
      02-design.md
      03-plan.md
      04-review-report.md
      05-issues.md
      06-knowledge-update.md
      07-spec-delta.md         ← Phase 2 产物（行为变更时必产）
    {subCategory}/             ← 归档后的迭代
      version.json
      01-requirements.md ...
    version.json               ← 模块级索引
  versions.json                ← 全局索引
spec/
  README.md
  {module}.md
knowledge/
  README.md
  {module}.md
```

**规则**：
- `_tmp/` 下文档**没有版本号子目录**，直接平铺
- 每个模块同一时间 `_tmp/` 只允许一组文档
- 无 `archive/` 目录；归档直接进大分类下的子分类目录
- 子分类名是功能的精准描述（如 `purchase`、`schema-migration`）

---

## 模块分类（**必须先改成你项目的业务域**）

UE5 模板默认：

| 模块 | 范围 |
|---|---|
| `core` | 启动、生命周期、领域基础类型 |
| `data` | 存档、schema 迁移、配置加载 |
| `economy` | 货币、价格、结算、账本 |
| `progression` | 经验、等级、解锁 |
| `ui` | 界面、HUD、弹窗 |
| `audio` | BGM/SFX |
| `_misc` | 无法归类 |

**init 时的模块推断**：未指定则按关键词推断（数据/存档/Profile→data；商店/购买/货币/结算→economy；等级/经验/解锁→progression；界面/HUD/UI→ui；音效/BGM→audio）。无法推断时**询问用户**，实在无法分类则 `_misc`。

> 模块名同时是 `knowledge/` 与 `change/` 的目录名，**必须与你的业务域一致**。事后改名会留下孤儿目录。

---

## 子命令详情

### 1. `/workflow init <type> [module] [subCategory]`

1. 读 `change/versions.json`
2. 解析 module（显式 > 关键词推断 > 询问 > `_misc`）
3. 解析 subCategory（显式 > 关键词推断 > 询问）
4. 检查 `_tmp/` 是否已有文件 → 有则提示先归档
5. 模块目录不存在则创建 `_tmp/`、`version.json`
6. 计算版本号（子分类维度递增；新子分类从 v0.0.1 起）
7. 从 `模板/` 复制 6 个文档到 `_tmp/`
8. 更新模块 `version.json`（`currentSubCategory`、`status=wip`）
9. 更新全局 `versions.json`
10. 回写工作计划 `docs/WorkPlan_*.md`（若存在）：`☐` → `◐`

**「优化迭代」判定**：若 subCategory 与已有子分类同名，复制该子分类最新文档到 `_tmp/` 作为起点。

---

### 2. `/workflow plan`

Phase 细则见 `开发规范/工作流执行.md`。要点：

#### Phase 0（可选）
`--prd` 提供时，调 `prd-reader` → `00-prd-analysis.md` → 自动进 Phase 1。
未提供则直接 Phase 1。

#### Phase 1 需求
默认 brainstorm-design：探索上下文 → **在途契约软检查** → 逐轮澄清（一次一问）→ 2–3 方案 → 分块确认 → 写 `01-requirements.md` → 审核 → 用户确认。

`--direct`：跳过问答，直接写文档，审核流程一致。

#### Phase 2 设计
默认 brainstorm-develop：深入代码 → 技术维度澄清 → 2–3 技术方案 → 分块确认 → 写 `02-design.md`（核心重点前置）→ **产出 `07-spec-delta.md`** → 在途契约终检 → 审核 → 用户确认。

> **delta 为什么在 Phase 2 而不是 Phase 1**：delta 描述的是**契约**（行为/数值/接口/事件），必须等设计定稿才写得准；Phase 1 写出来的是愿望。

#### Phase 3 计划
写 `03-plan.md`（任务清单、依赖、回滚、输出文件路径、层归属、需要的测试、资产修改清单）→ 审核（≤3 轮）→ 执行摘要 → 用户确认。

---

### 3. `/workflow archive [subCategory]`

1. 从 `version.json` 定位当前迭代，检查 `status=wip`
2. 确定归档目标子分类名
3. **归档前门控**：先跑 dry-run 看合并结果，再执行归档事务——**合并由工具确定性完成，禁止手工合并**
4. 执行归档事务（工具内部顺序：校验 → 合并 spec → 移动文档 → 更新索引 → 清空 `_tmp`）：

```bash
# ① 先看将合并成什么样（不写文件）
python AI工具链/tools/spec_tool.py merge --module {module} --version {vX.Y.Z} --subcategory {subCategory}

# ② 正式归档（原子写 + 失败回滚 + 并发锁 + 幂等）
python AI工具链/tools/spec_tool.py archive --module {module} --version {vX.Y.Z} \
    --subcategory {subCategory} --description "{描述}" --type {major|minor|patch} --apply
```

5. 工具保证的合并语义（详见 `tools/README.md`）：
   - `ADDED R{n}` → 写为 `## R{n} — 标题`（**剥离操作前缀**）
   - `MODIFIED R{n}` → 整段替换，标题带 `（MODIFIED v{X.Y.Z}）` 留痕
   - `REMOVED R{n}` → 删除
   - 子分类 `version.json` 的 `versions` **追加**（优化迭代保留历史，不覆盖）
   - 首次生成 spec 时自动在 `spec/README.md` 索引追加一行
   - 头部同时写描述性戳与 `最后归档 v{X.Y.Z} @ {date}`；旧 spec 留 `.bak`
6. 把**工具 stdout 原文**回给用户（含校验结论与归档路径），禁止只写"归档成功"
8. 回写工作计划：`◐` → `✓` + 归档路径 + 版本号

---

### 4. `/workflow validate [module]`

校验 `07-spec-delta.md` 与 `spec/{module}.md` 一致性。**由工具确定性执行，禁止人工目视替代**：

```bash
python AI工具链/tools/spec_tool.py validate --module {module}
```

8 项：

| ID | 检查 | 级别 |
|---|---|---|
| C1 | 每条目为 `ADDED/MODIFIED/REMOVED R{n} — 标题`，n 为正整数 | error |
| C2 | `MODIFIED/REMOVED` 引用的 `R{n}` 在 spec 中存在 | error |
| C3 | `ADDED` 的 `R{n}` 不与现存 ID 冲突 | error |
| C4 | spec 内 `R{n}` 唯一 | error |
| C5 | 每条 ADDED/MODIFIED 至少一个 `### 场景:` | error |
| C6 | 每个场景含「当…」与「则…」两段 | error |
| C7 | 场景的「则」落在**权威端**，不得只表述为表现层裁定 | warning |
| C8 | spec 标题不得残留 `ADDED/MODIFIED/REMOVED` 前缀（存量体检） | error |

> **C7 的引擎化**：Roblox 版要求"落服务端权威"；本版要求"落在 `开发规范/架构.md` 声明的权威端"——Dedicated=服务器（`HasAuthority()` 侧），Standalone=Gameplay 层唯一写入口。**规则精神不变：结果不能由表现层（UMG/蓝图）决定。**

失败 → 列出失败项 → 写 `05-issues.md` → **阻断 archive**。

---

### 5. `/workflow spec-diff [module]`

只读渲染：读 `_tmp/07-spec-delta.md` + `spec/{module}.md`，输出本次动了哪几条能力（ADDED/MODIFIED/REMOVED 各列 `R{n}` + 标题 + 摘要）。
**不产文件、不改状态**，供 Phase 3 确认前一眼看清变更范围。

---

### 6. `/workflow verify <phase>`

| phase | 审核文档 | 关联文档 |
|---|---|---|
| `requirements` | `01-requirements.md` | — |
| `design` | `02-design.md` | `01` |
| `plan` | `03-plan.md` | `01` + `02` |

调 `plan-reviewer` → 更新 `04-review-report.md`。

---

### 7. `/workflow status`

输出：当前版本号 + 子分类 + 模块、`_tmp` 文档完成度、各子分类概览、最近审核结果、知识库同步状态、`spec/` 基线状态。

---

## 在途契约对齐（多会话并行）

多会话并行开发不同模块时，`spec/` 只反映已归档状态，其它会话在途（`_tmp/`）的接口变更不可见 → 出现兼容性窗口。本机制在**决策点**强制读取所有在途契约。

| 时机 | 动作 | 结果 |
|---|---|---|
| **Phase 1（软检查）** | 读 `versions.json` 列出 `status=wip` 模块（排除自身），读各自 `_tmp/02-design.md` 与 `07-spec-delta.md`，形成「在途契约占位清单」 | 作为需求澄清输入，**不阻断** |
| **Phase 2（硬检查）** | 本模块契约定型后，逐项比对 C1–C5 | 冲突 → 记 `05-issues.md` 按**阻断**处理；0 冲突 → 在 `02-design.md` 头部记一行 |

**C1–C5 定义见 `开发规范/工作流执行.md` §Phase 2。**

**delta 立即入库**：终检 0 冲突后

```bash
git add change/{module}/_tmp/
git commit -m "docs({module}): {subCategory} v{X.Y.Z} 在途契约冻结"
```

- **只 add 本模块 `_tmp/`**，禁止 `git add -A` / `git add .`
- **不 push**
- 目的：让 git 历史成为并行会话的对齐媒介
- `--unattended` 例外：禁止 commit → 只做终检并在进度文件记「待 commit」

---

## 工作计划同步

项目可选维护 `docs/WorkPlan_*.md`（多版本取版本号最高者），按里程碑列出工作项，每项有 `module` + `subCategory` + `状态`。

| 标识 | 含义 |
|---|---|
| ☐ 未开始 | 默认 |
| ◐ 进行中 wip | 已 `init` |
| ✓ 已归档 | 已 `archive` |

**同步时机（强制）**：
- `init` 成功 → `☐` → `◐`
- `archive` 成功 → `◐` → `✓ 已归档 → change/{module}/{subCategory}/ v{X.Y.Z}`

**匹配键**：`module` + `subCategory`。未匹配则跳过并在 `05-issues.md` 记一条，不阻断。

---

## Phase 4：代码执行

1. 按 `03-plan.md` 执行，逐项更新状态
2. 问题记 `05-issues.md`
3. **先测试后实现**（Domain/Application 层）
4. 完成后调 `code-reviewer`
5. `AskUserQuestion` 展示 → 确认 → 整理报告
6. 修复 → 重跑门禁（`开发规范/验证与门禁.md` §3）
7. 通过 → Phase 5

**P4 硬要求**：
- 每个新增行为 ≥1 条 L1 Automation Test
- 改 `GameCore`/`GameFramework` → 跑 `Automation RunTests Project`
- 改 UMG/表现 → 留 L4 截图（必须在真实渲染下）
- 改存档结构 / `UPROPERTY` 名 → schema 往返测试 + Core Redirect 验证
- 涉及复制 → 双端验证
- 业务逻辑进 BP → 直接阻断

**若变更需要人眼验证**（手感/视觉/多分辨率），必须产出**验证用例表**：

| # | 用例名 | 前置条件 | 操作步骤 | 预期结果 | 证据 | 结果 |
|---|---|---|---|---|---|---|
| T1 | … | … | 1. … 2. … | … | 截图/录屏 | ☐ |

不得只写"验证通过"。

---

## Phase 5：知识沉淀

1. 分析影响面，确定涉及的 `knowledge/{module}.md`
2. `/knowledge-set <module>`（默认 dry-run）
3. 写 `06-knowledge-update.md`
4. 更新 `knowledge/README.md` 索引
5. 确认 delta 已产出 → `/workflow validate`
6. `/workflow archive` → delta 合并进 `spec/`
7. 回写工作计划

---

## Plan Mode 红线（汇总）

- 禁止跳过审核 / 禁止审核后直接进下一阶段 / 禁止批量询问
- 禁止先执行后补文档 / 禁止忽略阻断 / 禁止跳过归档
- 禁止行为变更无 delta 归档 / 禁止 validate 失败仍归档 / 禁止手改 `spec/`
- 禁止跳过验证证据（见 `验证与门禁.md` §2）
- 禁止自行假设

---

## 审核循环机制

```
产物完成 → plan-reviewer / code-reviewer
    ↓
写 04-review-report.md
    ↓
AskUserQuestion 展示摘要
    ├─ 确认通过 → 追加确认记录 → 下一阶段
    ├─ 修复后重审 → 修复 → 重审 → 再问
    └─ 讨论详情 → 澄清 → 更新报告 → 再问
```

**关键**：审核完成后禁止直接进入下一阶段；用户确认后必须把确认结论追加到 `04-review-report.md`。

---

## 文档模板

`模板/` 下有 7 个空模板（01–07）。`init` 时复制，填内容时保留标题结构——**结构是给审核 agent 的解析契约，改结构会让审核失效**。

---

## 版本管理格式

`change/versions.json`：

```json
{
  "modules": {
    "economy": {
      "currentSubCategory": null,
      "status": "idle",
      "subCategories": {}
    }
  }
}
```

`change/{module}/version.json`：

```json
{
  "module": "economy",
  "currentSubCategory": "purchase",
  "status": "wip",
  "subCategories": {
    "purchase": {
      "description": "商店购买与退款",
      "currentVersion": "v0.1.0",
      "status": "archived",
      "path": "change/economy/purchase"
    }
  }
}
```

版本递增：`major = v{X+1}.0.0`、`minor = v{x.Y+1}.0`、`patch = v{x.y.Z+1}`。

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.1.0 | 2026-11-12 | **归档与校验改为工具执行**（`AI工具链/tools/spec_tool.py`）：修复 ADDED 前缀污染 spec、MODIFIED 无变更留痕、中断后不可恢复、重跑非幂等、BOM 致首条需求被静默跳过；新增 C8 标题卫生与 `--dry-run`；归档顺序改为「先合并 spec → 再移动文档」，加并发锁与异常回滚。 |
| v1.0.0 | 2026-11-12 | 从 Roblox/Knit 版移植（UE5 宿主）：剥离引擎实现细节到 `开发规范/`；保留 Phase 0–5、门禁、严重度矩阵、delta/validate、三层真相源、在途契约对齐；C7 改为"落权威端（`HasAuthority()` 侧）"；验证从"Play F5 手动"升级为 L0–L4 分级证据；**新增 Blueprint 边界红线**（BP 只做装配）；明确 UE 自治模式默认仅对 `GameCore` 开放。 |
