#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import random
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin


EDGE_APP = "Microsoft Edge"
BASE_URL = (
    "https://webvpn.tsinghua.edu.cn/"
    "http/77726476706e69737468656265737421e4ff52942e3a615170469dbf915b243ddde8bbb91b1c7df56e/"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use the live Microsoft Edge session to serially save project detail HTML pages."
    )
    parser.add_argument("index_html", type=Path, help="Saved local index HTML file")
    parser.add_argument("output_dir", type=Path, help="Directory to save detail HTML files into")
    parser.add_argument("--count", type=int, default=100, help="Number of detail pages to save")
    parser.add_argument("--offset", type=int, default=0, help="Start offset into the extracted detail links")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional manifest JSON path. Defaults to <output_dir>/manifest.json",
    )
    parser.add_argument("--min-delay", type=float, default=2.8, help="Minimum delay between pages")
    parser.add_argument("--max-delay", type=float, default=5.4, help="Maximum delay between pages")
    parser.add_argument("--pause-every-min", type=int, default=7, help="Minimum pages between longer pauses")
    parser.add_argument("--pause-every-max", type=int, default=13, help="Maximum pages between longer pauses")
    parser.add_argument("--pause-min", type=float, default=10.0, help="Minimum longer pause duration")
    parser.add_argument("--pause-max", type=float, default=24.0, help="Maximum longer pause duration")
    parser.add_argument("--item-retries", type=int, default=3, help="Retries per page before marking as failed")
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Log failures and continue the batch instead of stopping on the first failure",
    )
    parser.add_argument(
        "--failure-log",
        type=Path,
        default=None,
        help="Optional failure log JSON path. Defaults to <output_dir>/failures.json",
    )
    return parser.parse_args()


def clean_title(raw: str) -> str:
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.startswith("重点"):
        text = text[2:].strip()
    return text


def normalize_for_match(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def safe_name(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120] or "untitled"


def extract_detail_links(index_html: Path) -> list[dict[str, str]]:
    source = index_html.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        r'<a class="tit" onclick="[^"]*window\.open\(&quot;(?P<path>/f/xs/xmsq/view/[^&]+)&quot;\)[^"]*">(?P<title>.*?)</a>',
        re.S,
    )
    seen: set[str] = set()
    results: list[dict[str, str]] = []
    for match in pattern.finditer(source):
        rel_path = html.unescape(match.group("path")).strip()
        title = clean_title(match.group("title"))
        if rel_path in seen:
            continue
        seen.add(rel_path)
        results.append(
            {
                "path": rel_path,
                "url": urljoin(BASE_URL, rel_path.lstrip("/")),
                "title": title,
            }
        )
    return results


