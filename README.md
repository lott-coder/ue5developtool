# UE5 AI 开发工具链（conservative v0.1）

> 从一套已在 Roblox 生产项目上跑通的 AI 辅助开发方法论移植而来，**保留流程治理内核，重写引擎实现层**。
> 适配目标：Unreal Engine 5.4+（C++ 为主，Blueprint 仅装配）。
> **保守原则**：只收录基于引擎原生能力、已验证可行的做法；不确定的一律标注【暂不采用】并写明理由，而不是省略。

---

## 这个包是什么 / 不是什么

| 是 | 不是 |
|---|---|
| 一套**文档驱动 + 门禁控制**的 AI 开发流程 | 一个 UE 插件/框架 |
| 三层真相源（spec / knowledge / change） | 代码脚手架（不含任何 `.h`/`.cpp`） |
| 可被机器执行的验收口径 | 自动生成游戏的工具 |
| 引擎架构的**保守约束集**（含 Blueprint 边界） | 完整架构方案（会随项目长大） |

**核心主张**：AI 写代码不是瓶颈，**"AI 说完成但其实没完成"才是瓶颈**。本包的全部设计都指向一件事——让"完成"变成可验证的事实。

---

## 三层结构

```
UE5/ue5developtool/
├─ AI工具链/          流程执行器（skills / commands / agents / **tools 可执行工具**）
├─ 开发规范/          引擎架构与验收口径（本包唯一的"真理"来源）
├─ 模板/              7 个迭代文档模板
├─ change/            变更档案（这次改了什么）
├─ spec/              活规格（现在必须是什么行为）★ 只读
├─ knowledge/         项目知识（怎么做/踩过什么坑）
├─ README.md
└─ 快速启动.md
```

### 三层真相源的关系

```
   change/{module}/_tmp/        一次迭代的完整思考过程
          │  /workflow archive（校验 + 合并）
          ▼
   spec/{module}.md             当前契约（what）——禁止手改
          │  实现时查阅
          ▼
   knowledge/{module}.md        实现原理与坑（how）——可读写
```

**为什么必须分开**：混在一起会让"现在到底该怎样"没人说得清；只有 `change/` 则每次都要读历史才知道现状；只有 `spec/` 则不知道为什么这么设计，会重复踩坑。

---

## 流程：六阶段 + 三拍门禁

```
Phase 0  PRD 解析（可选）
Phase 1  需求  ──┐
Phase 2  设计  ──┤  每阶段：产物文档 → 独立 agent 审核 → 用户确认
Phase 3  计划  ──┘            ↑ 缺一不可进下一阶段
Phase 4  编码 + code-reviewer + 门禁（编译/Automation/模块依赖/硬编码路径）
Phase 5  知识沉淀 → archive（delta 合并进 spec/）
```

三种模式：**brainstorm**（交互，默认）/ `--direct`（快速）/ `--unattended`（自治，**默认仅对 `GameCore` 开放**）。

---

## 保守版架构（一句话版）

| 维度 | 选择 | 为何保守 |
|---|---|---|
| 分层 | 四模块（GameCore/GameFramework/GameServices/GameUI+GamePlay）+ **原生 Gameplay Framework** | 不造平行 Service 层，避免双权威源 |
| 权威 | Standalone / Dedicated 二选一，声明制；用原生 `HasAuthority()` | 排除 Listen Server（host 特权）、预测回滚、Iris/Replication Graph |
| 通信 | 原生 RPC + `Replicated` 属性；RPC 只做薄入口 | 每条自建通道都增加"状态在哪"的搜索空间 |
| 数据 | `USaveGame`（单机）/ 后端（联机，二期） | 明确"联机时 `USaveGame` 不可作权威存档" |
| 能力系统 | Gameplay Framework + C++ | **GAS 暂不引入**（首版），有技能/buff 复杂度需求再上 |
| 验证 | 纯 C++ Automation Test 为主 | 把逻辑挤出 `UWorld`，用最便宜的方式覆盖最多行为 |
| Blueprint | **只做装配** | 不可 diff → 不可审查 → 不可进 spec |

完整版含**"暂不采用"清单与理由**，见 [开发规范/架构.md](开发规范/架构.md) §9。

---

## 与 Roblox 原版的三个关键差异

