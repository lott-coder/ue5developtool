---
name: knowledge-get
description: 查询项目知识与活规格。按模块检索 knowledge/ 与 spec/，回答"这个模块怎么做的""现在必须是什么行为""以前踩过什么坑"。在任何设计/实现前需要了解现状时使用。
user-invocable: true
allowed-tools: Read, Grep, Glob
version: 1.0.0
---

# 知识查询（knowledge-get）

> 纯文件知识库，**无向量库**。检索靠 Grep 精确匹配 + 目录约定，结果可解释、可复核。

## 三层查什么

| 你想知道 | 查哪里 | 回答的问题 |
|---|---|---|
| 系统**现在必须**是什么行为 | `spec/{module}.md` | what（契约、场景、数值） |
| 这个模块**怎么实现**、踩过什么坑 | `knowledge/{module}.md` | how（设计原理、坑、约束） |
| 上次**改了什么**、为什么 | `change/{module}/**` | what changed & why |
| 某条规则的**权威定义** | `开发规范/*.md` | 规范本文 |

**这三者不可互相替代**：`spec` 没有实现细节，`knowledge` 没有契约效力，`change` 只是历史。

---

## 使用方式

```
/knowledge-get <module> [关键词]
```

- `module`：模块名（必须与 `change/` 目录名一致）
- `关键词`（可选）：如"存档""解锁""冷却"

---

## 步骤

1. **定位模块**：模块名不在 `change/` 或 `knowledge/` 下 → 提示用户确认；可能是 `_misc` 或尚未建档。
2. **读活规格**：`spec/{module}.md`（若存在）→ 提取 `R{n}` 能力清单与场景。
3. **读知识库**：`knowledge/{module}.md` → 提取架构说明、坑、约束。
4. **关键词检索**（有关键词时）：
   ```
   Grep "关键词" knowledge/ spec/
   Grep "关键词" Source/
   ```
5. **读最近变更**：`change/{module}/` 下最近 1–2 个子分类的 `01-requirements.md` 与 `03-plan.md`。
6. **输出结构化摘要**：

```
## {module} 现状

### 能力清单（spec）
- R1 …（版本戳）
- R2 …

### 实现要点（knowledge）
- 关键类型与分层落位
- 已知坑

### 近期变更
- v0.1.0 purchase：新增…

### 相关规范
- 架构.md §2 权威模型
- 验证与门禁.md §5 验收标准
```

---

## 检索技巧

| 目标 | 查法 |
|---|---|
| 某接口谁在用 | `Grep "IEconomyService" Source/` |
| 某数值从哪来 | `Grep "Price" Content/` 定位 DataAsset + 读对应字段 |
| 某个坑是否已记录 | `Grep "坑\|注意\|禁止" knowledge/{module}.md` |
| 契约是否被动过 | `Grep "R{n}" spec/ change/` |
| 谁改过这个模块 | `git log --oneline -20 -- Source/<path>` |

---

## 注意事项

- **`spec/` 是只读的**：本技能只读不写。要改规格必须走 `/workflow archive`。
- **`knowledge/` 可读可写**：更新走 `/knowledge-set`（默认 dry-run）。
- **找不到不等于没有**：先查 `knowledge/README.md` 索引，再查 `_misc`，最后 Grep 全库。
- **优先信 spec 而非代码**：代码可能偏离契约——偏离本身就是 Bug。发现偏离时在答复中显式指出，不要默默以代码为准。
