# `change/` 变更档案

> 回答"**这次改了什么、为什么**"（what changed & why）。
> 一个模块一个目录，同一时间只允许一组进行中的迭代。

---

## 生命周期

```
change/{module}/_tmp/            进行中（wip）
        ↓  /workflow archive
change/{module}/{subCategory}/   已归档（immutable 历史）
        ↓  delta 合并
spec/{module}.md                 活规格（当前真相）
```

---

## 目录结构

```
change/
├─ versions.json                 全局索引（模块 / 状态 / 子分类）
├─ {module}/
│  ├─ version.json               模块级索引
│  ├─ _tmp/                      进行中（同时只允许一组）
│  │  ├─ 00-prd-analysis.md      Phase 0（可选）
│  │  ├─ 01-requirements.md      Phase 1
│  │  ├─ 02-design.md            Phase 2
│  │  ├─ 03-plan.md              Phase 3
│  │  ├─ 04-review-report.md     各阶段审核共用，追加写
│  │  ├─ 05-issues.md            问题与验证记录
│  │  ├─ 06-knowledge-update.md  Phase 5
│  │  └─ 07-spec-delta.md        Phase 2（行为变更时必产）
│  └─ {subCategory}/             归档后
│     ├─ version.json
│     └─ 01-…07-….md
```

---

## 规则

| 规则 | 说明 |
|---|---|
| `_tmp/` 下**没有版本号子目录** | 文档直接平铺 |
| 同一模块同时只允许一组 `_tmp/` | 有内容时先 archive |
| 无 `archive/` 目录 | 归档直接进 `{subCategory}/` |
| 子分类名 = 功能精准描述 | `purchase`、`schema-migration`，不要 `fix1`/`v2` |
| 已归档目录只读 | 要改就再走一轮迭代，覆盖同名子分类 |
| `04-review-report.md` 追加写 | 保留每一轮审核历史，不覆盖 |

---

## 版本号

在**子分类维度**递增（不是全局）：

| 类型 | 规则 | 适用 |
|---|---|---|
| `major` | v{X+1}.0.0 | 重构、破坏性变更 |
| `minor` | v{x.Y+1}.0 | 新增能力 |
| `patch` | v{x.y.Z+1} | 修 Bug、调数值 |

新子分类从 `v0.0.1` 起。

---

## 归档的硬门控

归档前必须通过：

1. `07-spec-delta.md` 存在（若本次有行为变更）
2. `/workflow validate` 的 C1–C7 全过（error 级）
3. `05-issues.md` 的验证记录已回填
4. `06-knowledge-update.md` 已填写

失败则**阻断归档**，把失败项写入 `05-issues.md`。