| 原版（Roblox） | 本版（UE5） | 为什么 |
|---|---|---|
| 服务端权威是**平台强制** | **原生 `HasAuthority()`**（Standalone 下恒 true） | 同构度最高；单机与联机同一套代码 ← **比 Unity 迁移更顺的地方** |
| 无单测框架 → Play F5 手动用例表 | L0–L4 分级证据 + Automation Test | UE 有测试框架，照搬手动 = 浪费 |
| 改实例名必须同步 Studio（字符串引用） | 该铁律失效；改为防 `UPROPERTY` 改名丢数据、重定向器堆积、写死 `/Game/` 路径 | UE 用包内引用，但故障面换了形状 |

**新增的一条铁律**（原版没有）：**Blueprint 边界**。BP 是最容易背离这套方法论的地方——它不可 diff、不可审查、不可被 agent 可靠读写。因此逻辑必须下沉 C++。

---

## 部署到项目

**唯一入口是 [适配说明.md](适配说明.md)**（复制映射 / 必须改的三处 / 推荐顺序 / 自检清单）。这里只给两条硬约束：

1. **不放进 `Content/`**——避免被引擎导入、进包体
2. **`change/ spec/ knowledge/ 模板/` 必须解包到项目根**，不能把整个工具包当文件夹放在旁边

```
MyUEProject/                 ← 项目根（内容解包到这里）
├─ Source/  Content/  Config/    ← UE 工程
├─ .claude/{rules,skills,agents,commands}/
├─ tools/
├─ change/  spec/  knowledge/  模板/
```

装好后第一步跑 `/setup`：它会问清模块分类、权威模式、门禁命令与 **Blueprint 边界**，落盘并自检。

**宿主差异**：Claude Code / ZCode 见 `适配说明.md`；**DSH（DeepSeek Harness）见 [DSH适配.md](DSH适配.md)**——技能根是 `.dsh/skills`，`agents/` 与 `commands/` 没有文件加载机制，需改成 prompt 模板与别名表。`AGENTS模板.md` 可直接复制为项目根 `AGENTS.md`（DSH / ZCode 通用）。

---

## 第一步

1. 读 [快速启动.md](快速启动.md)（约 25 分钟）
2. 改 `开发规范/架构.md` §6 的**模块分类表** + `change/versions.json` 为你的业务域
3. 改 `开发规范/架构.md` §2 的**权威模式**（Standalone or Dedicated）
4. 定 **Blueprint 边界**（哪些 BP 允许存在、各自只负责什么装配）
5. 初始化一个模块跑通全流程：`/workflow init minor data save-baseline`

---

## 版本

| 版本 | 日期 | 内容 |
|---|---|---|
| v0.3.0 | 2026-11-12 | **对照原版全量审查后的修复**：补 `AI协作纪律`、`多会话与独占资源` 两篇规范（共 11 篇）；新增领域专家 `ue5-systems-engineer` 与 `experience-designer` 两个 agent；《验证与门禁》重写（P0–P3 分级 + 数值门禁 + G1–G9）；《无人值守安全》补调度器（Phase 判定/边界/可修复范围/`--cron`/完成报告，并明确自治仅对 `GameCore` 开放）；模板补动作动词、收尾三件事、确认不修段；`spec_tool.py` 新增 `check-modules`（C9）。 |
| v0.2.0 | 2026-11-12 | **归档与校验工具化**：新增 `AI工具链/tools/spec_tool.py`（validate / merge / archive，含原子写、失败回滚、并发锁、幂等、BOM 容忍）；修复 ADDED 前缀污染 spec 等 5 处缺陷；补 `代码清理`、`上下文效率`、`技能与代理使用` 三篇规范（共 9 篇）。 |
| v0.1.0 | 2026-11-12 | 从 Roblox/Knit 工具链移植：流程治理 + 三层真相源完整迁移；架构方法论取保守子集（原生 Gameplay Framework + `HasAuthority()`）；新增 Blueprint 边界红线与"UE 自治模式仅开放 GameCore"约束；验证升级为 L0–L4 分级证据。 |

**迁移留痕**：原版中被**刻意剔除**的内容——Rojo/Wally、Knit/Trove/ProfileService 实现、Play F5 手动验证门禁、实例名双侧同步铁律、PerfKit、ExcelToLuau 活表管线、mcp-lock、**GAS**、**Gauntlet**、**Listen Server**。剔除理由见 [开发规范/架构.md](开发规范/架构.md) §9 与各规范文档的"暂不采用"表。
