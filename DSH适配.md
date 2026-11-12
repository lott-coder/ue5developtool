# DSH 适配（DeepSeek Harness）

> 适用：DSH 桌面版 / Web 版。本文只讲**与 Claude Code、ZCode 不同的地方**；通用落位见 [适配说明.md](适配说明.md)。
> 事实依据：本机安装版本的包文档（`dsh-agent-instructions`、`dsh-skill-filesystem`、`dsh-client-ui-commands`），非推断。

---

## 0. 一句话结论

**大部分能用，两处要改写法**：

| 内容 | DSH 下 |
|---|---|
| `开发规范/` 11 篇 | ✅ 换成项目根 `AGENTS.md`（自动加载） |
| `AI工具链/skills/` 8 个 | ✅ 放到 `.dsh/skills/`（自动发现） |
| `AI工具链/tools/` | ✅ 不变（Python 直接跑，`pwsh` 调用） |
| `change/ spec/ knowledge/ 模板/` | ✅ 项目根不变 |
| `AI工具链/agents/` 5 个 | ⚠️ **无自动发现** → 作为 prompt 模板，调 `subagent` 时喂给它 |
| `AI工具链/commands/` 4 个 | ❌ **无文件命令机制** → 改为 `AGENTS.md` 的命令别名表 |

---

## 1. DSH 的三个机制（已核）

### 1.1 项目指令：`AGENTS.md` 自动加载

- 从**项目根到当前工作目录**逐级加载候选文件：`AGENTS.md`、`CLAUDE.md`（另有 `AGENTS.local.md`、`CLAUDE.local.md` 覆盖层）
- 项目根标记默认是 `.git`
- 内容重复的文件会合并渲染，不会重复占预算
- 每条指令链有 **64KB** 字节预算，超出时先丢宽泛的文件、保留最具体的

→ **含义**：把规范浓缩版写成项目根 `AGENTS.md` 就够，不需要任何插件。

### 1.2 技能：`.dsh/skills` 自动发现

技能根（优先级从高到低）：

| 优先级 | 位置 |
|---|---|
| 100 | `<项目根>/.dsh/skills` |
| 200 | `<项目根>/.agents/skills` |
| 300 | `customSkillDirs`（配置项） |
| 400 | `~/.dsh/skills` |
| 500 | `~/.agents/skills` |

**发现规则（最容易踩的一条）**：
- 只扫根目录的**直接子项**：目录 bundle `<name>/SKILL.md` 或平铺文件 `<name>.md`
- **嵌套的 `**/SKILL.md` 不会被发现**——多套一层目录，技能就消失

**frontmatter**：
- 必填 `name`（**kebab-case**）与 `description`
- 可选 `whenToUse`、`metadata`、`disable-model-invocation`、`user-invocable`
- `allowed-tools`、`version` 是 Claude Code 字段，DSH 不识别（一般被忽略）

→ **含义**：把 8 个技能目录**直接**放进 `.dsh/skills/`，不要再套一层 `skills/`。

### 1.3 斜杠命令与子代理

- **斜杠命令由插件注册**（`ctx.commandUi` / host command），**不是从文件读的**。所以 `commands/*.md` 放到哪个目录都不会变成 `/workflow`。
- **子代理**是工具调用（`subagent` / `subagent_fork`），角色完全由 prompt 决定，没有"agent 定义文件"的加载机制。

→ **含义**：`commands/` 与 `agents/` 必须改成"别名表 + prompt 模板"的用法（见 §3）。

---

## 2. 落位步骤（5 步）

### 步骤 1 · 解包到项目根

同 [适配说明.md](适配说明.md) §0：`change/ spec/ knowledge/ 模板/` 必须在项目根。

### 步骤 2 · 装技能

```bash
# 正确：8 个技能目录直接放在技能根下
MyUEProject/
└─ .dsh/
   └─ skills/
      ├─ workflow/SKILL.md
      ├─ brainstorm-design/SKILL.md
      ├─ brainstorm-develop/SKILL.md
      ├─ knowledge-get/SKILL.md
      ├─ knowledge-set/SKILL.md
      ├─ project-setup/SKILL.md
      ├─ systematic-debugging/SKILL.md
      └─ verification-before-completion/SKILL.md
```

```bash
# 错误：多套了一层，任何技能都不会被发现
.dsh/skills/AI工具链/skills/workflow/SKILL.md
.dsh/skills/skills/workflow/SKILL.md
```

> 也可以用 `.agents/skills/`（优先级 200），但**同一技能不要在两个根都放**，否则可能出重复项。

