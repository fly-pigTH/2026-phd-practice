#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "项目申请信息表.csv"
DETAIL_JSON_PATH = ROOT / "data" / "processed" / "项目详情信息表.json"
HTML_PATH = ROOT / "site" / "index.html"
MAP_SVG_PATH = ROOT / "assets" / "china_blank_province_map.svg"
DATA_TIMESTAMP = "2026-05-01 13:30"

PROVINCE_FALLBACKS = {
    "德阳基地": "四川省",
    "苏州吴中基地": "江苏省",
    "广东惠州": "广东省",
    "北京亦庄": "北京市",
    "中核集团": "北京市",
    "江苏南通": "江苏省",
    "国家能源集团": "北京市",
    "浙江金华": "浙江省",
    "赛力斯集团": "重庆市",
    "吉林长春": "吉林省",
    "新疆和田": "新疆维吾尔自治区",
    "清华大学研究生社会实践海淀基地": "北京市",
    "四川凉山": "四川省",
    "小米集团": "北京市",
}

REGION_MAP = {
    "北京市": "华北",
    "天津市": "华北",
    "河北省": "华北",
    "山西省": "华北",
    "内蒙古自治区": "华北",
    "辽宁省": "东北",
    "吉林省": "东北",
    "黑龙江省": "东北",
    "上海市": "华东",
    "江苏省": "华东",
    "浙江省": "华东",
    "安徽省": "华东",
    "福建省": "华东",
    "江西省": "华东",
    "山东省": "华东",
    "河南省": "华中",
    "湖北省": "华中",
    "湖南省": "华中",
    "广东省": "华南",
    "广西壮族自治区": "华南",
    "海南省": "华南",
    "重庆市": "西南",
    "四川省": "西南",
    "贵州省": "西南",
    "云南省": "西南",
    "西藏自治区": "西南",
    "陕西省": "西北",
    "甘肃省": "西北",
    "青海省": "西北",
    "宁夏回族自治区": "西北",
    "新疆维吾尔自治区": "西北",
    "香港特别行政区": "港澳台",
    "澳门特别行政区": "港澳台",
    "台湾省": "港澳台",
}

REGION_ORDER = ["全部区域", "华北", "华东", "华南", "华中", "西南", "西北", "东北", "港澳台", "未分区"]

PROVINCE_META = {
    "pBJ": {"province": "北京市", "short": "北京", "region": "华北"},
    "pTJ": {"province": "天津市", "short": "天津", "region": "华北"},
    "pHE": {"province": "河北省", "short": "河北", "region": "华北"},
    "pSX": {"province": "山西省", "short": "山西", "region": "华北"},
    "pNM": {"province": "内蒙古自治区", "short": "内蒙古", "region": "华北"},
    "pLN": {"province": "辽宁省", "short": "辽宁", "region": "东北"},
    "pJL": {"province": "吉林省", "short": "吉林", "region": "东北"},
    "pHJ": {"province": "黑龙江省", "short": "黑龙江", "region": "东北"},
    "pSH": {"province": "上海市", "short": "上海", "region": "华东"},
    "pJS": {"province": "江苏省", "short": "江苏", "region": "华东"},
    "pZJ": {"province": "浙江省", "short": "浙江", "region": "华东"},
    "pAH": {"province": "安徽省", "short": "安徽", "region": "华东"},
    "pFJ": {"province": "福建省", "short": "福建", "region": "华东"},
    "pJX": {"province": "江西省", "short": "江西", "region": "华东"},
    "pSD": {"province": "山东省", "short": "山东", "region": "华东"},
    "pHA": {"province": "河南省", "short": "河南", "region": "华中"},
    "pHB": {"province": "湖北省", "short": "湖北", "region": "华中"},
    "pHN": {"province": "湖南省", "short": "湖南", "region": "华中"},
    "pGD": {"province": "广东省", "short": "广东", "region": "华南"},
    "pGX": {"province": "广西壮族自治区", "short": "广西", "region": "华南"},
    "pHI": {"province": "海南省", "short": "海南", "region": "华南"},
    "pCQ": {"province": "重庆市", "short": "重庆", "region": "西南"},
    "pSC": {"province": "四川省", "short": "四川", "region": "西南"},
    "pGZ": {"province": "贵州省", "short": "贵州", "region": "西南"},
    "pYN": {"province": "云南省", "short": "云南", "region": "西南"},
    "pXZ": {"province": "西藏自治区", "short": "西藏", "region": "西南"},
    "pSN": {"province": "陕西省", "short": "陕西", "region": "西北"},
    "pGS": {"province": "甘肃省", "short": "甘肃", "region": "西北"},
    "pQH": {"province": "青海省", "short": "青海", "region": "西北"},
    "pNX": {"province": "宁夏回族自治区", "short": "宁夏", "region": "西北"},
    "pXJ": {"province": "新疆维吾尔自治区", "short": "新疆", "region": "西北"},
    "pTW": {"province": "台湾省", "short": "台湾", "region": "港澳台"},
    "pHK": {"province": "香港特别行政区", "short": "香港", "region": "港澳台"},
    "pMO": {"province": "澳门特别行政区", "short": "澳门", "region": "港澳台"},
}

PROVINCE_LOOKUP = {
    meta["province"]: {
        "code": code,
        "short": meta["short"],
        "region": meta["region"],
        "order": index,
    }
    for index, (code, meta) in enumerate(PROVINCE_META.items())
}


def to_int(value: str) -> int:
    value = (value or "").strip()
    return int(value) if value.isdigit() else 0


def short_name(province: str) -> str:
    if province in PROVINCE_LOOKUP:
        return PROVINCE_LOOKUP[province]["short"]
    name = province
    for suffix in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "省", "市"):
        name = name.replace(suffix, "")
    return name or province


def infer_province(raw: str, base_name: str) -> str:
    raw = (raw or "").strip()
    if raw and raw != "无":
        return raw
    if base_name in PROVINCE_FALLBACKS:
        return PROVINCE_FALLBACKS[base_name]
    for province in REGION_MAP:
        token = short_name(province)
        if token and token in base_name:
            return province
    return "未注明"


def competition_band(value: float) -> str:
    if value <= 0.5:
        return "低竞争"
    if value <= 1.0:
        return "中竞争"
    return "高竞争"


def load_project_details() -> dict[int, dict]:
    if not DETAIL_JSON_PATH.exists():
        return {}
    rows = json.loads(DETAIL_JSON_PATH.read_text(encoding="utf-8"))
    details: dict[int, dict] = {}
    for row in rows:
        seq = str(row.get("序号", "")).strip()
        if not seq.isdigit():
            continue
        details[int(seq)] = {
            "title": row.get("项目名称", ""),
            "projectCode": row.get("项目编号", ""),
            "baseCode": row.get("所属基地编号", ""),
            "baseName": row.get("所属基地名称", ""),
            "researchDirection": row.get("研究方向", ""),
            "workloadDays": row.get("预计工作量(天)", ""),
            "preparation": row.get("所需准备工作", ""),
            "isKeyText": row.get("是否重点项目", ""),
            "unitName": row.get("单位名称", ""),
            "unitProvince": row.get("单位省市", ""),
            "unitDistrict": row.get("单位区县", ""),
            "unitAddress": row.get("单位地址", ""),
            "background": row.get("项目背景", ""),
            "goal": row.get("项目目标", ""),
            "keyProblem": row.get("需要解决的关键技术问题", ""),
            "existingCondition": row.get("现有条件", ""),
            "schedule": row.get("时间安排", ""),
            "intro": row.get("详情介绍", ""),
            "url": row.get("详情链接", ""),
            "htmlFile": row.get("HTML文件", ""),
        }
    return details


def load_svg_map() -> str:
    text = MAP_SVG_PATH.read_text(encoding="utf-8")
    text = re.sub(r"^\<\?xml.*?\?>\s*", "", text)
    text = re.sub(
        r"<svg[^>]*width=\"1000\" height=\"850\"[^>]*>",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 850" class="china-map-svg" role="img" aria-label="中国省级地图">',
        text,
        count=1,
    )
    return text


