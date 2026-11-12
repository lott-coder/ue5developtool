---
name: project-setup
description: 首次导入本工具链时的项目初始化。询问并落盘项目特定配置（模块分类 / 权威模式 / 门禁命令 / Blueprint 边界），同步写入项目主文件（CLAUDE.md / AGENTS.md）、架构.md 与 change/versions.json，最后跑 check-modules 自检。可重复运行（幂等）。
user-invocable: true
allowed-tools: AskUserQuestion, Read, Edit, Write, Glob, Grep, Bash
version: 1.0.0
---

# Project Setup 技能（首次导入初始化）

把本工具链导入新项目后**运行一次**。它做三件事：

1. 问清**只有你知道**的四个决策（模块分类 / 权威模式 / 门禁命令 / BP 边界）
2. 把它落盘到该去的地方（`架构.md`、`change/versions.json`、`验证与门禁.md`、项目主文件）
3. 跑一次自检，告诉你还差什么

> 对应源包的 `/setup`，对象从"回复称呼"换成"项目上下文"——UE 项目里真正会导错的是这几处配置。

---

## 何时运行

- 新项目部署完本包之后的**第一步**
- `/setup` 时；或改模块 / 换权威模式 / 调整 BP 边界后重跑（幂等）

---

## 步骤 0 · 解析参数

| 参数 | 说明 |
|---|---|
| `/setup` | 走完整四问 |
| `/setup <a,b,c>` | 直接采用给定模块名，跳过第 1 问 |
| `--auto` | 全用推荐值，产物标 **【默认待确认】** |

---

## 步骤 1 · 探测宿主与主文件

| 项目情况 | 目标主文件 |
|---|---|
| 存在 `AGENTS.md` | `AGENTS.md` |
| 存在 `CLAUDE.md` | `CLAUDE.md` |
| 两者都在 | **两者都写**，保持一致 |
| 都不在 | 有 `.agents/` / `.zcode/` → 建 `AGENTS.md`；否则 `CLAUDE.md` |

同时确认：`开发规范/架构.md`、`change/versions.json`、`开发规范/验证与门禁.md`、`tools/spec_tool.py` 存在。缺任一 → 提示先按 `适配说明.md` 解包，**不要继续**。

---

## 步骤 2 · 四问（逐问，一次一个）

### 问 1 · 模块分类

> 「你项目的业务模块有哪些？按业务域切，不要按技术层。」

| 选项 | 内容 |
|---|---|
| A（推荐） | 默认 `core / data / economy / progression / ui / audio / _misc` |
| B | 自定义列表（用户填写） |
| C | AI 扫 `Source/` 后给 2–3 套方案再选 |

**判据**：能用一句话讲清"负责游戏的哪一块"才是模块；只能讲清"是个工具"的，放 `GameServices` 或 Utility。

### 问 2 · 权威模式

| 选项 | 含义 |
|---|---|
| A Standalone | 单机/离线；`HasAuthority()` 恒 true |
| B Dedicated Server | 联机；服务器权威 |
| C 暂不确定 | 先按 A 落盘，标【待定】 |

**不允许 Listen Server**（除非显式声明并接受 host 特权）——见 `架构.md §2`。

### 问 3 · 门禁命令

| 选项 | 内容 |
|---|---|
| A（推荐） | 默认：`Build.bat …` + `UnrealEditor-Cmd.exe … -ExecCmds="Automation RunTests Project; Quit" -nullrhi` |
| B | 自定义（用户填写，逐条替换 G1–G9） |
| C | 暂无 CI | 保留默认并标注「本地手动执行」 |

### 问 4 · Blueprint 边界（UE 特有）

> 「哪些 Blueprint 允许存在？各自只负责什么装配？」

| 选项 | 内容 |
|---|---|
| A（推荐） | 只有装配类（Widget / 关卡摆放 / 继承 C++ 基类的 Actor） |
| B | 用户给清单 |
| C | 暂不确定 | 先按 A 落盘，标【待定】 |

落盘位置：`架构.md §7` 的"允许放 BP"表。**业务规则进 BP = 阻断**。

---

## 步骤 3 · 同步配置

| # | 文件 | 改什么 |
|---|---|---|
| 1 | `开发规范/架构.md` | §6 模块表（保持 `\| \`module\` \| 范围 \|` 两列）；§2 权威模式；§7 BP 边界表 |
| 2 | `change/versions.json` | `modules` 列表 + `updatedAt` |
| 3 | `开发规范/验证与门禁.md` | §3 的 G1–G9 命令替换为实际命令 |

选 C 的第 2/4 问 → 在 `架构.md` 对应处加 `> TODO(待定): …`。

---

## 步骤 4 · 写入主文件「项目上下文」段（幂等）

```markdown
## 项目上下文（由 /setup 生成）

- **引擎**：UE {版本}
- **权威模式**：{Standalone / Dedicated}
- **模块**：GameCore / GameFramework / GameServices / GameUI / GamePlay
- **数据**：{USaveGame + SchemaVersion / 后端}
- **Blueprint 边界**：仅装配（清单见 `开发规范/架构.md §7`）
- **模块分类**：{a / b / c …}
- **门禁**：G1 编译 → `…`；G3 Automation → `…`
- **真相源**：`change/` → `spec/`（只读）→ `knowledge/`
- **本工作流入口**：`/workflow init|plan|verify|archive`
```

**规则**：已有同名段整段替换；双宿主两份保持一致；写项目文件、不写 AI 私有 memory。

---

## 步骤 5 · 自检

```bash
python tools/spec_tool.py check-modules --module <任一模块> --root .
```

| 结果 | 处理 |
|---|---|
| `[OK] 模块分类一致` | 继续 |
| `[FAIL] … 不一致` | 按提示改，重跑 |
| `[WARN] 已登记但尚未建目录` | 正常，首次 init 才建 |

---

## 步骤 6 · 输出下一步

```
✅ 导入配置完成
   模块：{…}  权威：{…}  BP 边界：{…}  门禁：{…}

下一步：
1. /workflow init patch <模块> <子分类>
2. /workflow plan --direct
3. archive 后才生成 spec/{模块}.md（此前为空是正常的）
```

---

## 注意

- **不替用户决定**：给推荐与理由，但必须由用户选；被跳过按推荐落盘并标【默认待确认】
- **不猜模块**：用户说"你看着办"时，先扫 `Source/` 给 2–3 套方案
- **不改代码**：只改配置与文档，不碰 `Source/`、`Content/`
- **可重复运行**：幂等覆盖
- **失败不静默**：写入失败要报出文件与原因，先备份 `.bak`
