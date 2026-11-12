# `AI工具链/tools/` 可执行工具

> 本目录把"流程里最关键、最容易做错的几步"从**提示词约定**变成**可执行代码**。
> 没有它，`/workflow archive` 只是一份"请 AI 照做"的说明书；有它，合并是可测、可回滚的。

---

## spec_tool.py

三层真相源（`change/` → `spec/`）的确定性工具。仅依赖 Python 3，无第三方包。

| 子命令 | 作用 | 会改文件吗 |
|---|---|---|
| `validate` | 校验 `07-spec-delta.md` 与 `spec/{module}.md` 一致性（C1–C9） | 否 |
| `check-spec` | 只体检 spec 自身（C4 编号唯一 / C8 标题卫生） | 否 |
| `check-modules` | 校验模块分类四处一致：`架构.md §6` ↔ `versions.json` ↔ `change/` ↔ `knowledge/` | 否 |
| `merge` | 计算 delta → spec 合并结果；默认 dry-run | 加 `--apply` 才写 |
| `archive` | 归档事务：加锁 → 校验 → 合并 → 移文档 → 更新索引 | 加 `--apply` 才写 |

### 用法

```bash
# 归档前校验（不改文件）
python AI工具链/tools/spec_tool.py validate --module economy

# 模块分类一致性（改了模块表之后必跑）
python AI工具链/tools/spec_tool.py check-modules --module core

# spec 存量体检（编号唯一 / 标题卫生）
python AI工具链/tools/spec_tool.py check-spec --module economy

# 看合并结果（dry-run，强烈建议先看）
python AI工具链/tools/spec_tool.py merge --module economy --version v0.2.0 --subcategory purchase

# 正式归档（原子写 + 失败回滚 + 并发锁）
python AI工具链/tools/spec_tool.py archive --module economy \
    --version v0.2.0 --subcategory purchase \
    --description "商店购买与退款" --type minor --apply
```

项目根不在当前目录时加 `--root <path>`；目录不叫 `spec`/`change` 时加 `--spec-dir` / `--change-dir`。

### 退出码

| 码 | 含义 | 处理 |
|---|---|---|
| 0 | 通过 | 继续 |
| 1 | 校验失败 | 按输出的 C{n} 逐条修 delta，**不要**改 spec |
| 2 | 用法/环境错误 | 检查路径与参数 |
| 3 | 缺基线 / 锁冲突 | 见下 |

---

## 校验项（C1–C8）

| ID | 检查 | 级别 |
|---|---|---|
| C1 | delta 每个 `##` 标题必须是 `ADDED/MODIFIED/REMOVED R{n} — 标题` | error |
| C2 | `MODIFIED/REMOVED` 引用的 R{n} 在 spec 中存在 | error |
| C3 | `ADDED` 的 R{n} 不与现存冲突 | error |
| C4 | spec 内 R{n} 唯一 | error |
| C5 | 每条 `ADDED/MODIFIED` 至少一个 `### 场景:` | error |
| C6 | 每个场景含「当」与「则」 | error |
| C7 | 「则」不得只落在表现层（启发式） | warning |
| C8 | **spec 标题不得残留 `ADDED/MODIFIED/REMOVED` 前缀** | error |
| C9 | 模块分类四处一致（`架构.md §6` / `versions.json` / `change/` / `knowledge/`）；设计文档记录了「在途契约终检」 | error（分类）/ warning（契约记录） |

> **C8 是源包遗留缺陷的体检项**：原工具链的活规格里真实出现过 `## ADDED R2 — …` 这种脏标题，说明"追加时须剥离操作前缀"这条从未被明确规定。本工具在合并时直接剥离，并用 C8 存量体检。

---

## 合并规则（与旧提示词版本的差异）

| 项 | 旧（提示词） | 现在（工具） |
|---|---|---|
| ADDED 标题 | 原样追加 → 得到 `## ADDED R3` | **剥离前缀**，写为 `## R3 — 标题` |
| MODIFIED 标题 | "保留标题"（未说谁的） | `## R{n} — 新标题（MODIFIED vX.Y.Z）` |
| MODIFIED 边界 | 未定义 | 从 `## R{n}` 到下一个 `## ` 或 EOF |
| 版本戳 | "刷新"（未定义格式） | **双戳**：`> 由 change/… 生成（日期）`（人读，与历史产物一致）+ `> 最后归档 vX.Y.Z @ 日期`（机器可 grep）；已有 spec 缺机器戳时自动补插 |
| 重复执行 | 会重复写入 / C3 报错 | **幂等**：检测到已合并则跳过 |
| 中途失败 | 文档已移走、spec 未更新 | **先合并 → 后移动**，异常回滚 |
| 并发 | 两会话互相覆盖 | `change/.archive.lock`（30 分钟过期） |
| 编码 | 未考虑 BOM | `utf-8-sig` 读取；BOM 不再导致首条需求被跳过 |