def run_osascript(script: str) -> str:
    proc = subprocess.run(
        ["osascript", "-"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "osascript failed")
    return proc.stdout


def apple_window_exists() -> bool:
    script = f'''
tell application "{EDGE_APP}"
    return (count of windows) > 0
end tell
'''
    return run_osascript(script).strip().lower() == "true"


def set_edge_url(url: str) -> None:
    script = f'''
tell application "{EDGE_APP}"
    activate
    if (count of windows) is 0 then make new window
    set URL of active tab of front window to "{url}"
end tell
'''
    run_osascript(script)


def get_edge_title(retries: int = 6, retry_delay: float = 0.6) -> str:
    script = f'''
tell application "{EDGE_APP}"
    if (count of windows) is 0 then error "Edge has no open window"
    return title of active tab of front window
end tell
'''
    last_error: RuntimeError | None = None
    for _ in range(retries):
        try:
            return run_osascript(script).strip()
        except RuntimeError as exc:
            last_error = exc
            time.sleep(retry_delay)
    raise last_error or RuntimeError("Could not read Edge title")


def get_edge_html(retries: int = 6, retry_delay: float = 0.6) -> str:
    script = f'''
tell application "{EDGE_APP}"
    if (count of windows) is 0 then error "Edge has no open window"
    return execute active tab of front window javascript "document.documentElement.outerHTML"
end tell
'''
    last_error: RuntimeError | None = None
    for _ in range(retries):
        try:
            return run_osascript(script)
        except RuntimeError as exc:
            last_error = exc
            time.sleep(retry_delay)
    raise last_error or RuntimeError("Could not read Edge HTML")


def wait_for_detail_page(expected_title: str, timeout_s: float = 30.0) -> tuple[str, str]:
    start = time.time()
    last_title = ""
    normalized_expected = normalize_for_match(expected_title)
    while time.time() - start < timeout_s:
        time.sleep(0.8)
        last_title = get_edge_title()
        try:
            html_text = get_edge_html()
        except RuntimeError:
            continue
        normalized_html = normalize_for_match(html_text)
        if (
            "项目背景" in html_text
            and "项目目标" in html_text
            and "所属基地名称" in html_text
            and normalized_expected in normalized_html
        ):
            return last_title, html_text
    raise TimeoutError(f"Timed out waiting for detail page. Last title: {last_title!r}")


def save_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_row(rows: list[dict[str, object]], row: dict[str, object]) -> None:
    for index, existing in enumerate(rows):
        if existing.get("seq") == row.get("seq"):
            rows[index] = row
            return
    rows.append(row)


def next_pause_threshold(current_seq: int, low: int, high: int) -> int:
    return current_seq + random.randint(low, high)


def main() -> int:
    args = parse_args()
    if args.min_delay <= 0 or args.max_delay <= 0 or args.min_delay > args.max_delay:
        raise SystemExit("Delay values are invalid")
    if args.pause_every_min <= 0 or args.pause_every_max < args.pause_every_min:
        raise SystemExit("Pause cadence values are invalid")
    if args.pause_min <= 0 or args.pause_max < args.pause_min:
        raise SystemExit("Pause duration values are invalid")

    all_links = extract_detail_links(args.index_html)
    if not all_links:
        raise SystemExit("No detail links found in the saved index HTML")

    selected = all_links[args.offset : args.offset + args.count]
    if not selected:
        raise SystemExit("The requested slice is empty")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest or (args.output_dir / "manifest.json")
    failure_log_path = args.failure_log or (args.output_dir / "failures.json")
    manifest_rows: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    if manifest_path.exists():
        try:
            manifest_rows = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest_rows = []
    if failure_log_path.exists():
        try:
            failure_rows = json.loads(failure_log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failure_rows = []
    pause_after_seq = next_pause_threshold(args.offset + 1, args.pause_every_min, args.pause_every_max)

    for index, item in enumerate(selected, start=1):
        seq = args.offset + index
        last_error = ""
        saved = False
        for attempt in range(1, args.item_retries + 1):
            try:
                set_edge_url(item["url"])
                page_title, html_text = wait_for_detail_page(item["title"])
                filename = f"{seq:03d}_{safe_name(item['title'])}.html"
                file_path = args.output_dir / filename
                file_path.write_text(html_text, encoding="utf-8")
                upsert_row(
                    manifest_rows,
                    {
                        "seq": seq,
                        "title": item["title"],
                        "url": item["url"],
                        "pageTitle": page_title,
                        "file": str(file_path),
                    },
                )
                save_manifest(manifest_path, manifest_rows)
                print(
                    f"[{seq:03d}/{args.offset + len(selected):03d}] saved {file_path.name}"
                    + (f" (attempt {attempt})" if attempt > 1 else ""),
                    flush=True,
                )
                time.sleep(random.uniform(args.min_delay, args.max_delay))
                saved = True
                break
            except Exception as exc:
                last_error = str(exc)
                print(f"[warn] item {seq:03d} attempt {attempt} failed: {last_error}", flush=True)
                time.sleep(random.uniform(args.min_delay, args.max_delay) + attempt)

        if not saved:
            upsert_row(
                failure_rows,
                {
                    "seq": seq,
                    "title": item["title"],
                    "url": item["url"],
                    "error": last_error,
                },
            )
            save_manifest(failure_log_path, failure_rows)
            if not args.continue_on_failure:
                raise RuntimeError(f"Failed to save item {seq:03d}: {last_error}")
            print(f"[skip] item {seq:03d} logged to {failure_log_path.name}", flush=True)
        if seq >= pause_after_seq and seq < args.offset + len(selected):
            long_pause = random.uniform(args.pause_min, args.pause_max)
            print(f"[pause] sleeping {long_pause:.1f}s after item {seq:03d}", flush=True)
            time.sleep(long_pause)
            pause_after_seq = next_pause_threshold(seq + 1, args.pause_every_min, args.pause_every_max)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
