"""Build an original, compact API index from JoinQuant's public help pages.

The output stores names, short labels, signatures, and source links rather than
redistributing the full official documentation.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent
BASE = "https://www.joinquant.com/help/api/help"
CONTENT = "https://www.joinquant.com/help/api/getContent"
SEEDS = ["api", "Stock", "Future", "fund", "index", "JQData", "optimizer", "faq"]
HEADING = re.compile(r"^h[1-6]$")
CALL = re.compile(r"(?:^|\n)\s*(?:[\w.]+\s*=\s*)?([A-Za-z_][\w.]*)\s*\(")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def compact_signature(value: str, fallback: str) -> str:
    value = clean(value)
    match = CALL.search(value)
    if not match:
        return ""
    start = match.start(1)
    depth = 0
    end = len(value)
    for pos in range(value.find("(", start), len(value)):
        if value[pos] == "(":
            depth += 1
        elif value[pos] == ")":
            depth -= 1
            if depth == 0:
                end = pos + 1
                break
    signature = value[start:end]
    return signature[:360] + ("…" if len(signature) > 360 else "")


def snapshot_signature(title: str, value: str) -> str:
    """Extract a declaration or call from an already collected code block."""
    candidates = re.findall(r"[A-Za-z_][\w.]*", title)
    for name in candidates:
        if len(name) < 3:
            continue
        match = re.search(r"\b" + re.escape(name) + r"\s*\(", value)
        if match:
            return compact_signature(value[match.start():], title)
    return compact_signature(value, title)


def heading_context(tag: Tag) -> tuple[str, str]:
    section = tag.find_previous("h3")
    chapter = tag.find_previous("h2")
    return (clean(chapter.get_text(" ", strip=True)) if chapter else "",
            clean(section.get_text(" ", strip=True)) if section else "")


def heading_blocks(heading: Tag):
    level = int(heading.name[1])
    for item in heading.next_siblings:
        if not isinstance(item, Tag):
            continue
        if HEADING.match(item.name or "") and int(item.name[1]) <= level:
            break
        yield item


def get_entries(name: str, soup: BeautifulSoup) -> list[dict]:
    source = f"{BASE}?name={name}"
    entries = []
    for group in soup.select("section .group"):
        labels = group.find_all("label", recursive=False)
        if len(labels) < 2:
            continue
        title = clean(labels[0].get_text(" ", strip=True))
        purpose = clean(labels[1].get_text(" ", strip=True))
        article = group.find("article", recursive=False)
        code = article.find("code") if article else None
        chapter, section = heading_context(group)
        signature = compact_signature(code.get_text(" ", strip=True), title) if code else ""
        entries.append(dict(page=name, chapter=chapter, section=section,
                            name=title, purpose=purpose, signature=signature,
                            source=source, kind="documented entry"))

    for heading in soup.find_all(HEADING):
        if heading.name not in {"h3", "h4", "h5"} or heading.find_parent("section"):
            continue
        blocks = list(heading_blocks(heading))
        code = next((c for b in blocks[:12] for c in b.find_all("code")
                     if c.find_parent("pre") and CALL.search(c.get_text(" ", strip=True))), None)
        if not code:
            continue
        signature = compact_signature(code.get_text(" ", strip=True), "")
        if not signature:
            continue
        title = clean(heading.get_text(" ", strip=True))
        chapter, section = heading_context(heading)
        if section == title:
            section = ""
        entries.append(dict(page=name, chapter=chapter, section=section,
                            name=signature.split("(", 1)[0], purpose=title,
                            signature=signature, source=source, kind="function"))
    return entries


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--snapshot":
        snapshot = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        pages, entries, topics = [], [], []
        for page in snapshot:
            name = page["name"]
            source = f"{BASE}?name={name}"
            headings = [clean(title) for level, title in page["headings"] if level in {"h2", "h3", "h4"}]
            pages.append(dict(name=name, url=source, sections=headings,
                              entry_count=len(page["groups"])))
            for level, title in page["headings"]:
                if level in {"h2", "h3", "h4"}:
                    topics.append(dict(page=name, level=level, title=clean(title), source=source))
            for group in page["groups"]:
                title = clean(group["title"])
                raw_signature = group["signature"]
                signature = snapshot_signature(title, raw_signature) if raw_signature else ""
                entries.append(dict(page=name, name=title,
                                    purpose=clean(group["summary"])[:120],
                                    signature=signature, source=source,
                                    kind="function" if signature else "topic"))
        output = dict(title="聚宽 API 接口大全", generated_at=datetime.now(timezone.utc).isoformat(),
                      official_entry_url=f"{BASE}#name:api", pages=pages,
                      entries=entries, topics=topics)
        (ROOT / "catalog.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"TOTAL: {len(entries)} entries, {len(topics)} topics across {len(pages)} pages")
        return

    session = requests.Session()
    queue = SEEDS[:]
    seen = set()
    pages = []
    entries = []
    topics = []
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        response = session.get(CONTENT, params={"name": name}, timeout=60)
        response.raise_for_status()
        data = response.json().get("data") or ""
        soup = BeautifulSoup(data, "html.parser")
        headings = [clean(h.get_text(" ", strip=True)) for h in soup.find_all(HEADING)
                    if h.name in {"h2", "h3", "h4"}]
        topics.extend(dict(page=name, level=h.name,
                           title=clean(h.get_text(" ", strip=True)),
                           source=f"{BASE}?name={name}")
                      for h in soup.find_all(HEADING) if h.name in {"h2", "h3", "h4"})
        for a in soup.find_all("a", href=True):
            url = urljoin(BASE, a["href"])
            if "/help/api/help" in url:
                child = parse_qs(urlsplit(url).query).get("name", [None])[0]
                if child and child not in seen and child not in queue:
                    queue.append(child)
        page_entries = get_entries(name, soup)
        pages.append(dict(name=name, url=f"{BASE}?name={name}",
                          sections=headings, entry_count=len(page_entries)))
        entries.extend(page_entries)
        print(f"{name}: {len(page_entries)} entries", flush=True)

    # An entry may be in both an HTML heading and a group on the same page.
    unique = {}
    for entry in entries:
        key = (entry["page"], entry["name"], entry["signature"])
        unique.setdefault(key, entry)
    output = dict(title="聚宽 API 接口大全", generated_at=datetime.now(timezone.utc).isoformat(),
                  official_entry_url=f"{BASE}#name:api", pages=pages,
                  entries=list(unique.values()), topics=topics)
    (ROOT / "catalog.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"TOTAL: {len(output['entries'])} entries across {len(pages)} pages")


if __name__ == "__main__":
    main()
