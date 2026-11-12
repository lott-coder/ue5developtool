# 技术设计文档: <主题>

> 模块: {module}
> 日期: YYYY-MM-DD
> 状态: 草稿 / 已确认设计
> 权威模式: Standalone / Dedicated
> 在途契约终检: <待执行 / 0 冲突（比对 N 个在途模块） YYYY-MM-DD>

## ★ 核心重点（一目了然区）

> 看这部分就知道怎么干。

### ★1. 架构总览
<新增/修改什么，落在哪个模块，一句话概括>

### ★2. 关键类型清单
| 类型 | 模块 | 职责 | 依赖 |
|------|------|------|------|
| UEconomySubsystem | GameFramework | 唯一写入口 | UGameInstance |
| UEconomyConfig | GameCore | 配置数据 | — |

### ★3. 接入点
- 模块：`Source/GameFramework/GameFramework.Build.cs`（是否需要新增依赖）
- 注册：Subsystem 自动实例化 / GameMode 配置
- 配置：`Content/Data/Economy/DA_EconomyConfig`（新增或改字段）
- 存档：是否新增 `USaveGame` 字段，`SchemaVersion` 是否提升
- Blueprint 装配：<无 / 只有 XX Widget 需要绑事件>
- 入口：哪个 PlayerController / Widget 调用

### ★4. 核心数据流
<DataAsset → Gameplay 层 → GameCore 规则 → 存档/复制 → Presentation>

### ★5. 实现步骤概要
| 步骤 | 内容 | 依赖 |
|------|------|------|

---

## 详细设计（补齐区）

### 1. 架构设计
#### 1.1 模块定位
<在四层中的位置，与哪些现有类型交互，明确不做什么>

#### 1.2 类型结构
```cpp
// 关键签名（不必完整实现）
UCLASS()
class GAMEFRAMEWORK_API UEconomySubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    /** 尝试购买；余额不足时不产生任何变更。 */
    UFUNCTION(BlueprintCallable, Category = "Economy")
    bool TryBuy(const FString& ItemId, FString& OutReason);
};
```

#### 1.3 依赖方向
<谁依赖谁；`*.Build.cs` 是否变动>

### 2. 数据结构
#### 2.1 核心类型
```cpp
USTRUCT(BlueprintType)
struct FPriceRule { GENERATED_BODY() };

enum class EPurchaseResult : uint8 { Ok, Insufficient, InvalidItem };
```

#### 2.2 接口 / 事件契约（C1）
| 名称 | 类型 | 方向 | 参数 | 说明 |
|------|------|------|------|------|
| ServerRequestBuy | RPC(Server, Reliable, WithValidation) | C→S | (FString ItemId) | 只表达意图 |
| OnCoinsChanged | 动态多播委托 | Gameplay→UI | (int64 NewTotal) | 状态变化广播 |
| TotalCoins | Replicated 属性 | S→C | — | 权威数值 |

#### 2.3 复制策略
| 状态 | 是否复制 | 理由 |
|------|---------|------|
| TotalCoins | 是 | 客户端需展示 |
| PurchaseCooldown | 否 | 仅服务器判定 |

#### 2.4 存档影响（C2）
- 类型：`USaveGame` 子类 / 后端
- 字段变更：
- `SchemaVersion`：<不变 / N→N+1>
- 迁移方案：<无变更 / 具体规则>
- `UPROPERTY` 改名：<无 / 有 → 需 Core Redirects>
- 旧存档兼容：<可读 / 需迁移 / 不兼容（说明理由）>

### 3. 交互流程
#### 3.1 时序
```
Widget 点击 → PC::RequestBuy → ServerRequestBuy（校验）
  → UEconomySubsystem::TryBuy（Gameplay 层写入口）
  → GameCore 规则计算
  → 写存档 / 更新 Replicated 属性
  → OnCoinsChanged 广播 → Widget 刷新
```

#### 3.2 生命周期
<GameInstance 级 / World 级 / 表现级的初始化序；委托绑定与解绑点>

#### 3.3 错误处理与兜底
| 失败点 | 表现 | 处理 |
|---|---|---|
| 余额不足 | 返回 false + `INSUFFICIENT` | 不做任何变更 |
| 存档写失败 | 返回 false + `IO` | 回滚内存状态 + 提示 |
| 非权威端调用 | `HasAuthority()` 拦截 | 直接 return，不产生副作用 |

### 4. 性能与防御性设计
#### 4.1 Tick 策略
<是否需要 Tick；若需要，为何不能用计时器/事件/复制回调>
#### 4.2 性能红线
- `Tick` 内禁止：`FindComponentByClass`、`GetAllActorsOfClass`、同步 `LoadObject`、`FString` 拼接
- 热路径预分配（`Reserve`）、用 `FName` 做标识
#### 4.3 防御性编码
- 幂等：<哪些操作需要 `bGranted` 或 requestId>
- 终态守卫：<哪些方法需要状态判断>
- 清理顺序：停计时器 → 解绑委托 → 释放引用
#### 4.4 内存/资产预估
<新增常驻对象、DataAsset 体积>

### 5. Blueprint 边界声明
| BP 资产 | 职责（仅装配） | 确认不含业务规则 |
|---------|---------------|----------------|
| `WBP_ShopPanel` | 绑按钮事件、显示数值 | ☐ |

> 任何"计算/判定/结算"必须在 C++。BP 只做装配与表现（见 `开发规范/架构.md` §7）。

### 6. 架构约束遵守声明
- [ ] 类型放在正确模块，未引入反向依赖
- [ ] Gameplay 层是唯一写入口，Presentation 不直接改状态
- [ ] 权威模式与 `架构.md` 一致（Standalone / Dedicated）
- [ ] Server RPC 有 `HasAuthority()` 守卫与五项校验
- [ ] `UObject*` 成员都有 `UPROPERTY()` 且用 `TObjectPtr`
- [ ] 复制属性已声明 `GetLifetimeReplicatedProps`
- [ ] 外部输入已净化（NaN/越界/非法 ID）
- [ ] 存档变更有 `SchemaVersion` 迁移或 Core Redirect
- [ ] 业务逻辑未进 Blueprint
- [ ] 验证策略可执行（用例 + 级别，L1 优先）

### 7. 验证策略
| 用例 | 级别 | 覆盖的 AC | 构造方式 |
|------|------|----------|---------|
| Economy.PriceRule | L1 | AC-1 | 纯 C++，无 World |
| Economy.Buy_Insufficient | L1 | AC-2 | Subsystem 测试替身 |
| Replication.Buy_AuthorityOnly | L2 | AC-5 | 双端 Automation |

### 8. 风险评估
| 风险 | 影响 | 应对 |
|---|---|---|
