# 知识库更新 - {module} v{X.Y.Z}

> Phase 5 产物。记录本次迭代对 `knowledge/` 的更新，**不重复 spec 的契约内容**。

## 1. 更新的知识模块

| 文档 | 操作 | 原因 |
|------|------|------|
| `knowledge/{module}.md` | 新增 / 修改章节 | |

## 2. 变更详情

### 新增内容
- <为什么值得记：一年后读到能少踩一次坑吗？>

### 修正内容
- <之前记错了什么，正确是什么>

### 踩坑记录
| 现象 | 根因 | 正确做法 |
|---|---|---|

## 3. 索引更新

- [ ] `knowledge/README.md` 是否需要新增模块入口
- [ ] 相关模块是否需交叉引用

## 4. 未沉淀项（显式声明）

| 项 | 为何不沉淀 |
|---|---|
| | 一次性问题 / 已在代码注释中 / 属于 spec 而非 knowledge |

## 5. 规格增量确认

- [ ] 本次是否涉及行为变更？
  - 是 → `07-spec-delta.md` 已产出，`/workflow validate` 已通过
  - 否 → 理由：<纯重构 / 纯性能 / 纯文档>
- [ ] 已执行 `/workflow archive`

## 6. 归档信息

- 归档路径：`change/{module}/{subCategory}/`
- 版本：`v{X.Y.Z}`
- `spec/{module}.md` 合并结果：ADDED n / MODIFIED n / REMOVED n
