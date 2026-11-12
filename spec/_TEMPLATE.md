# {module} 模块规格（活规格基线）

> 由 change/{module}/{subCategory}/v{X.Y.Z} 的 07-spec-delta.md 归档合并生成（YYYY-MM-DD）。
> 最后归档 v{X.Y.Z} @ YYYY-MM-DD
> 本文件是当前真相源（what）；只读——更新唯一入口是 /workflow archive 的 delta 合并。

---

## R1 — <能力标题>

系统必须 <一句话行为契约>。

### 场景: <场景名>
- 当 <前置条件 / 输入>
- 则 <权威端裁定结果>

### 场景: <边界场景名>
- 当 <越界 / 空数据 / 并发 / 首次启动>
- 则 <拒绝 / 兜底 / 幂等处理>

---

## R2 — <能力标题>

系统必须 <一句话行为契约>。

### 场景: <场景名>
- 当 <前置条件 / 输入>
- 则 <权威端裁定结果>

---

<!--
本文件由 /workflow archive 维护，禁止手改。
新增/修改能力的唯一路径：
  1. 在 change/{module}/_tmp/07-spec-delta.md 写 ADDED/MODIFIED/REMOVED
  2. /workflow validate 通过
  3. /workflow archive（自动合并进本文件）

约定：
- R{n} 全局唯一，只增不复用（删除的编号保留空洞）
- 每条至少一个「### 场景:」，含「当…」「则…」
- 「则」落在权威端：Dedicated=服务器（`HasAuthority()` 侧）；Standalone=Gameplay 层唯一写入口
-->