def normalize_rows() -> tuple[list[dict], dict]:
    projects: list[dict] = []
    stats: dict[str, int | float] = defaultdict(int)
    details_by_seq = load_project_details()

    with CSV_PATH.open(encoding="utf-8-sig") as f:
        for index, row in enumerate(csv.DictReader(f), start=1):
            detail = details_by_seq.get(index, {})
            project_name = detail.get("title") or row["项目名称"]
            need = max(to_int(row["需求人数"]), 1)
            first = to_int(row["第一志愿申请数"])
            second = to_int(row["第二志愿申请数"])
            third = to_int(row["第三志愿申请数"])
            fourth = to_int(row["第四志愿申请数"])
            total_apply = first + second + third + fourth
            note = (row["备注"] or "").strip()
            applicant_status = "完整"
            if note == "原PDF未显示志愿申请数":
                applicant_status = "申请数缺失"
            elif note == "PDF右侧截断，第四志愿数未显示":
                applicant_status = "第四志愿缺失"
            applicant_data_complete = applicant_status == "完整"
            province = infer_province(row["基地省市"], row["基地名称"])
            if province == "未注明" and detail.get("unitProvince"):
                province = detail["unitProvince"].strip()
            region = REGION_MAP.get(province, "未分区")
            competition = round(total_apply / need, 2)
            first_pressure = round(first / need, 2)
            opportunity = round((need * 2.4) + (1.2 if row["是否重点"] == "是" else 0) - (first * 1.4) - (competition * 5.4), 2)
            if not applicant_data_complete:
                opportunity = round(-1000 + need + (1.2 if row["是否重点"] == "是" else 0), 2)
            lookup = PROVINCE_LOOKUP.get(province, {})

            projects.append(
                {
                    "id": index,
                    "name": project_name,
                    "isKey": row["是否重点"] == "是",
                    "need": need,
                    "firstChoice": first,
                    "secondChoice": second,
                    "thirdChoice": third,
                    "fourthChoice": fourth,
                    "totalApplicants": total_apply,
                    "competition": competition,
                    "competitionBand": competition_band(competition) if applicant_data_complete else "申请数不完整",
                    "firstPressure": first_pressure,
                    "opportunity": opportunity,
                    "applicantDataStatus": applicant_status,
                    "applicantDataComplete": applicant_data_complete,
                    "baseName": row["基地名称"],
                    "baseLevel": row["基地级别"] or "未注明",
                    "province": province,
                    "provinceShort": short_name(province),
                    "provinceCode": lookup.get("code", ""),
                    "region": region,
                    "note": note,
                    "detail": detail,
                    "searchText": " ".join(
                        [
                            row["项目名称"],
                            project_name,
                            row["基地名称"],
                            province,
                            region,
                            row["基地级别"] or "",
                            detail.get("researchDirection", ""),
                            detail.get("preparation", ""),
                            detail.get("unitName", ""),
                            detail.get("unitAddress", ""),
                            detail.get("intro", ""),
                            detail.get("goal", ""),
                        ]
                    ).lower(),
                }
            )

            stats["totalProjects"] += 1
            stats["totalNeed"] += need
            stats["keyProjects"] += 1 if row["是否重点"] == "是" else 0
            stats["knownApplicantLowerBound"] += total_apply
            stats["incompleteApplicantProjects"] += 0 if applicant_data_complete else 1
            if applicant_data_complete:
                stats["knownApplicantProjects"] += 1
                stats["knownNeed"] += need
                stats["totalApplicants"] += total_apply
            stats["unmatchedProjects"] += 1 if province == "未注明" else 0

    stats["avgCompetition"] = round(stats["totalApplicants"] / max(stats["knownNeed"], 1), 2)
    stats["detailProjects"] = len(details_by_seq)
    return projects, dict(stats)


def province_option_order(province: str) -> tuple[int, str]:
    if province in PROVINCE_LOOKUP:
        return (PROVINCE_LOOKUP[province]["order"], province)
    return (999, province)


def build_payload(projects: list[dict], summary: dict) -> dict:
    province_options = sorted({project["province"] for project in projects}, key=province_option_order)
    return {
        "timestamp": DATA_TIMESTAMP,
        "summary": summary,
        "projects": projects,
        "regionOrder": REGION_ORDER,
        "provinceLookup": PROVINCE_LOOKUP,
        "provinceOptions": province_options,
    }


