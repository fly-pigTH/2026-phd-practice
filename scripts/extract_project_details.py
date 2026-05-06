#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from extract_project_table import normalize_text


ROOT = Path(__file__).resolve().parents[1]
DETAIL_DIR = ROOT / "data" / "raw" / "项目详情HTML"
LINKS_JSON = ROOT / "data" / "raw" / "项目详情链接清单.json"
OUT_JSON = ROOT / "data" / "processed" / "项目详情信息表.json"
OUT_CSV = ROOT / "data" / "processed" / "项目详情信息表.csv"

FIELDS = [
    "序号",
    "项目名称",
    "项目ID",
    "详情链接",
    "项目编号",
    "所属基地编号",
    "所属基地名称",
    "研究方向",
    "预计工作量(天)",
    "所需准备工作",
    "是否重点项目",
    "单位名称",
    "单位省市",
    "单位区县",
    "单位地址",
    "项目背景",
    "项目目标",
    "需要解决的关键技术问题",
    "现有条件",
    "时间安排",
    "详情介绍",
    "HTML文件",
]


def clean_value(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]*\n[ \t]*", "\n", value)
    return value.strip()


def meaningful(value: str) -> bool:
    value = clean_value(value)
    return bool(value and value not in {"无", "无。", "暂无", "暂无。", "无\n", "-"})


def trim_intro(value: str, limit: int = 240) -> str:
    value = re.sub(r"\s+", " ", clean_value(value))
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def build_intro(fields: dict[str, str]) -> str:
    candidates = [
        ("目标", fields.get("项目目标", "")),
        ("背景", fields.get("项目背景", "")),
        ("关键问题", fields.get("需要解决的关键技术问题", "")),
        ("准备", fields.get("所需准备工作", "")),
        ("条件", fields.get("现有条件", "")),
        ("安排", fields.get("时间安排", "")),
    ]
    for label, value in candidates:
        if meaningful(value):
            return f"{label}：{trim_intro(value)}"
    return "详情页未提供有效介绍。"


def load_links() -> dict[int, str]:
    if not LINKS_JSON.exists():
        return {}
    rows = json.loads(LINKS_JSON.read_text(encoding="utf-8"))
    return {int(row["seq"]): row.get("url", "") for row in rows if str(row.get("seq", "")).isdigit()}


def extract_label_values(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for label in soup.select("label"):
        key = clean_value(label.get_text(" ", strip=True)).rstrip(":：")
        if not key:
            continue
        span = label.find_next_sibling("span")
        if span is None and label.parent is not None:
            span = label.parent.find("span")
        values[key] = clean_value(span.get_text("\n", strip=True)) if span else ""
    return values


def parse_detail_file(path: Path, links_by_seq: dict[int, str]) -> dict[str, str]:
    seq_match = re.match(r"(\d+)_", path.name)
    if not seq_match:
        raise ValueError(f"Cannot parse seq from file name: {path}")
    seq = int(seq_match.group(1))
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    values = extract_label_values(soup)
    title_node = soup.select_one(".content .title") or soup.select_one(".title")
    project_id_node = soup.select_one("input#xmid")

    row = {field: "" for field in FIELDS}
    row["序号"] = str(seq)
    row["项目名称"] = clean_value(title_node.get_text(" ", strip=True)) if title_node else ""
    row["项目ID"] = project_id_node.get("value", "").strip() if project_id_node else ""
    row["详情链接"] = links_by_seq.get(seq, "")
    for field in FIELDS:
        if field in values:
            row[field] = values[field]
    if row["预计工作量(天)"] == "天":
        row["预计工作量(天)"] = ""
    row["详情介绍"] = build_intro(row)
    row["HTML文件"] = str(path.relative_to(ROOT))
    return row


def main() -> None:
    if not DETAIL_DIR.exists():
        raise SystemExit(f"Detail HTML directory not found: {DETAIL_DIR}")

    links_by_seq = load_links()
    rows = [
        parse_detail_file(path, links_by_seq)
        for path in sorted(DETAIL_DIR.glob("*.html"), key=lambda item: int(item.name.split("_", 1)[0]))
    ]

    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"details={len(rows)}")
    print(f"json={OUT_JSON}")
    print(f"csv={OUT_CSV}")


if __name__ == "__main__":
    main()
