# 2026 博士生社会实践项目数据

本目录整理了 2026 博士生社会实践项目列表、详情页抓取结果、清洗后的完整信息表，以及本地可视化网页。

## 目录结构

```text
.
├── assets/                  # 可视化静态资源
├── data/
│   ├── raw/                 # 原始 PDF、详情 HTML、详情链接清单
│   └── processed/           # 清洗后的 CSV/XLSX/JSON 数据
├── reports/                 # 数据质量检查报告
├── scripts/                 # 数据抽取、清洗、合并、网页构建脚本
└── site/                    # 最终可视化网页
```

## 主要产物

- `site/index.html`：项目地域可视化网页。
- `data/processed/项目完整信息表.xlsx`：推荐使用的完整 Excel 表。
- `data/processed/项目完整信息表.csv`：同上，CSV 版本。
- `reports/数据质量检查报告.md`：数据口径、缺失值和风险说明。

## 重新生成

从现有原始数据重新生成全部处理结果：

```bash
python3 scripts/extract_project_table.py
python3 scripts/extract_project_details.py
python3 scripts/build_enriched_project_table.py
python3 scripts/build_dashboard.py
```

## 数据口径

- 地域分析使用 `项目省市(用于地图)` 和 `地域分区`。
- 竞争度分析只建议使用 `申请数据状态 = 完整` 的项目。
- `申请数缺失` 和 `第四志愿缺失` 来自源数据缺失/截断，不能从详情页可靠恢复。