def build_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    svg_map = load_svg_map()
    html = HTML_TEMPLATE.replace("__DATA__", data_json)
    html = html.replace("__SVG__", svg_map)
    html = html.replace("__TIMESTAMP__", DATA_TIMESTAMP)
    return html


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>项目地域选择面板</title>
  <style>
    :root {
      --paper: #f5f5f7;
      --paper-warm: #fbfbfd;
      --slate: #e8e8ed;
      --ink: #1d1d1f;
      --ink-soft: #6e6e73;
      --ink-faint: #9a9aa0;
      --line: rgba(0, 0, 0, 0.08);
      --line-strong: rgba(0, 0, 0, 0.13);
      --surface: rgba(255, 255, 255, 0.72);
      --surface-strong: rgba(255, 255, 255, 0.94);
      --accent: #007aff;
      --accent-deep: #0057b8;
      --teal: #0a84ff;
      --teal-soft: #5ac8fa;
      --olive: #34c759;
      --gold: #ff9f0a;
      --good: #34c759;
      --warn: #ff9f0a;
      --shadow: 0 28px 80px rgba(0, 0, 0, 0.14);
      --shadow-soft: 0 16px 44px rgba(0, 0, 0, 0.08);
      --radius: 16px;
      --radius-lg: 26px;
      --panel-fill: rgba(255, 255, 255, 0.66);
      --panel-surface: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 248, 251, 0.76));
      --panel-border: rgba(0, 0, 0, 0.09);
    }

    * { box-sizing: border-box; }

    html, body {
      margin: 0;
      height: 100%;
      min-height: 100%;
      overflow: hidden;
      background:
        radial-gradient(circle at 16% 6%, rgba(10, 132, 255, 0.18), transparent 28%),
        radial-gradient(circle at 86% 12%, rgba(90, 200, 250, 0.18), transparent 30%),
        linear-gradient(145deg, #f5f5f7 0%, #ffffff 52%, #edf3fb 100%);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Hiragino Sans GB", sans-serif;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.8;
      background-image:
        radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.95) 0 2px, transparent 3px),
        linear-gradient(180deg, rgba(255, 255, 255, 0.42), transparent 62%);
      background-size: 32px 32px, auto;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.62), transparent 92%);
    }

    .app-shell {
      width: min(1540px, calc(100vw - 36px));
      height: calc(100vh - 36px);
      margin: 18px auto;
      display: grid;
      grid-template-columns: minmax(420px, 44%) minmax(680px, 56%);
      border: 1px solid var(--panel-border);
      border-radius: 30px;
      overflow: hidden;
      background: rgba(255, 255, 255, 0.62);
      backdrop-filter: saturate(1.25) blur(28px);
      box-shadow: var(--shadow);
    }

    .map-stage,
    .workboard {
      padding: 24px 24px 22px;
      background:
        radial-gradient(circle at 18% 2%, rgba(255, 255, 255, 0.96), transparent 34%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(245, 247, 250, 0.82));
      display: grid;
      gap: 18px;
      align-content: start;
      min-height: 0;
    }

    .map-stage {
      border-right: 1px solid var(--panel-border);
      overflow: auto;
      scrollbar-gutter: stable;
    }

    .stage-top,
    .board-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
    }

    .kicker {
      font-size: 11px;
      letter-spacing: 0.13em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 700;
    }

    h1, h2, h3, p {
      margin: 0;
    }

    h1 {
      margin-top: 6px;
      font-size: clamp(34px, 3.1vw, 50px);
      line-height: 0.98;
      letter-spacing: -0.045em;
      font-weight: 700;
    }

    h2 {
      font-size: 32px;
      line-height: 1.05;
      margin-top: 6px;
      font-weight: 700;
      letter-spacing: -0.035em;
    }

    .subtitle {
      margin-top: 10px;
      color: var(--ink-soft);
      line-height: 1.72;
      font-size: 14px;
      max-width: 48ch;
    }

    .stage-meta,
    .board-stamp {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      align-items: center;
      font-size: 12px;
      color: var(--ink-soft);
    }

    .meta-pill,
    .board-stamp span {
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.62);
      backdrop-filter: blur(16px);
      white-space: nowrap;
    }

    .ghost-button {
      flex: 0 0 auto;
      align-self: center;
      appearance: none;
      border: 1px solid rgba(0, 122, 255, 0.22);
      background: rgba(0, 122, 255, 0.08);
      color: var(--ink);
      padding: 10px 13px;
      border-radius: 999px;
      font-size: 13px;
      cursor: pointer;
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
    }

    .ghost-button:hover {
      border-color: rgba(0, 122, 255, 0.38);
      background: rgba(0, 122, 255, 0.14);
      box-shadow: 0 8px 20px rgba(0, 122, 255, 0.12);
      transform: translateY(-1px);
    }

    .ghost-button:disabled {
      opacity: 0.46;
      cursor: default;
      transform: none;
    }

    .metric-ribbon {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      border: 1px solid var(--panel-border);
      border-radius: 24px;
      overflow: hidden;
      background: rgba(255, 255, 255, 0.64);
      backdrop-filter: blur(20px);
      box-shadow: var(--shadow-soft);
    }

    .metric-ribbon article {
      padding: 17px 15px 16px;
      min-height: 98px;
      border-right: 1px solid var(--line);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(250, 250, 252, 0.46));
    }

    .metric-ribbon article:last-child {
      border-right: 0;
    }

    .metric-ribbon span {
      font-size: 12px;
      color: var(--ink-soft);
    }

    .metric-ribbon strong {
      font-size: 34px;
      line-height: 1;
      letter-spacing: -0.045em;
      font-weight: 700;
    }

    .metric-ribbon small {
      font-size: 12px;
      color: var(--ink-soft);
      line-height: 1.45;
    }

    .atlas-layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 16px;
    }

    .map-panel,
    .province-hero,
    .province-ranking,
    .control-band,
    .table-shell {
      border: 1px solid var(--panel-border);
      border-radius: 24px;
      background: var(--panel-surface);
      backdrop-filter: blur(22px);
      box-shadow: var(--shadow-soft);
    }

    .map-panel,
    .province-hero,
    .province-ranking {
      display: grid;
      gap: 12px;
      padding: 16px;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }

    .section-head h3 {
      font-size: 20px;
      line-height: 1.2;
      font-weight: 700;
    }

    .section-head p {
      font-size: 12px;
      color: var(--ink-soft);
    }

    .legend-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      font-size: 12px;
      color: var(--ink-soft);
    }

    .legend-scale {
      display: inline-flex;
      gap: 8px;
      align-items: center;
    }

    .legend-gradient {
      width: 160px;
      height: 10px;
      border-radius: 999px;
      border: 1px solid rgba(0, 122, 255, 0.16);
      background: linear-gradient(90deg, #eef5ff, #82c7ff, #0066cc);
    }

    .map-frame {
      position: relative;
      min-height: 490px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background:
        radial-gradient(circle at 18% 8%, rgba(90, 200, 250, 0.18), transparent 30%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(241, 247, 255, 0.86));
      overflow: hidden;
    }

    .map-canvas {
      width: 100%;
      height: 100%;
      padding: 18px 18px 10px;
    }

    .china-map-svg {
      width: 100%;
      height: auto;
      display: block;
    }

    .china-map-svg .disputed {
      opacity: 0.2;
    }

    .china-map-svg .province path,
    .china-map-svg path[id^="p"] {
      transition: fill 140ms ease, stroke-width 140ms ease, opacity 140ms ease;
    }

    .map-tooltip {
      position: absolute;
      pointer-events: none;
      min-width: 168px;
      max-width: 220px;
      padding: 12px 13px;
      border: 1px solid rgba(0, 0, 0, 0.08);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(18px);
      box-shadow: 0 18px 36px rgba(0, 0, 0, 0.16);
      font-size: 12px;
      line-height: 1.55;
      z-index: 2;
    }

    .map-tooltip strong {
      display: block;
      font-size: 14px;
      margin-bottom: 4px;
      color: var(--ink);
    }

    .map-footer {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
      font-size: 11px;
      color: var(--ink-soft);
      line-height: 1.6;
    }

    .province-brief {
      display: grid;
      gap: 14px;
      padding-top: 2px;
    }

    .province-hero {
      gap: 14px;
    }

    .province-title {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-end;
      margin-bottom: 8px;
    }

    .province-title h3 {
      font-size: 28px;
      line-height: 1.05;
      font-weight: 700;
      letter-spacing: -0.035em;
    }

    .province-title span {
      font-size: 12px;
      color: var(--ink-soft);
      white-space: nowrap;
    }

    .province-summary {
      color: var(--ink-soft);
      font-size: 13px;
      line-height: 1.6;
      margin-bottom: 14px;
    }

    .province-metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .province-metrics div {
      padding: 12px;
      border: 1px solid rgba(0, 0, 0, 0.08);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.58);
    }

    .province-metrics span {
      display: block;
      font-size: 11px;
      color: var(--ink-soft);
      margin-bottom: 6px;
    }

    .province-metrics strong {
      display: block;
      font-size: 22px;
      line-height: 1;
    }

    .focus-projects {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 8px;
    }

    .focus-projects li {
      display: grid;
      gap: 4px;
      padding: 12px 14px;
      border: 1px solid rgba(0, 122, 255, 0.12);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.62);
      box-shadow: inset 3px 0 0 rgba(0, 122, 255, 0.32);
    }

    .focus-projects strong {
      font-size: 13px;
      line-height: 1.5;
      font-weight: 600;
    }

    .focus-projects span {
      font-size: 12px;
      color: var(--ink-soft);
    }

    .province-ranking {
      gap: 10px;
    }

    .province-ranking h4 {
      margin: 0;
      font-size: 13px;
      color: var(--ink-soft);
      font-weight: 600;
      letter-spacing: 0.02em;
    }

    .ranking-list {
      display: grid;
      gap: 8px;
    }

    .ranking-item {
      display: grid;
      grid-template-columns: minmax(86px, 110px) 1fr auto;
      gap: 10px;
      align-items: center;
      font-size: 13px;
      padding: 10px 12px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.58);
      border: 1px solid rgba(0, 0, 0, 0.06);
    }

    .ranking-item strong {
      font-weight: 600;
    }

    .ranking-track {
      position: relative;
      height: 7px;
      background: rgba(0, 0, 0, 0.08);
      overflow: hidden;
      border-radius: 999px;
    }

    .ranking-track i {
      position: absolute;
      inset: 0 auto 0 0;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--teal-soft), var(--accent));
    }

    .workboard {
      grid-template-rows: auto auto minmax(0, 1fr);
      overflow: hidden;
    }

    .board-subtitle {
      margin-top: 10px;
      color: var(--ink-soft);
      font-size: 14px;
      line-height: 1.6;
      max-width: 46ch;
    }

    .control-band {
      display: grid;
      gap: 14px;
      padding: 16px;
      min-height: 0;
    }

    .region-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }

    .region-tab {
      appearance: none;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.58);
      color: var(--ink-soft);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      letter-spacing: 0.02em;
      cursor: pointer;
      transition: all 160ms ease;
    }

    .region-tab.active {
      background: var(--ink);
      border-color: var(--ink);
      color: #fff;
      box-shadow: 0 9px 22px rgba(0, 0, 0, 0.16);
    }

    .region-tab:hover {
      border-color: rgba(0, 122, 255, 0.32);
      color: var(--ink);
    }

    .filter-grid {
      display: grid;
      grid-template-columns: minmax(220px, 1.4fr) repeat(5, minmax(0, 1fr));
      gap: 10px;
    }

    .filter-field {
      display: grid;
      gap: 6px;
    }

    .filter-field label {
      font-size: 11px;
      color: var(--ink-soft);
      text-transform: uppercase;
      letter-spacing: 0.11em;
    }

    .filter-field input,
    .filter-field select {
      width: 100%;
      appearance: none;
      border: 1px solid rgba(0, 0, 0, 0.11);
      background: rgba(255, 255, 255, 0.82);
      color: var(--ink);
      min-height: 44px;
      padding: 11px 12px;
      border-radius: var(--radius);
      font-size: 14px;
      outline: none;
      transition: border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
    }

    .filter-field input:focus,
    .filter-field select:focus {
      border-color: rgba(0, 122, 255, 0.56);
      box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.12);
      background: #fff;
    }

    .result-meta {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
      align-items: center;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .chip {
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
      color: var(--ink-soft);
    }

    .chip strong {
      color: var(--ink);
      font-weight: 600;
    }

    .result-count {
      font-size: 13px;
      color: var(--ink-soft);
      white-space: nowrap;
    }

    .table-shell {
      min-height: 0;
      overflow: auto;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(247, 248, 251, 0.72));
      scrollbar-gutter: stable;
    }

    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 10px;
      table-layout: fixed;
      padding: 0 12px 8px;
    }

    thead th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: rgba(248, 248, 251, 0.92);
      backdrop-filter: blur(16px);
      text-align: left;
      font-size: 12px;
      color: var(--ink-soft);
      font-weight: 600;
      padding: 14px 10px 12px;
      border-bottom: 1px solid var(--line);
      letter-spacing: 0.05em;
    }

    tbody td {
      padding: 14px 10px;
      border-top: 1px solid rgba(0, 0, 0, 0.09);
      border-bottom: 1px solid rgba(0, 0, 0, 0.09);
      vertical-align: top;
      font-size: 13px;
      line-height: 1.55;
      background: rgba(255, 255, 255, 0.76);
    }

    tbody td:first-child {
      border-left: 1px solid rgba(0, 0, 0, 0.09);
      border-radius: 16px 0 0 16px;
    }

    tbody td:last-child {
      border-right: 1px solid rgba(0, 0, 0, 0.09);
      border-radius: 0 16px 16px 0;
    }

    tbody tr:nth-child(even) {
      background: transparent;
    }

    tbody tr:hover {
      background: transparent;
    }

    tbody tr:hover td {
      background: rgba(255, 255, 255, 0.96);
      border-color: rgba(0, 122, 255, 0.2);
      box-shadow: 0 10px 26px rgba(0, 0, 0, 0.06);
    }

    .col-project { width: 33%; }
    .col-location { width: 19%; }
    .col-base { width: 15%; }
    .col-num { width: 8%; }
    .col-advice { width: 17%; }

    .project-title-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 7px;
    }

    .project-name {
      font-weight: 600;
      color: var(--ink);
      word-break: break-word;
      letter-spacing: -0.01em;
    }

    .favorite-button {
      flex: 0 0 auto;
      appearance: none;
      width: 32px;
      height: 32px;
      display: inline-grid;
      place-items: center;
      border: 1px solid rgba(0, 0, 0, 0.08);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.78);
      color: #b4b4bc;
      cursor: pointer;
      font-size: 15px;
      line-height: 1;
      transition: color 160ms ease, background 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }

    .favorite-button:hover {
      color: var(--gold);
      transform: translateY(-1px);
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
    }

    .favorite-button.active {
      color: #fff;
      background: linear-gradient(180deg, #ffd76a, #ff9f0a);
      border-color: rgba(255, 159, 10, 0.46);
      box-shadow: 0 10px 22px rgba(255, 159, 10, 0.22);
    }

    .detail-intro {
      margin: 8px 0 9px;
      color: var(--ink-soft);
      font-size: 12px;
      line-height: 1.66;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .research-note {
      margin: 8px 0 10px;
      padding: 9px 11px;
      border-radius: 14px;
      border: 1px solid rgba(0, 122, 255, 0.12);
      background: rgba(0, 122, 255, 0.055);
      color: var(--ink-soft);
      font-size: 12px;
      line-height: 1.58;
    }

    .research-note span {
      display: inline-block;
      margin-right: 7px;
      color: var(--accent-deep);
      font-weight: 700;
    }

    .research-note strong {
      color: var(--ink);
      font-weight: 500;
    }

    .detail-button {
      appearance: none;
      border: 1px solid rgba(0, 122, 255, 0.22);
      background: rgba(0, 122, 255, 0.08);
      color: var(--teal);
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 12px;
      cursor: pointer;
      transition: transform 120ms ease, background 120ms ease, border-color 120ms ease;
    }

    .detail-button:hover {
      transform: translateY(-1px);
      background: rgba(0, 122, 255, 0.14);
      border-color: rgba(0, 122, 255, 0.38);
    }

    .tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 999px;
      line-height: 1;
      border: 1px solid transparent;
    }

    .tag.key {
      background: rgba(0, 122, 255, 0.11);
      color: var(--accent-deep);
      border-color: rgba(0, 122, 255, 0.14);
    }

    .tag.level {
      background: rgba(0, 122, 255, 0.08);
      color: var(--teal);
      border-color: rgba(0, 122, 255, 0.12);
    }

    .tag.low {
      background: rgba(47, 118, 95, 0.11);
      color: #275f4d;
      border-color: rgba(47, 118, 95, 0.15);
    }

    .tag.mid {
      background: rgba(160, 111, 43, 0.11);
      color: #7d541e;
      border-color: rgba(160, 111, 43, 0.16);
    }

    .tag.high {
      background: rgba(255, 69, 58, 0.11);
      color: #b42318;
      border-color: rgba(255, 69, 58, 0.15);
    }

    .muted {
      color: var(--ink-soft);
      font-size: 12px;
    }

    .advice {
      font-weight: 600;
      color: var(--ink);
      margin-bottom: 5px;
    }

    .empty-state {
      display: none;
      padding: 56px 24px;
      min-height: 220px;
      text-align: center;
      color: var(--ink-soft);
      font-size: 14px;
      line-height: 1.8;
    }

    .table-shell.is-empty table {
      display: none;
    }

    .table-shell.is-empty .empty-state {
      display: block;
    }

    .pagination-bar {
      position: sticky;
      bottom: 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-top: 1px solid var(--line);
      background: rgba(248, 248, 251, 0.9);
      backdrop-filter: blur(18px);
    }

    .detail-overlay {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: grid;
      justify-items: end;
      background: rgba(29, 29, 31, 0.28);
      backdrop-filter: blur(12px);
      opacity: 0;
      pointer-events: none;
      transition: opacity 180ms ease;
    }

    .detail-overlay.is-open {
      opacity: 1;
      pointer-events: auto;
    }

    .detail-drawer {
      width: min(720px, 100vw);
      height: 100%;
      overflow: auto;
      padding: 26px;
      background:
        radial-gradient(circle at top right, rgba(90, 200, 250, 0.16), transparent 30%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(247, 248, 251, 0.96));
      border-left: 1px solid rgba(0, 0, 0, 0.08);
      box-shadow: -32px 0 70px rgba(0, 0, 0, 0.16);
      transform: translateX(24px);
      transition: transform 180ms ease;
    }

    .detail-overlay.is-open .detail-drawer {
      transform: translateX(0);
    }

    .drawer-top {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 18px;
    }

    .drawer-title h2 {
      font-size: 30px;
      line-height: 1.18;
      margin-top: 8px;
    }

    .drawer-close {
      appearance: none;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
      color: var(--ink);
      width: 40px;
      height: 40px;
      border-radius: 999px;
      cursor: pointer;
      font-size: 22px;
      line-height: 1;
    }

    .detail-grid {
      display: grid;
      gap: 14px;
    }

    .detail-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.72);
      padding: 16px;
    }

    .detail-card h3 {
      font-size: 16px;
      margin-bottom: 10px;
    }

    .detail-card p {
      white-space: pre-wrap;
      color: var(--ink-soft);
      font-size: 13px;
      line-height: 1.75;
    }

    .detail-fields {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .detail-field {
      padding: 10px 11px;
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.035);
    }

    .detail-field span {
      display: block;
      color: var(--ink-soft);
      font-size: 11px;
      margin-bottom: 4px;
    }

    .detail-field strong {
      display: block;
      font-size: 13px;
      line-height: 1.45;
      font-weight: 600;
      word-break: break-word;
    }

    .detail-link {
      display: inline-flex;
      margin-top: 10px;
      color: var(--teal);
      font-size: 13px;
      text-decoration: none;
      border-bottom: 1px solid rgba(44, 102, 108, 0.28);
    }

    .pagination-meta {
      font-size: 12px;
      color: var(--ink-soft);
      white-space: nowrap;
    }

    .pagination-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }

    .page-button {
      appearance: none;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.9);
      color: var(--ink);
      min-width: 38px;
      height: 34px;
      padding: 0 10px;
      border-radius: 999px;
      font-size: 12px;
      cursor: pointer;
      transition: all 120ms ease;
    }

    .page-button.active {
      background: var(--ink);
      border-color: var(--ink);
      color: #fff;
    }

    .page-button:disabled {
      opacity: 0.42;
      cursor: default;
    }

    .page-button:not(:disabled):hover {
      border-color: rgba(0, 122, 255, 0.38);
      transform: translateY(-1px);
    }

    @media (max-width: 1280px) {
      html,
      body {
        height: auto;
        overflow: auto;
      }

      .app-shell {
        grid-template-columns: 1fr;
        height: auto;
      }

      .map-stage,
      .workboard {
        min-height: auto;
        overflow: visible;
      }

      .map-stage {
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }

      .table-shell {
        max-height: 72vh;
      }

      .filter-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
    }

    @media (max-width: 860px) {
      .app-shell {
        width: min(100vw - 20px, 1540px);
        margin: 10px auto 16px;
      }

      .map-stage,
      .workboard {
        padding: 16px 16px 18px;
      }

      .stage-top,
      .board-top,
      .section-head,
      .result-meta,
      .pagination-bar {
        flex-direction: column;
        align-items: flex-start;
      }

      .metric-ribbon,
      .province-metrics,
      .filter-grid {
        grid-template-columns: 1fr;
      }

      .metric-ribbon article {
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }

      .metric-ribbon article:last-child {
        border-bottom: 0;
      }

      .map-frame {
        min-height: 360px;
      }

      .detail-drawer {
        padding: 18px;
      }

      .detail-fields {
        grid-template-columns: 1fr;
      }

      h1 {
        font-size: 30px;
      }

      h2 {
        font-size: 26px;
      }
    }
  </style>
