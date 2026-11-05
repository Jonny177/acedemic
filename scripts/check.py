#!/usr/bin/env python3
"""Validate the generated academic site without third-party dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SLUGS = ("initial-ends", "vanishing-order", "biharmonic-landis")
MANUSCRIPTS = (
    "Initial_Ends",
    "Vanishing_Order_Biharmonic",
    "Biharmonic_Landis",
)
EXPECTED_HTML = ("index.html", "drafts/index.html") + tuple(
    f"drafts/{slug}/index.html" for slug in SLUGS
)
AI_PATTERN = re.compile(r"\bAI[\s\-\u2010-\u2015]+generated\b|AI\s*生成", re.I)
AUTHOR_UNSPECIFIED = re.compile(
    r"\bauthors?\b.{0,100}?(?:not\s+specified|not\s+provided|unspecified|not\s+stated)",
    re.I,
)
PLACEHOLDER_PATTERN = re.compile(
    r"example\.invalid|\[\s*authors?\s*\]|\bauthor name\b|email@example\.com",
    re.I,
)


@dataclass
class Page:
    path: Path
    ids: set[str] = field(default_factory=set)
    duplicate_ids: list[str] = field(default_factory=list)
    links: list[tuple[str, str, int]] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    citation_authors: list[str] = field(default_factory=list)
    json_ld: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


class PageParser(HTMLParser):
    def __init__(self, page: Page):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.skip_depth = 0
        self.json_ld_depth = 0
        self.json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self.skip_depth:
            if tag in {"script", "style", "template"}:
                self.skip_depth += 1
            return
        if tag in {"script", "style", "template"}:
            self.skip_depth = 1
            if tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
                self.json_ld_depth = 1
                self.json_ld_parts = []
        element_id = attributes.get("id")
        if element_id:
            if element_id in self.page.ids:
                self.page.duplicate_ids.append(element_id)
            self.page.ids.add(element_id)
        if tag == "a" and attributes.get("name"):
            self.page.ids.add(attributes["name"])
        for attribute in ("href", "src"):
            if attributes.get(attribute) is not None:
                self.page.links.append((attribute, attributes[attribute], self.getpos()[0]))
        if tag == "meta" and attributes.get("name", "").lower() in {
            "citation_author", "dc.creator", "dc.creator.personalname", "prism.author"
        }:
            value = attributes.get("content", "").strip()
            if value:
                self.page.citation_authors.append(value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in {"script", "style", "template"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth and tag in {"script", "style", "template"}:
            self.skip_depth -= 1
            if self.json_ld_depth and tag == "script":
                self.page.json_ld.append("".join(self.json_ld_parts))
                self.json_ld_depth = 0

    def handle_data(self, data: str) -> None:
        if self.json_ld_depth:
            self.json_ld_parts.append(data)
        if not self.skip_depth:
            self.page.text_parts.append(data)


def has_scholarly_author(value: object) -> bool:
    if isinstance(value, dict):
        item_types = value.get("@type", [])
        if isinstance(item_types, str):
            item_types = [item_types]
        if "ScholarlyArticle" in item_types and value.get("author"):
            return True
        return any(has_scholarly_author(item) for item in value.values())
    if isinstance(value, list):
        return any(has_scholarly_author(item) for item in value)
    return False


def main() -> int:
    errors: list[str] = []
    if not SITE.is_dir():
        print("FAIL: site/ does not exist. Run python scripts/build.py first.")
        return 1

    site_root = SITE.resolve()
    for relative in EXPECTED_HTML:
        if not (SITE / relative).is_file():
            errors.append(f"Missing required page: {relative}")

    pages: dict[Path, Page] = {}
    for path in sorted(SITE.rglob("*.html")):
        page = Page(path.resolve())
        parser = PageParser(page)
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read HTML {path.relative_to(SITE)}: {exc}")
            continue
        pages[page.path] = page
        for duplicate in page.duplicate_ids:
            errors.append(f"Duplicate id in {path.relative_to(SITE)}: {duplicate}")
        if PLACEHOLDER_PATTERN.search(page.text):
            errors.append(f"Visible placeholder in {path.relative_to(SITE)}")

    local_link_count = 0
    external_link_count = 0
    fragment_count = 0
    for page in pages.values():
        source_name = page.path.relative_to(site_root)
        for attribute, value, line in page.links:
            context = f"{source_name}:{line} {attribute}={value!r}"
            if PLACEHOLDER_PATTERN.search(value):
                errors.append(f"Placeholder URL: {context}")
                continue
            try:
                parts = urlsplit(value)
            except ValueError as exc:
                errors.append(f"Invalid URL ({exc}): {context}")
                continue
            if parts.scheme or parts.netloc:
                if parts.scheme.lower() not in {"", "http", "https", "mailto", "tel", "data"}:
                    errors.append(f"Unsupported URL scheme: {context}")
                external_link_count += 1
                continue
            local_link_count += 1
            decoded_path = unquote(parts.path)
            if decoded_path.startswith("/") or "\\" in decoded_path:
                errors.append(f"Use a relative URL for /academic/ and local preview: {context}")
                continue
            candidate = (page.path.parent / decoded_path).resolve() if decoded_path else page.path
            try:
                candidate.relative_to(site_root)
            except ValueError:
                errors.append(f"Local link escapes site/: {context}")
                continue
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.is_file():
                errors.append(f"Missing local target: {context}")
                continue
            fragment = unquote(parts.fragment)
            if fragment and candidate.suffix.lower() == ".html":
                fragment_count += 1
                target = pages.get(candidate.resolve())
                if target is None or fragment not in target.ids:
                    errors.append(f"Missing HTML anchor #{fragment}: {context}")

    checked_ai_pages = 0
    for relative in EXPECTED_HTML:
        page = pages.get((SITE / relative).resolve())
        if page is None:
            continue
        if not AI_PATTERN.search(page.text):
            errors.append(f"AI-generated status is not visible on {relative}")
        elif not re.search(r"\bdrafts?\b|草稿", page.text, re.I):
            errors.append(f"Draft status is not visible on {relative}")
        else:
            checked_ai_pages += 1

    for slug in SLUGS:
        relative = f"drafts/{slug}/index.html"
        page = pages.get((SITE / relative).resolve())
        if page is None:
            continue
        if not AUTHOR_UNSPECIFIED.search(page.text):
            errors.append(f"Missing source-author attribution notice on {relative}")
        if page.citation_authors:
            errors.append(f"Unsubstantiated manuscript author metadata on {relative}")
        for encoded in page.json_ld:
            try:
                payload = json.loads(encoded)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSON-LD on {relative}: {exc}")
                continue
            if has_scholarly_author(payload):
                errors.append(f"Unsubstantiated ScholarlyArticle author on {relative}")

    download_count = 0
    for stem in MANUSCRIPTS:
        for extension in ("pdf", "tex"):
            relative = Path("files") / f"{stem}.{extension}"
            target = SITE / relative
            source = ROOT / "static" / relative
            if not target.is_file() or not source.is_file():
                errors.append(f"Missing source or generated download: {relative}")
                continue
            generated_bytes = target.read_bytes()
            source_bytes = source.read_bytes()
            if not generated_bytes:
                errors.append(f"Empty download: {relative}")
            elif hashlib.sha256(generated_bytes).digest() != hashlib.sha256(source_bytes).digest():
                errors.append(f"Download differs from supplied static file: {relative}")
            elif extension == "pdf" and not generated_bytes.startswith(b"%PDF-"):
                errors.append(f"Invalid PDF header: {relative}")
            elif extension == "tex" and b"\\begin{document}" not in generated_bytes:
                errors.append(f"LaTeX document marker missing: {relative}")
            else:
                download_count += 1

    if not (SITE / ".nojekyll").is_file():
        errors.append("Missing site/.nojekyll for direct static publication")

    if errors:
        print(f"FAIL: {len(errors)} issue(s)")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS: generated academic site checks")
    print(f"  HTML pages: {len(pages)} (including all {len(EXPECTED_HTML)} required pages)")
    print(f"  Local links/assets: {local_link_count}; HTML fragments: {fragment_count}")
    print(f"  External URLs: {external_link_count} (syntax classified; not fetched)")
    print(f"  Original downloads: {download_count}/6 byte-identical")
    print(f"  Visible AI/draft notices: {checked_ai_pages}/{len(EXPECTED_HTML)} pages")
    print("  Source-author notices: 3/3; no invented manuscript-author metadata")
    print("  Publication path: relative URLs; .nojekyll present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