### 步骤 3 · 写项目指令

把 [AGENTS模板.md](AGENTS模板.md) 复制为项目根 **`AGENTS.md`**，填掉 `〈…〉` 占位。

> 若项目已有 `CLAUDE.md` 且内容相同，DSH 会去重，不必删。

### 步骤 4 · 让子代理可用

`agents/*.md` 不自动加载。用法：调 `subagent` 时把该文件的正文作为角色说明。

```
subagent({
  description: "需求审核",
  prompt: "<把 agents/plan-reviewer.md 的正文粘在这里>\n\n---\n审核类型: requirements\n文档: change/economy/_tmp/01-requirements.md"
})
```

**建议**：在 `AGENTS.md` 的「子代理」一节列出 5 个文件与用途，让 agent 自己按需 Read 后拼 prompt（比每次手粘省事）。

### 步骤 5 · 命令降级为别名

`commands/*.md` 不生效。在 `AGENTS.md` 写一张别名表：

| 用户说 | 实际动作 |
|---|---|
| `/workflow init <type> <module> <sub>` | 加载 skill `workflow`，args = `init <type> <module> <sub>` |
| `/workflow plan [--direct\|--unattended]` | 加载 skill `workflow`，args = `plan …` |
| `/workflow archive …` / `verify …` / `validate` | 同上 |
| `/setup` | 加载 skill `project-setup` |
| `/brainstorm-design <主题>` | 加载 skill `brainstorm-design` |
| `/brainstorm-develop <需求>` | 加载 skill `brainstorm-develop` |

> DSH 的 `/` 菜单只显示插件注册的命令；上面这些是**约定**，靠 `AGENTS.md` 让 agent 认得并转成 skill 调用。

---

## 3. 技能 frontmatter 检查表

| 字段 | DSH 行为 | 本包现状 |
|---|---|---|
| `name` | 必填、kebab-case，否则**整条技能被丢弃并告警** | ✅ 8 个均合规（`workflow`、`brainstorm-design`…） |
| `description` | 必填 | ✅ |
| `user-invocable` | 控制是否出现在人可见入口 | ⚠️ 是否映射成 `/` 菜单项**未验证**（见 §6） |
| `allowed-tools` | 不识别（Claude Code 字段） | 保留无害；若技能被跳过，先删掉它 |
| `version` | 不识别 | 同上 |

**排障顺序**：技能没出现 → ① 检查是否多套了一层目录 ② 检查 `name` 是否 kebab-case ③ 临时删掉 `allowed-tools`/`version` 再试。

---

## 4. 自检

| 检查 | 怎么做 | 期望 |
|---|---|---|
| 技能被发现 | 让 agent「列出你当前可用的技能」 | 含 `workflow`、`project-setup`、`verification-before-completion` |
| 指令已加载 | 问「本项目的门禁命令是什么？」 | 能答出 G1/G3 的具体命令（来自 `AGENTS.md`） |
| 规范可追溯 | 问「分层约束写在哪篇？」 | 指向 `docs/rules/架构.md` 或 `.claude/rules/架构.md` |
| 工具可跑 | `python tools/spec_tool.py check-modules --module <m> --root .` | `[OK] 模块分类一致` |

---

## 5. 与 ZCode 的差异速查

| 维度 | ZCode | DSH |
|---|---|---|
| 指令文件 | 只认 `AGENTS.md` | `AGENTS.md` **和** `CLAUDE.md`（含 `.local.md` 覆盖层） |
| 技能根 | `.agents/skills` | **`.dsh/skills` 优先**，`.agents/skills` 次之 |
| 技能嵌套 | 未明确限制 | **不发现 `**/SKILL.md`** |
| 子代理定义 | `.zcode/agents/`（可加载） | 无文件机制，靠 prompt |
| 命令 | `.agents/commands/` | 插件注册，无文件机制 |

---

## 6. 未验证项（不猜）

| 项 | 状态 |
|---|---|
| `user-invocable: true` 的技能是否出现在 `/` 菜单 | **未验证**。`dsh-skill-filesystem` 只说明该字段控制"human-facing commands"面，`/` 菜单条目由 `dsh-client-ui-commands` 的插件注册决定。需实测一次 |
| `AGENTS.local.md` 覆盖层的实际优先级效果 | 文档说明存在，**未实测** |
| 多个技能根同名技能的合并规则 | 文档给出 rank 顺序，**未实测冲突时谁赢** |

> 这三项我会在真机上验证后再补结论；在此之前按本文的保守写法执行。

<!-- 已读到文末: DSH适配 -->