---

## 缺基线（退出码 3）

首次归档且**既无 spec 基线也无 delta** 时，工具会拒绝而不是造一个"待回填"的假真相。两条路：

1. 产出 `_tmp/07-spec-delta.md`（推荐：能力即契约）
2. 人工按 `spec/_TEMPLATE.md` 回填 `spec/{module}.md` 后重试

---

## 锁

`change/.archive.lock`，内容含模块名、PID、时间。

- 存在且 **< 30 分钟** → 拒绝（退出码 3），说明另一个归档正在进行
- 存在且 **> 30 分钟** → 判定为残留，接管并警告

> 锁只防"同一项目内两个 archive 并发"，不防跨机器。多人协作时仍需口头/IM 协调。

---

## 与源包 `archive.json` 的对照（迁移留痕）

源包的归档定义是 **9 个 step（提示词步骤）**。逐条对照如下——**先承认遗漏，再说明有意偏离**。

### 已补齐的 3 处（源包有、我第一版漏了）

| # | 源包要求 | 第一版问题 | 现在 |
|---|---|---|---|
| 1 | step 4：优化迭代时**合并 version.json（追加版本记录）** | 整体覆盖子分类 `version.json`，**历史 versions 被清空** | 读旧文件 → 按 version 去重追加 → 保留 description |
| 2 | step 6：模块**首次**建 spec 时，在 `spec/README.md` 索引**追加一行** | 完全没做，索引永远为空 | `update_spec_index()` 自动追加 `| 模块 | 规格 | 基线来源 |` 行 |
| 3 | step 6：spec 头部版本戳 `最后归档 v{X.Y.Z} @ {date}` | 只有描述性一行，不可机器检索 | 同时写 `> 由 change/... 生成` 与 `> 最后归档 vX @ date` |

### 有意偏离的 4 处（并说明理由）

| # | 源包做法 | 本工具做法 | 理由 |
|---|---|---|---|
| 1 | step 4 先移文档 → step 5 再校验 | **先合并 spec → 再移动文档** | 见下方"源包矛盾"：先移会让 delta 离开 `_tmp`，校验形同虚设；且中途失败不可恢复 |
| 2 | 靠 `versions.json` 里 `status=wip` 自动发现迭代 | 要求显式 `--module` / `--subcategory` | 自治模式下"自动发现"容易归档错模块；显式参数可审计 |
| 3 | 无并发保护 | `change/.archive.lock` | 多会话并行会互相覆盖 |
| 4 | 无幂等 | 检测已合并则跳过 | 合并成功但移档失败时的重跑会卡在 C3 |

### 源包自身的 4 处矛盾（照抄会继承缺陷）

| # | 矛盾 | 影响 |
|---|---|---|
| 1 | 描述说"从 `_tmp/` **移入**子分类"（step 4），step 5 却检查"若 `_tmp/07-spec-delta.md` 存在"，step 7 又"清空 `_tmp`" | 若 step 4 真是移入，step 5 的校验**永不触发**；若不清空，step 7 无意义 |
| 2 | step 6 规定戳为 `最后归档 v{X} @ {date}`，但真实产物（`10-pixel-beads/规格/economy.md`）写的是 `由 change/... 生成（日期）` | 规格与实现不一致，双方各写一套 |
| 3 | `verify.json` 追加标题为 `## 阶段: {phase}`，`plan-reviewer.md` 要求 `## 需求审核 / ## 设计审核 / ## 计划审核` | agent 按哪种写取决于它先读到谁 |
| 4 | `status.json` 查 `knowledge/{module}/`（目录），`knowledge-set` 写 `knowledge/{module}.md`（文件） | 状态查询永远显示"未同步" |

> 本工具统一采用**真实产物**的约定（矛盾 #2 取产物格式），并同时写机器可读戳，两边都不丢。
> 矛盾 #1 的处理方式即"有意偏离"第 1 条；#3/#4 在各自文档中已统一为 `## {阶段}审核` 与 `knowledge/{module}.md`。

---

## 尚存的自动化缺口（诚实声明）

| 项 | 现状 |
|---|---|
| 跨机器并发 | 锁只在单机生效 |
| 进程被强杀（无法捕获异常） | 留 `.bak` / `.owbak`，靠幂等重跑恢复，非真事务 |
| `UPROPERTY` / 序列化字段改名丢数据 | UE 侧仅人工检查项 |
| C7 权威端判定 | 词表启发式，可能误报 |

---

## 自测

```bash
# 在任意沙盒目录造 spec 与 delta 后：
python spec_tool.py validate --module demo
python spec_tool.py merge --module demo --version v0.2.0 --subcategory s1   # dry-run 先看
```
