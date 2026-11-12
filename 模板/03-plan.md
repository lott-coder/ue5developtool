# 执行计划 - v{X.Y.Z}

> 模块: {module}
> 子分类: {subCategory}
> 日期: YYYY-MM-DD

## 1. 任务清单

> 每项必须标注：输出文件 / 模块 / 需要的测试 / 是否涉及资产。

| # | 任务 | 输出文件 | 模块 | 测试 | 资产 | 依赖 | 状态 |
|---|------|---------|------|------|------|------|------|
| 1 | 定义价格规则 | `Source/GameCore/Private/Economy/PriceRule.cpp` | GameCore | L1 | — | — | ☐ |
| 2 | 实现结算子系统 | `Source/GameFramework/Private/Economy/EconomySubsystem.cpp` | GameFramework | L1 | — | 1 | ☐ |
| 3 | 存档字段与迁移 | `Source/GameServices/Private/Save/GameSaveGame.h` | GameServices | L1 | — | 1 | ☐ |
| 4 | 商店界面绑定 | `Source/GameUI/Private/Shop/ShopPanelWidget.cpp` | GameUI | L2/L4 | WBP | 2 | ☐ |

**状态**：☐ 未开始 / ◐ 进行中 / ✓ 完成 / ✗ 受阻

## 2. 资产修改清单（需在编辑器内手工完成 / 由人确认）

> 这部分 **AI 不得直接改**（`.uasset`/`.umap` 不可 diff），只能给步骤。

| # | 类型 | 资产路径 | 操作 | 验收方式 |
|---|------|---------|------|---------|
| A1 | DataAsset | `Content/Data/Economy/DA_EconomyConfig` | 新增 `PriceTable` 并填值 | Data Validation 通过 |
| A2 | Widget Blueprint | `Content/UI/Shop/WBP_ShopPanel` | 绑按钮事件、绑数值显示 | 运行时点击有效 |
| A3 | Level | `Content/Maps/L_Shop` | 放置商店 Actor | PIE 可见 |
| A4 | Core Redirect | `Config/DefaultEngine.ini` | `UPROPERTY` 改名映射 | 老存档可读 |

## 3. 依赖关系

```
1 → 2 → 4
1 → 3
```

## 4. 验证计划

| 阶段 | 动作 | 通过标准 |
|---|---|---|
| 每完成 1 项 | 编译 + 相关 L1 测试 | 0 error，测试绿 |
| 全部完成 | `Automation RunTests Project` | 全绿 |
| 涉及表现 | L2/L4 + 截图 | 无报错、界面符合预期 |
| 涉及复制 | 双端验证 | 客户端表现与服务器一致 |
| 归档前 | 门禁 G1–G9（见 `开发规范/验证与门禁.md` §3） | 全通过 |

**命令参考**：

```
Build.bat <Project>Editor Win64 Development -Project="<path>.uproject"
UnrealEditor-Cmd.exe "<path>.uproject" -ExecCmds="Automation RunTests Project; Quit" -nullrhi -unattended -ReportExportPath="<dir>"
```

## 5. 验收标准对照

| AC | 覆盖任务 | 证据 | 状态 |
|---|---|---|---|
| AC-1 | 2, 4 | L1 `Economy.Buy_Succeeds` | ☐ |

## 6. 回滚方案

- 代码：`git revert <commit>` 或丢弃工作区改动
- 存档：升级 `SchemaVersion` 后保留旧版读取能力至少一个版本周期
- `UPROPERTY` 改名：保留 Core Redirect 至少两个版本再清理
- 资产：Editor 内操作前在版本控制打 tag

## 7. 风险

| 风险 | 影响 | 应对 |
|---|---|---|

## 8. 任务动作与前置检查

> 来源：源包批次计划表（`arch-fix-batches-*.md`）。**每个任务必须有一个动作动词**，否则执行时容易"顺手多改"。

| 动作 | 含义 | 边界 |
|---|---|---|
| **加** | 新增文件/类型/配置 | 不动既有逻辑 |
| **修** | 改既有实现 | 不扩大范围 |
| **删** | 移除死代码/废弃项 | 先 grep 引用，再删 |
| **并** | 合并重复实现 | 合并后行为必须等价 |
| **迁** | 移动/重命名 | 保留历史（`git mv`），一次一个目录 |

**前置检查（动手前逐条确认）**：
- [ ] 基线已记录：编译通过、相关测试全绿
- [ ] 工作区干净（或已存档在途改动）
- [ ] 要改的符号已用 `grep` 确认全部引用点
- [ ] 涉及 `UPROPERTY` 改名/存档字段的，已确认 Core Redirect 或迁移方案
- [ ] 涉及资产/BP/关卡的，已确认由人操作（AI 不改 `.uasset`）

## 9. 每批收尾三件事

> 每完成一个可独立验证的批次（不是整个迭代），做这三件：

1. **新鲜验证证据**：贴本次的编译/测试输出 / 截图 / Insights 数字（见 `开发规范/验证与门禁.md` §2）
2. **更新知识**：若踩到坑或产生新约束，写进 `knowledge/{module}.md`（可延后到 Phase 5，但必须在 `05-issues.md` 记一行）
3. **独立提交**：一个批次一个 commit，message 写清"做了什么 + 证据 + 回退方式"（AI 不自动 commit，由人执行）

**为什么按批次而不是按迭代**：迭代可能持续数天，中间失败时若只有一个大 commit，回滚会连带丢掉已通过的部分。
