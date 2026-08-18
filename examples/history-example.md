# 每日历史记录 · 示例

本示例全部为**虚构数据**，只用来演示 `scripts/history.py` 的用法与记录格式。

## 1. 追加记录

```bash
python scripts/history.py add --date 2026-08-18 --cat 项目A --text "完成需求评审，输出 v1 方案"
python scripts/history.py add --date 2026-08-18 --cat 周会 --text "同步了下季度排期，确认 9 月迭代目标"
python scripts/history.py add --date 2026-08-19 --cat 学习 --text "读完《设计数据密集型应用》前三章"
```

## 2. 查询

```bash
python scripts/history.py list                 # 最近 20 条，倒序
python scripts/history.py list --date 2026-08-18
python scripts/history.py list --limit 50
```

## 3. 统计

```bash
python scripts/history.py stats
# 日期          分类           条数
# 2026-08-19  学习           1
# 2026-08-18  项目A          1
# 2026-08-18  周会           1
```

## 4. 导出 HTML 视图（数据源仍是 DB）

```bash
python scripts/history.py export              # 生成 每日历史记录.html
```

## 示例渲染效果（一条虚构记录）

| 日期 | 分类 | 内容 |
|---|---|---|
| 2026-08-18 | 项目A | 完成需求评审，输出 v1 方案 |

> 实际数据落在 `daily_history.db`（SQLite）。HTML 只是浏览视图，追加/修改永远走 `history.py add`，不要在 HTML 上手改。