</head>
<body>
  <main class="app-shell">
    <section class="map-stage">
      <div class="stage-top">
        <div>
          <div class="kicker">2026 博士生实践 / 地域参考</div>
          <h1>中国地域选择面板</h1>
          <p class="subtitle">以省级分布、需求规模和申请压力为主线，帮助你在 2026 博士生实践项目中快速收窄候选范围。</p>
        </div>
        <div class="stage-meta" id="stageMeta"></div>
      </div>

      <div class="metric-ribbon" id="metricRibbon"></div>

      <div class="section-head">
        <div>
          <h3>中国地域分布图</h3>
          <p>颜色越深，表示当前条件下该省承载的项目越多。</p>
        </div>
        <button id="clearProvinceBtn" class="ghost-button">清除省份筛选</button>
      </div>

      <div class="atlas-layout">
        <section class="map-panel">
          <div class="legend-row">
            <div class="legend-scale">
              <span>少</span>
              <div class="legend-gradient"></div>
              <span>多</span>
            </div>
            <span id="mapScopeLabel">地图当前显示全部项目</span>
          </div>
          <div class="map-frame" id="mapFrame">
            <div class="map-canvas">
              __SVG__
            </div>
            <div class="map-tooltip" id="mapTooltip" hidden></div>
          </div>
          <div class="map-footer">
            <span>列表保留全部数据；地图按当前筛选实时着色，仅显示已定位到省份的项目。</span>
            <span>底图来源：Wikimedia Commons 公有领域 SVG，本地离线重绘。</span>
          </div>
        </section>

        <section class="province-brief">
          <div class="province-hero" id="provinceHero"></div>
          <div class="province-ranking">
            <h4>当前筛选下优先关注的省份</h4>
            <div class="ranking-list" id="rankingList"></div>
          </div>
        </section>
      </div>
    </section>

    <section class="workboard">
      <div class="board-top">
        <div>
          <div class="kicker">项目筛选列表</div>
          <h2>按地域、竞争度和基地类型精筛</h2>
          <p class="board-subtitle">先用区域和省份收窄，再按需求、竞争度和基地类型比较候选项目。</p>
        </div>
        <div class="board-stamp" id="favoriteStamp"></div>
      </div>

      <section class="control-band">
        <div class="region-tabs" id="regionTabs"></div>

        <div class="filter-grid">
          <div class="filter-field">
            <label for="searchInput">关键词</label>
            <input id="searchInput" type="text" placeholder="搜索项目名称 / 院系专业 / 基地 / 省份" />
          </div>
          <div class="filter-field">
            <label for="provinceSelect">地域筛选</label>
            <select id="provinceSelect"></select>
          </div>
          <div class="filter-field">
            <label for="levelSelect">基地级别</label>
            <select id="levelSelect"></select>
          </div>
          <div class="filter-field">
            <label for="keySelect">项目范围</label>
            <select id="keySelect"></select>
          </div>
          <div class="filter-field">
            <label for="bandSelect">竞争度筛选</label>
            <select id="bandSelect"></select>
          </div>
          <div class="filter-field">
            <label for="sortSelect">竞争度排序 / 推荐</label>
            <select id="sortSelect"></select>
          </div>
        </div>

        <div class="result-meta">
          <div class="chips" id="activeChips"></div>
          <div class="result-count" id="resultCount"></div>
        </div>
      </section>

      <div class="table-shell" id="tableShell">
        <table>
          <thead>
            <tr>
              <th class="col-project">项目</th>
              <th class="col-location">地域</th>
              <th class="col-base">基地</th>
              <th class="col-num">需求</th>
              <th class="col-num">一志愿</th>
              <th class="col-num">总申请</th>
              <th class="col-num">竞争度</th>
              <th class="col-advice">参考</th>
            </tr>
          </thead>
          <tbody id="projectTable"></tbody>
        </table>
        <div class="empty-state">没有匹配结果，调整一下地域或竞争度条件。</div>
        <div class="pagination-bar" id="paginationBar"></div>
      </div>
    </section>
  </main>

  <aside class="detail-overlay" id="detailOverlay" aria-hidden="true">
    <section class="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="detailTitle">
      <div class="drawer-top">
        <div class="drawer-title" id="detailTitleBlock"></div>
        <button class="drawer-close" id="detailCloseBtn" aria-label="关闭详情">×</button>
      </div>
      <div class="detail-grid" id="detailBody"></div>
    </section>
  </aside>

  <script>
    const DATA = __DATA__;

    const state = {
      region: "全部区域",
      province: "",
      baseLevel: "全部级别",
      keyMode: "全部项目",
      competitionBand: "全部竞争度",
      sort: "机会评分",
      search: "",
      page: 1
    };

    const PAGE_SIZE = 60;
    const FAVORITES_KEY = "doctoral-practice-favorite-projects";
    let favorites = loadFavorites();
    let activeDetailId = null;

    const regionTabs = document.getElementById("regionTabs");
    const searchInput = document.getElementById("searchInput");
    const provinceSelect = document.getElementById("provinceSelect");
    const levelSelect = document.getElementById("levelSelect");
    const keySelect = document.getElementById("keySelect");
    const bandSelect = document.getElementById("bandSelect");
    const sortSelect = document.getElementById("sortSelect");
    const stageMeta = document.getElementById("stageMeta");
    const favoriteStamp = document.getElementById("favoriteStamp");
    const metricRibbon = document.getElementById("metricRibbon");
    const mapScopeLabel = document.getElementById("mapScopeLabel");
    const mapTooltip = document.getElementById("mapTooltip");
    const mapFrame = document.getElementById("mapFrame");
    const provinceHero = document.getElementById("provinceHero");
    const rankingList = document.getElementById("rankingList");
    const activeChips = document.getElementById("activeChips");
    const resultCount = document.getElementById("resultCount");
    const projectTable = document.getElementById("projectTable");
    const tableShell = document.getElementById("tableShell");
    const paginationBar = document.getElementById("paginationBar");
    const clearProvinceBtn = document.getElementById("clearProvinceBtn");
    const emptyState = tableShell.querySelector(".empty-state");
    const detailOverlay = document.getElementById("detailOverlay");
    const detailTitleBlock = document.getElementById("detailTitleBlock");
    const detailBody = document.getElementById("detailBody");
    const detailCloseBtn = document.getElementById("detailCloseBtn");

    const provinceLookup = DATA.provinceLookup;
    const provinceEntries = Object.entries(provinceLookup).sort((a, b) => a[1].order - b[1].order);
    const provinceElements = new Map();
    const scopeCache = new Map();
    const sortCache = new Map();
    const indexStore = buildIndexes(DATA.projects);
    let searchTimer = null;
    let currentView = {
      scopeKey: "",
      scopedProjects: [],
      visibleProjects: [],
      scopedStats: new Map(),
      sortedRows: [],
      pagedRows: [],
      totalPages: 1,
      pageStart: 0,
      unmatchedCount: 0
    };

    function formatNumber(value) {
      return Number(value).toLocaleString("zh-CN");
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>\"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function usefulText(value) {
      const text = String(value ?? "").trim();
      return text && !["无", "无。", "暂无", "暂无。"].includes(text) ? text : "";
    }

    function displayText(value, fallback = "未注明") {
      return usefulText(value) || fallback;
    }

    function loadFavorites() {
      try {
        const raw = localStorage.getItem(FAVORITES_KEY);
        const values = raw ? JSON.parse(raw) : [];
        return new Set(values.map((value) => Number(value)).filter(Number.isFinite));
      } catch (error) {
        console.warn("收藏数据读取失败，已使用空收藏列表。", error);
        return new Set();
      }
    }

    function saveFavorites() {
      try {
        localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
      } catch (error) {
        console.warn("收藏数据保存失败。", error);
      }
    }

    function isFavorite(projectId) {
      return favorites.has(Number(projectId));
    }

    function favoritesSignature() {
      return [...favorites].sort((a, b) => a - b).join(",");
    }

    function toggleFavorite(projectId) {
      const id = Number(projectId);
      if (!Number.isFinite(id)) return;
      if (favorites.has(id)) {
        favorites.delete(id);
      } else {
        favorites.add(id);
      }
      saveFavorites();
      scopeCache.clear();
      sortCache.clear();
      render();
      if (activeDetailId) openDetail(activeDetailId);
    }

    function renderDetailFields(items) {
      return `
        <div class="detail-fields">
          ${items.map(([label, value]) => `
            <div class="detail-field">
              <span>${escapeHtml(label)}</span>
              <strong>${escapeHtml(displayText(value))}</strong>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderDetailCard(title, value, fallback = "详情页未提供。") {
      return `
        <section class="detail-card">
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(displayText(value, fallback))}</p>
        </section>
      `;
    }

    function trimmedSearch() {
      return state.search.trim().toLowerCase();
    }

    function mixColor(a, b, t) {
      const ca = a.match(/\\w\\w/g).map((hex) => parseInt(hex, 16));
      const cb = b.match(/\\w\\w/g).map((hex) => parseInt(hex, 16));
      const mixed = ca.map((value, index) => Math.round(value + (cb[index] - value) * t));
      return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
    }

    function bandOf(project) {
      return project.competitionBand;
    }

    function addToIndex(map, key, id) {
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key).push(id);
    }

    function buildIndexes(projects) {
      const byId = new Map();
      const allIds = [];
      const byRegion = new Map();
      const byBaseLevel = new Map();
      const byCompetitionBand = new Map();
      const byProvince = new Map();
      const byKeyMode = new Map([
        ["仅重点项目", []],
        ["仅非重点项目", []]
      ]);

      projects.forEach((project) => {
        allIds.push(project.id);
        byId.set(project.id, project);
        addToIndex(byRegion, project.region, project.id);
        addToIndex(byBaseLevel, project.baseLevel, project.id);
        addToIndex(byCompetitionBand, project.competitionBand, project.id);
        addToIndex(byProvince, project.province, project.id);
        addToIndex(byKeyMode, project.isKey ? "仅重点项目" : "仅非重点项目", project.id);
      });

      return {
        byId,
        allIds,
        byRegion,
        byBaseLevel,
        byCompetitionBand,
        byProvince,
        byKeyMode
      };
    }

    function constrainCacheSize(cache, limit) {
      if (cache.size <= limit) return;
      cache.clear();
    }

    function scopeKeyOfState() {
      return JSON.stringify([
        state.region,
        state.baseLevel,
        state.keyMode,
        state.competitionBand,
        trimmedSearch(),
        state.keyMode === "仅收藏项目" ? favoritesSignature() : ""
      ]);
    }

    function resolveCandidateIds() {
      const buckets = [];
      if (state.region !== "全部区域") buckets.push(indexStore.byRegion.get(state.region) || []);
      if (state.baseLevel !== "全部级别") buckets.push(indexStore.byBaseLevel.get(state.baseLevel) || []);
      if (state.keyMode === "仅收藏项目") {
        buckets.push([...favorites]);
      } else if (state.keyMode !== "全部项目") {
        buckets.push(indexStore.byKeyMode.get(state.keyMode) || []);
      }
      if (state.competitionBand !== "全部竞争度") buckets.push(indexStore.byCompetitionBand.get(state.competitionBand) || []);
      if (!buckets.length) return indexStore.allIds;

      const orderedBuckets = [...buckets].sort((a, b) => a.length - b.length);
      let result = [...orderedBuckets[0]];

      for (let i = 1; i < orderedBuckets.length && result.length; i += 1) {
        const matcher = new Set(orderedBuckets[i]);
        result = result.filter((id) => matcher.has(id));
      }

      return result;
    }

    function getScopedView() {
      const scopeKey = scopeKeyOfState();
      const cachedView = scopeCache.get(scopeKey);
      if (cachedView) return cachedView;

      const scopedProjects = [];
      const keyword = trimmedSearch();
      let unmatchedCount = 0;

      resolveCandidateIds().forEach((id) => {
        const project = indexStore.byId.get(id);
        if (keyword && !project.searchText.includes(keyword)) return;
        scopedProjects.push(project);
        if (project.province === "未注明") unmatchedCount += 1;
      });

      const view = {
        key: scopeKey,
        scopedProjects,
        scopedStats: aggregateProvinceStats(scopedProjects),
        unmatchedCount
      };

      scopeCache.set(scopeKey, view);
      constrainCacheSize(scopeCache, 48);
      return view;
    }

    function getVisibleProjects(scopedProjects) {
      if (!state.province) return scopedProjects;
      return scopedProjects.filter((project) => project.province === state.province);
    }

    function getSortedRows(scopeKey, visibleProjects) {
      const cacheKey = `${scopeKey}::${state.province || "*"}::${state.sort}`;
      const cachedRows = sortCache.get(cacheKey);
      if (cachedRows) return cachedRows;
      const rows = sortProjects(visibleProjects);
      sortCache.set(cacheKey, rows);
      constrainCacheSize(sortCache, 96);
      return rows;
    }

    function aggregateProvinceStats(projects) {
      const aggregates = new Map();
      projects.forEach((project) => {
        if (!aggregates.has(project.province)) {
          const meta = provinceLookup[project.province] || {};
          aggregates.set(project.province, {
            province: project.province,
            short: meta.short || project.provinceShort,
            region: project.region,
            mapId: meta.code || "",
            projects: 0,
            keyProjects: 0,
            needTotal: 0,
            firstChoiceTotal: 0,
            applicantsTotal: 0,
            knownNeedTotal: 0,
            incompleteProjects: 0,
            lowCompetitionProjects: 0,
            avgCompetition: 0,
            score: 0
          });
        }
        const entry = aggregates.get(project.province);
        entry.projects += 1;
        entry.keyProjects += project.isKey ? 1 : 0;
        entry.needTotal += project.need;
        if (project.applicantDataComplete) {
          entry.firstChoiceTotal += project.firstChoice;
          entry.applicantsTotal += project.totalApplicants;
          entry.knownNeedTotal += project.need;
          entry.lowCompetitionProjects += project.competition <= 0.5 ? 1 : 0;
        } else {
          entry.incompleteProjects += 1;
        }
      });

      aggregates.forEach((entry) => {
        entry.avgCompetition = Number((entry.applicantsTotal / Math.max(entry.knownNeedTotal, 1)).toFixed(2));
        entry.score = Number((entry.needTotal * 2.2 + entry.keyProjects * 1.3 - entry.firstChoiceTotal * 1.45 - entry.avgCompetition * 6.4).toFixed(2));
      });

      return aggregates;
    }

    function sortProjects(projects) {
      return [...projects].sort((a, b) => {
        switch (state.sort) {
          case "竞争度从低到高":
            return Number(!a.applicantDataComplete) - Number(!b.applicantDataComplete) || a.competition - b.competition || b.need - a.need || a.firstChoice - b.firstChoice;
          case "竞争度从高到低":
            return Number(!a.applicantDataComplete) - Number(!b.applicantDataComplete) || b.competition - a.competition || b.totalApplicants - a.totalApplicants;
          case "需求人数从高到低":
            return b.need - a.need || Number(!a.applicantDataComplete) - Number(!b.applicantDataComplete) || a.competition - b.competition;
          case "第一志愿从低到高":
            return Number(!a.applicantDataComplete) - Number(!b.applicantDataComplete) || a.firstChoice - b.firstChoice || a.competition - b.competition;
          case "总申请数从低到高":
            return Number(!a.applicantDataComplete) - Number(!b.applicantDataComplete) || a.totalApplicants - b.totalApplicants || a.competition - b.competition;
          case "重点项目优先":
            return Number(b.isKey) - Number(a.isKey) || Number(!a.applicantDataComplete) - Number(!b.applicantDataComplete) || a.competition - b.competition || b.need - a.need;
          default:
            return b.opportunity - a.opportunity || a.competition - b.competition || b.need - a.need;
        }
      });
    }

    function recommendation(project) {
      if (!project.applicantDataComplete) return "申请数据不完整，需回源确认";
      if (project.need >= 5 && project.competition <= 0.4) return "高需求、低压力";
      if (project.competition <= 0.5) return "申请压力较小";
      if (project.firstPressure <= 0.5) return "一志愿压力可控";
      if (project.isKey && project.need >= 2) return "重点项目，可保留";
      return "结合兴趣与地域再判断";
    }

    function levelTag(project) {
      if (!project.applicantDataComplete) return "mid";
      if (project.competition <= 0.5) return "low";
      if (project.competition <= 1.0) return "mid";
      return "high";
    }

    function firstChoiceLabel(project) {
      return project.applicantDataStatus === "申请数缺失" ? "未知" : String(project.firstChoice);
    }

    function totalApplicantsLabel(project) {
      if (project.applicantDataStatus === "申请数缺失") return "未知";
      if (project.applicantDataStatus === "第四志愿缺失") return `≥${project.totalApplicants}`;
      return String(project.totalApplicants);
    }

    function competitionLabel(project) {
      if (project.applicantDataStatus === "申请数缺失") return "未知";
      if (project.applicantDataStatus === "第四志愿缺失") return `≥${project.competition.toFixed(2)}`;
      return project.competition.toFixed(2);
    }

    function firstPressureLabel(project) {
      return project.applicantDataStatus === "申请数缺失" ? "未知" : project.firstPressure.toFixed(2);
    }

    function renderStageMeta(scopeView) {
      stageMeta.innerHTML = `
        <span class="meta-pill">总项目 ${formatNumber(DATA.summary.totalProjects)}</span>
        <span class="meta-pill">详情 ${formatNumber(DATA.summary.detailProjects)} 条</span>
        <span class="meta-pill">当前未定位 ${formatNumber(scopeView.unmatchedCount)}</span>
      `;
    }

    function renderFavoriteStamp() {
      favoriteStamp.innerHTML = `
        <span>${formatNumber(favorites.size)} 个收藏</span>
      `;
    }

    function renderMetricRibbon(visibleProjects) {
      const totalNeed = visibleProjects.reduce((sum, project) => sum + project.need, 0);
      const completeProjects = visibleProjects.filter((project) => project.applicantDataComplete);
      const knownNeed = completeProjects.reduce((sum, project) => sum + project.need, 0);
      const totalApplicants = completeProjects.reduce((sum, project) => sum + project.totalApplicants, 0);
      const avgCompetition = completeProjects.length ? (totalApplicants / Math.max(knownNeed, 1)).toFixed(2) : "无";
      const lowCompetition = completeProjects.filter((project) => project.competition <= 0.5).length;
      const incompleteCount = visibleProjects.length - completeProjects.length;

      metricRibbon.innerHTML = `
        <article>
          <span>当前匹配项目数</span>
          <strong>${formatNumber(visibleProjects.length)}</strong>
          <small>列表和地图联动后的结果数量</small>
        </article>
        <article>
          <span>需求总人数</span>
          <strong>${formatNumber(totalNeed)}</strong>
          <small>适合先筛高需求项目</small>
        </article>
        <article>
          <span>已知平均竞争度</span>
          <strong>${avgCompetition}</strong>
          <small>仅使用申请数完整项目计算</small>
        </article>
        <article>
          <span>低竞争 / 待确认</span>
          <strong>${formatNumber(lowCompetition)}</strong>
          <small>申请数不完整 ${formatNumber(incompleteCount)} 项</small>
        </article>
      `;
    }

    function paintProvince(node, fill, stroke, opacity) {
      const paths = node.tagName.toLowerCase() === "path" ? [node] : Array.from(node.querySelectorAll("path"));
      paths.forEach((path) => {
        path.style.fill = fill;
        path.style.stroke = stroke;
        path.style.strokeWidth = stroke === "#1d1d1f" ? "1.5" : "1";
        path.style.opacity = opacity;
      });
      node.style.cursor = "pointer";
    }

    function renderMap(scopedStats) {
      const mappedStats = [...scopedStats.values()].filter((item) => item.mapId);
      const maxProjects = Math.max(...mappedStats.map((item) => item.projects), 1);

      provinceEntries.forEach(([province, meta]) => {
        const node = provinceElements.get(meta.code);
        if (!node) return;
        const stats = scopedStats.get(province);
        const t = stats ? Math.sqrt(stats.projects / maxProjects) : 0;
        const baseFill = stats ? mixColor("eef5ff", "0066cc", t) : "rgb(237, 241, 246)";
        const dimmed = state.region !== "全部区域" && meta.region !== state.region;
        const selected = state.province === province;
        const fill = selected ? "rgb(0, 122, 255)" : baseFill;
        const stroke = selected ? "#1d1d1f" : "rgba(29, 29, 31, 0.62)";
        const opacity = dimmed ? 0.22 : 1;

        paintProvince(node, fill, stroke, opacity);
      });

      mapScopeLabel.textContent = state.region === "全部区域"
        ? "地图当前显示全部区域"
        : `地图当前聚焦 ${state.region}`;
    }

    function showTooltip(event, province, stats) {
      const rect = mapFrame.getBoundingClientRect();
      const left = Math.min(event.clientX - rect.left + 14, rect.width - 190);
      const top = Math.max(event.clientY - rect.top + 14, 12);
      const body = stats
        ? `
            <strong>${escapeHtml(province)}</strong>
            <div>项目数：${formatNumber(stats.projects)}</div>
            <div>需求人数：${formatNumber(stats.needTotal)}</div>
            <div>已知平均竞争度：${stats.avgCompetition.toFixed(2)}</div>
            <div>申请数待确认：${formatNumber(stats.incompleteProjects)}</div>
            <div>重点项目：${formatNumber(stats.keyProjects)}</div>
          `
        : `
            <strong>${escapeHtml(province)}</strong>
            <div>当前筛选下没有匹配项目</div>
          `;
      mapTooltip.innerHTML = body;
      mapTooltip.hidden = false;
      mapTooltip.style.left = `${left}px`;
      mapTooltip.style.top = `${top}px`;
    }

    function hideTooltip() {
      mapTooltip.hidden = true;
    }

    function renderPagination(totalRows) {
      if (totalRows === 0) {
        paginationBar.innerHTML = "";
        return;
      }

      const start = currentView.pageStart + 1;
      const end = currentView.pageStart + currentView.pagedRows.length;
      const pages = new Set([1, currentView.totalPages, state.page - 1, state.page, state.page + 1]);
      const pageList = [...pages].filter((page) => page >= 1 && page <= currentView.totalPages).sort((a, b) => a - b);

      paginationBar.innerHTML = `
        <div class="pagination-meta">显示 ${formatNumber(start)}-${formatNumber(end)} / ${formatNumber(totalRows)} 条</div>
        <div class="pagination-actions">
          <button class="page-button" data-page="${state.page - 1}" ${state.page === 1 ? "disabled" : ""}>上一页</button>
          ${pageList.map((page) => `
            <button class="page-button ${page === state.page ? "active" : ""}" data-page="${page}">${page}</button>
          `).join("")}
          <button class="page-button" data-page="${state.page + 1}" ${state.page === currentView.totalPages ? "disabled" : ""}>下一页</button>
        </div>
      `;
    }

    function bestProvince(scopedStats) {
      return [...scopedStats.values()].sort((a, b) => b.score - a.score || b.projects - a.projects)[0];
    }

    function renderProvinceHero(scopedProjects, visibleProjects, scopedStats) {
      let targetProvince = state.province;
      if (!targetProvince) {
        targetProvince = bestProvince(scopedStats)?.province || "";
      }

      if (!targetProvince) {
        provinceHero.innerHTML = "<p class='province-summary'>当前没有可展示的省份摘要。</p>";
        return;
      }

      const stats = scopedStats.get(targetProvince);
      const meta = provinceLookup[targetProvince] || {};
      const candidateProjects = sortProjects(
        (state.province ? visibleProjects : scopedProjects).filter((project) => project.province === targetProvince)
      ).slice(0, 3);

      if (!stats) {
        provinceHero.innerHTML = `
          <div class="province-title">
            <h3>${escapeHtml(targetProvince)}</h3>
            <span>当前筛选下无匹配项目</span>
          </div>
          <p class="province-summary">这个地域仍然保留在下拉筛选里，但当前区域、级别或竞争度条件下没有可用项目。</p>
        `;
        return;
      }

      provinceHero.innerHTML = `
        <div class="province-title">
          <h3>${escapeHtml(targetProvince)}</h3>
          <span>${escapeHtml(meta.region || stats.region)} · ${formatNumber(stats.projects)} 个项目</span>
        </div>
        <p class="province-summary">需求人数 ${formatNumber(stats.needTotal)}，已知平均竞争度 ${stats.avgCompetition.toFixed(2)}，申请数待确认 ${formatNumber(stats.incompleteProjects)} 项。${state.province ? "这是你当前点选的省份。" : "这是当前筛选下机会评分最高的省份。"} </p>
        <div class="province-metrics">
          <div><span>需求人数</span><strong>${formatNumber(stats.needTotal)}</strong></div>
          <div><span>一志愿</span><strong>${formatNumber(stats.firstChoiceTotal)}</strong></div>
          <div><span>低竞争项目</span><strong>${formatNumber(stats.lowCompetitionProjects)}</strong></div>
          <div><span>重点项目</span><strong>${formatNumber(stats.keyProjects)}</strong></div>
        </div>
        <ul class="focus-projects">
          ${candidateProjects.map((project) => `
            <li>
              <strong>${escapeHtml(project.name)}</strong>
              <span>${escapeHtml(project.baseName)} · 需求 ${project.need} · 竞争度 ${competitionLabel(project)} · ${escapeHtml(recommendation(project))}</span>
            </li>
          `).join("")}
        </ul>
      `;
    }

    function renderRanking(scopedStats) {
      const list = [...scopedStats.values()]
        .filter((item) => item.projects > 0)
        .sort((a, b) => b.score - a.score || b.projects - a.projects)
        .slice(0, 6);
      if (!list.length) {
        rankingList.innerHTML = "<div class='muted'>当前筛选下暂无可比较的省份。</div>";
        return;
      }
      const maxScore = Math.max(...list.map((item) => item.score), 1);

      rankingList.innerHTML = list.map((item) => `
        <div class="ranking-item">
          <strong>${escapeHtml(item.province)}</strong>
          <div class="ranking-track"><i style="width:${Math.max(18, (item.score / maxScore) * 100)}%"></i></div>
          <span>${formatNumber(item.projects)} 项</span>
        </div>
      `).join("");
    }

    function initialiseRegionTabs() {
      regionTabs.innerHTML = DATA.regionOrder.map((region) => `
        <button class="region-tab ${state.region === region ? "active" : ""}" data-region="${region}">${region}</button>
      `).join("");

      regionTabs.addEventListener("click", (event) => {
        const button = event.target.closest(".region-tab");
        if (!button) return;
        state.region = button.dataset.region;
        state.page = 1;
        if (state.province) {
          const provinceRegion = provinceLookup[state.province]?.region || "未分区";
          if (state.region !== "全部区域" && provinceRegion !== state.region) {
            state.province = "";
            provinceSelect.value = "";
          }
        }
        render();
      });
    }

    function syncRegionTabs() {
      regionTabs.querySelectorAll(".region-tab").forEach((button) => {
        button.classList.toggle("active", button.dataset.region === state.region);
      });
    }

    function syncClearProvinceButton() {
      clearProvinceBtn.disabled = !state.province;
    }

    function renderChips(visibleProjects) {
      const chips = [`<span class="chip"><strong>${formatNumber(visibleProjects.length)}</strong> 条匹配结果</span>`];
      if (state.region !== "全部区域") chips.push(`<span class="chip">区域 <strong>${escapeHtml(state.region)}</strong></span>`);
      if (state.province) chips.push(`<span class="chip">省份 <strong>${escapeHtml(state.province)}</strong></span>`);
      if (state.baseLevel !== "全部级别") chips.push(`<span class="chip">基地 <strong>${escapeHtml(state.baseLevel)}</strong></span>`);
      if (state.keyMode !== "全部项目") chips.push(`<span class="chip">范围 <strong>${escapeHtml(state.keyMode)}</strong></span>`);
      if (state.competitionBand !== "全部竞争度") chips.push(`<span class="chip">竞争度 <strong>${escapeHtml(state.competitionBand)}</strong></span>`);
      if (state.search.trim()) chips.push(`<span class="chip">搜索 <strong>${escapeHtml(state.search.trim())}</strong></span>`);
      activeChips.innerHTML = chips.join("");
    }

    function renderResultCount(visibleProjects, scopedProjects) {
      if (state.province) {
        resultCount.textContent = `当前省份 ${formatNumber(visibleProjects.length)} 条；省份外同条件项目 ${formatNumber(scopedProjects.length - visibleProjects.length)} 条`;
        return;
      }
      resultCount.textContent = `当前筛选共 ${formatNumber(visibleProjects.length)} 条`;
    }

    function renderTable(totalRows) {
      const rows = currentView.pagedRows;
      tableShell.classList.toggle("is-empty", totalRows.length === 0);
      if (!rows.length) {
        emptyState.innerHTML = state.province
          ? `当前锁定省份 <strong>${escapeHtml(state.province)}</strong> 在现有条件下没有项目，可清除省份筛选后查看同条件其他地域。`
          : state.search.trim()
            ? "没有命中当前关键词，可换一个关键词，或放宽基地级别与竞争度条件。"
            : "没有匹配结果，调整一下地域或竞争度条件。";
      }
      projectTable.innerHTML = rows.map((project) => `
        <tr>
          <td class="col-project">
            <div class="project-title-row">
              <div class="project-name">${escapeHtml(project.name)}</div>
              <button class="favorite-button ${isFavorite(project.id) ? "active" : ""}" data-favorite-id="${project.id}" type="button" aria-label="${isFavorite(project.id) ? "取消收藏" : "收藏项目"}" aria-pressed="${isFavorite(project.id) ? "true" : "false"}">★</button>
            </div>
            <div class="detail-intro">${escapeHtml(project.detail?.intro || "详情页未提供有效介绍。")}</div>
            ${usefulText(project.detail?.researchDirection) ? `
              <div class="research-note">
                <span>院系/专业</span><strong>${escapeHtml(project.detail.researchDirection)}</strong>
              </div>
            ` : ""}
            <div class="tag-row">
              ${project.isKey ? '<span class="tag key">重点项目</span>' : ""}
              <span class="tag level">${escapeHtml(project.baseLevel)}</span>
              <span class="tag ${levelTag(project)}">${escapeHtml(bandOf(project))}</span>
              <button class="detail-button" data-detail-id="${project.id}" type="button">查看详情</button>
            </div>
          </td>
          <td class="col-location">
            <div>${escapeHtml(project.province)}</div>
            <div class="muted">${escapeHtml(project.region)}</div>
          </td>
          <td class="col-base">
            <div>${escapeHtml(project.baseName)}</div>
            <div class="muted">${escapeHtml(project.baseLevel)}</div>
          </td>
          <td class="col-num">${project.need}</td>
          <td class="col-num">${firstChoiceLabel(project)}</td>
          <td class="col-num">${totalApplicantsLabel(project)}</td>
          <td class="col-num">
            <div>${competitionLabel(project)}</div>
            <div class="muted">一志愿比 ${firstPressureLabel(project)}</div>
          </td>
          <td class="col-advice">
            <div class="advice">${escapeHtml(recommendation(project))}</div>
            <div class="muted">${escapeHtml(project.note || "无额外备注")}</div>
          </td>
        </tr>
      `).join("");
      renderPagination(totalRows.length);
    }

    function openDetail(projectId) {
      const project = indexStore.byId.get(Number(projectId));
      if (!project) return;
      activeDetailId = project.id;
      const detail = project.detail || {};
      detailTitleBlock.innerHTML = `
        <div class="kicker">项目详情 · #${project.id}</div>
        <div class="project-title-row">
          <h2>${escapeHtml(project.name)}</h2>
          <button class="favorite-button ${isFavorite(project.id) ? "active" : ""}" data-favorite-id="${project.id}" type="button" aria-label="${isFavorite(project.id) ? "取消收藏" : "收藏项目"}" aria-pressed="${isFavorite(project.id) ? "true" : "false"}">★</button>
        </div>
        <p class="board-subtitle">${escapeHtml(detail.intro || "详情页未提供有效介绍。")}</p>
      `;
      detailBody.innerHTML = `
        <section class="detail-card">
          <h3>基本信息</h3>
          ${renderDetailFields([
            ["项目编号", detail.projectCode],
            ["基地编号", detail.baseCode],
            ["所属基地", detail.baseName || project.baseName],
            ["院系/专业要求", detail.researchDirection],
            ["预计工作量", detail.workloadDays],
            ["是否重点", detail.isKeyText || (project.isKey ? "是" : "否")],
            ["需求人数", project.need],
            ["申请数据", project.applicantDataStatus],
            ["竞争度", competitionLabel(project)]
          ])}
        </section>
        <section class="detail-card">
          <h3>单位信息</h3>
          ${renderDetailFields([
            ["单位名称", detail.unitName],
            ["单位省市", detail.unitProvince || project.province],
            ["单位区县", detail.unitDistrict],
            ["单位地址", detail.unitAddress]
          ])}
          ${detail.url ? `<a class="detail-link" href="${escapeHtml(detail.url)}" target="_blank" rel="noreferrer">打开原始详情页</a>` : ""}
        </section>
        ${renderDetailCard("项目背景", detail.background)}
        ${renderDetailCard("项目目标", detail.goal)}
        ${renderDetailCard("需要解决的关键技术问题", detail.keyProblem)}
        ${renderDetailCard("所需准备工作", detail.preparation)}
        ${renderDetailCard("现有条件", detail.existingCondition)}
        ${renderDetailCard("时间安排", detail.schedule)}
      `;
      detailOverlay.classList.add("is-open");
      detailOverlay.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      detailCloseBtn.focus();
    }

    function closeDetail() {
      detailOverlay.classList.remove("is-open");
      detailOverlay.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      activeDetailId = null;
    }

    function applyProvinceSelection(nextProvince) {
      state.province = nextProvince;
      provinceSelect.value = nextProvince;
      if (nextProvince && state.region !== "全部区域") {
        const provinceRegion = provinceLookup[nextProvince]?.region || "未分区";
        if (provinceRegion !== state.region) {
          state.region = provinceRegion;
        }
      }
    }

    function initialiseControls() {
      provinceSelect.innerHTML = [
        '<option value="">全部省份 / 未限定</option>',
        ...DATA.provinceOptions.map((province) => `<option value="${province}">${province}</option>`)
      ].join("");

      levelSelect.innerHTML = [
        "全部级别",
        ...new Set(DATA.projects.map((project) => project.baseLevel))
      ].map((value) => `<option value="${value}">${value}</option>`).join("");

      keySelect.innerHTML = ["全部项目", "仅收藏项目", "仅重点项目", "仅非重点项目"]
        .map((value) => `<option value="${value}">${value}</option>`).join("");

      bandSelect.innerHTML = ["全部竞争度", "低竞争", "中竞争", "高竞争", "申请数不完整"]
        .map((value) => `<option value="${value}">${value}</option>`).join("");

      sortSelect.innerHTML = [
        "机会评分",
        "竞争度从低到高",
        "竞争度从高到低",
        "需求人数从高到低",
        "第一志愿从低到高",
        "总申请数从低到高",
        "重点项目优先"
      ].map((value) => `<option value="${value}">${value}</option>`).join("");

      initialiseRegionTabs();

      searchInput.addEventListener("input", (event) => {
        state.search = event.target.value;
        state.page = 1;
        clearTimeout(searchTimer);
        searchTimer = setTimeout(render, 120);
      });

      provinceSelect.addEventListener("change", (event) => {
        applyProvinceSelection(event.target.value);
        state.page = 1;
        render();
      });

      levelSelect.addEventListener("change", (event) => {
        state.baseLevel = event.target.value;
        state.page = 1;
        render();
      });

      keySelect.addEventListener("change", (event) => {
        state.keyMode = event.target.value;
        state.page = 1;
        render();
      });

      bandSelect.addEventListener("change", (event) => {
        state.competitionBand = event.target.value;
        state.page = 1;
        render();
      });

      sortSelect.addEventListener("change", (event) => {
        state.sort = event.target.value;
        state.page = 1;
        render();
      });

      clearProvinceBtn.addEventListener("click", () => {
        applyProvinceSelection("");
        state.page = 1;
        render();
      });

      paginationBar.addEventListener("click", (event) => {
        const button = event.target.closest("[data-page]");
        if (!button || button.disabled) return;
        const page = Number(button.dataset.page);
        if (!page || page === state.page || page < 1 || page > currentView.totalPages) return;
        state.page = page;
        render();
      });

      document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-favorite-id]");
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        toggleFavorite(button.dataset.favoriteId);
      });

      projectTable.addEventListener("click", (event) => {
        const button = event.target.closest("[data-detail-id]");
        if (!button) return;
        openDetail(button.dataset.detailId);
      });

      detailCloseBtn.addEventListener("click", closeDetail);
      detailOverlay.addEventListener("click", (event) => {
        if (event.target === detailOverlay) closeDetail();
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && detailOverlay.classList.contains("is-open")) {
          closeDetail();
        }
      });
    }

    function initialiseMapNodes() {
      const svg = document.querySelector(".china-map-svg");
      provinceEntries.forEach(([province, meta]) => {
        const node = svg.querySelector(`#${meta.code}`);
        if (!node) return;
        provinceElements.set(meta.code, node);
        node.setAttribute("tabindex", "0");
        node.setAttribute("role", "button");
        node.addEventListener("mouseenter", (event) => {
          showTooltip(event, province, currentView.scopedStats.get(province));
        });
        node.addEventListener("mousemove", (event) => {
          showTooltip(event, province, currentView.scopedStats.get(province));
        });
        node.addEventListener("mouseleave", hideTooltip);
        node.addEventListener("click", () => {
          applyProvinceSelection(state.province === province ? "" : province);
          state.page = 1;
          render();
        });
        node.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          applyProvinceSelection(state.province === province ? "" : province);
          state.page = 1;
          render();
        });
      });
      mapFrame.addEventListener("mouseleave", hideTooltip);
    }

    function render() {
      const scopeView = getScopedView();
      const visibleProjects = getVisibleProjects(scopeView.scopedProjects);
      const sortedRows = getSortedRows(scopeView.key, visibleProjects);
      const totalPages = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE));
      if (state.page > totalPages) state.page = totalPages;
      const pageStart = (state.page - 1) * PAGE_SIZE;
      const pagedRows = sortedRows.slice(pageStart, pageStart + PAGE_SIZE);

      currentView = {
        scopeKey: scopeView.key,
        scopedProjects: scopeView.scopedProjects,
        visibleProjects,
        scopedStats: scopeView.scopedStats,
        sortedRows,
        pagedRows,
        totalPages,
        pageStart,
        unmatchedCount: scopeView.unmatchedCount
      };

      renderStageMeta(scopeView);
      renderFavoriteStamp();
      renderMetricRibbon(visibleProjects);
      syncRegionTabs();
      syncClearProvinceButton();
      renderMap(scopeView.scopedStats);
      renderProvinceHero(scopeView.scopedProjects, visibleProjects, scopeView.scopedStats);
      renderRanking(scopeView.scopedStats);
      renderChips(visibleProjects);
      renderResultCount(visibleProjects, scopeView.scopedProjects);
      renderTable(sortedRows);
    }

    initialiseControls();
    initialiseMapNodes();
    render();
  </script>
</body>
</html>
"""


def main() -> None:
    projects, summary = normalize_rows()
    payload = build_payload(projects, summary)
    HTML_PATH.write_text(build_html(payload), encoding="utf-8")
    print(HTML_PATH)


if __name__ == "__main__":
    main()
