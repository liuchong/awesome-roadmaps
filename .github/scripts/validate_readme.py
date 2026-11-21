"""Validate README.md structure, sorting, URLs, and badge conventions."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

ENTRY_RE = re.compile(
    r"^- \[(?P<title>[^\]]+)\]\((?P<url>[^)\s]+)\) - (?P<desc>.+?)(?P<badges>(?: <img [^>]+>)+)$"
)
IMG_RE = re.compile(
    r'^<img alt="(?P<alt>[^"]+)" src="https://img\.shields\.io/badge/(?P<spec>[^"]+)">$'
)
YEAR_SPEC_RE = re.compile(r"^Year-(?P<year>\d{4})-(?P<color>[a-z]+)$")

ALLOWED_TYPE_SPECS = {
    "GitHub-Repo-181717?logo=github",
    "Format-Website-0A66C2",
    "Format-Course-0A66C2",
    "Format-Book-6F42C1",
    "Format-PDF-B30B00?logo=adobeacrobatreader&logoColor=white",
    "Blog-Article-0A66C2",
    "Medium-Article-000000?logo=medium",
    "Type-Tool-0A66C2",
    "Status-Archived-6e7781",
}

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "fbclid",
    "gclid",
}


def expected_year_color(year: int) -> str:
    if year >= 2026:
        return "brightgreen"
    if year >= 2024:
        return "green"
    if year >= 2021:
        return "yellowgreen"
    return "yellow"


def github_heading_slug(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = slug.replace(" ", "-")
    return slug


def validate_readme_text(text: str, repo_root: pathlib.Path | None = None) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()

    if repo_root is not None:
        for asset in re.findall(r'<img\s+src="([^":]+)"', text):
            asset_path = repo_root / asset
            if not asset_path.is_file():
                errors.append(f"Missing local asset referenced in README: {asset}")
            elif asset_path.suffix.lower() == ".svg":
                try:
                    ET.parse(asset_path)
                except ET.ParseError as exc:
                    errors.append(f"Invalid SVG XML in {asset}: {exc}")

    toc_entries: list[tuple[str, str]] = []
    sections: list[tuple[str, int, list[tuple[int, str]]]] = []
    cur_heading: str | None = None
    cur_line = 0
    cur_body: list[tuple[int, str]] = []

    for lineno, line in enumerate(lines, 1):
        if line.startswith("## "):
            if cur_heading is not None:
                sections.append((cur_heading, cur_line, cur_body))
            cur_heading = line[3:].strip()
            cur_line = lineno
            cur_body = []
        elif cur_heading is not None:
            cur_body.append((lineno, line))

    if cur_heading is not None:
        sections.append((cur_heading, cur_line, cur_body))

    if not sections or sections[0][0] != "Contents":
        errors.append("First level-2 heading must be '## Contents'.")
        return errors
    if sections[-1][0] != "License":
        errors.append("Last level-2 heading must be '## License'.")
        return errors

    for lineno, line in sections[0][2]:
        if not line.strip():
            continue
        m = re.match(r"^- \[([^\]]+)\]\(#([^)]+)\)$", line)
        if not m:
            errors.append(f"L{lineno}: Invalid Contents entry: {line}")
            continue
        toc_entries.append((m.group(1), m.group(2)))

    content_sections = sections[1:-1]
    expected_toc = [(h, github_heading_slug(h)) for h, _, _ in content_sections]
    if toc_entries != expected_toc:
        errors.append(f"Contents TOC mismatch: got {toc_entries}, expected {expected_toc}")

    seen_urls: dict[str, int] = {}

    for heading, sec_lineno, body in content_sections:
        titles: list[tuple[int, str]] = []
        entry_count = 0
        for lineno, line in body:
            if not line.strip():
                continue
            if not line.startswith("- "):
                errors.append(f"L{lineno} [{heading}]: Unexpected non-item line: {line}")
                continue
            m = ENTRY_RE.match(line)
            if not m:
                errors.append(
                    f"L{lineno} [{heading}]: Entry must match '- [Title](https://...) - Description. <badges>': {line}"
                )
                continue

            entry_count += 1
            title = m.group("title")
            url = m.group("url")
            desc = m.group("desc")
            badges_raw = m.group("badges").strip()

            titles.append((lineno, title))

            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"L{lineno} [{heading}]: URL must use https://: {url}")
            query_keys = {k.lower() for k, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)}
            bad_params = sorted(query_keys & TRACKING_PARAMS)
            if bad_params:
                errors.append(f"L{lineno} [{heading}]: Tracking parameters {bad_params} not allowed in {url}")

            norm_url = url.rstrip("/")
            if norm_url in seen_urls:
                errors.append(
                    f"L{lineno} [{heading}]: Duplicate URL {url} (already listed on L{seen_urls[norm_url]})"
                )
            else:
                seen_urls[norm_url] = lineno

            if not desc[0].isupper():
                errors.append(f"L{lineno} [{heading}]: Description must start with an uppercase character: {desc}")
            if not desc.endswith("."):
                errors.append(f"L{lineno} [{heading}]: Description must end with a period: {desc}")

            badge_tokens = re.findall(r"<img [^>]+>", badges_raw)
            if " ".join(badge_tokens) != badges_raw:
                errors.append(f"L{lineno} [{heading}]: Badges must be separated by single spaces: {badges_raw}")

            has_type_badge = False
            saw_non_year = False
            saw_format_badge = False
            for idx, tok in enumerate(badge_tokens):
                im = IMG_RE.match(tok)
                if not im:
                    errors.append(f"L{lineno} [{heading}]: Invalid shields.io badge tag: {tok}")
                    continue
                alt = im.group("alt")
                spec = im.group("spec")
                ym = YEAR_SPEC_RE.match(spec)
                if ym:
                    if idx != 0 or saw_non_year:
                        errors.append(f"L{lineno} [{heading}]: Year badge must appear first: {tok}")
                    year = int(ym.group("year"))
                    color = ym.group("color")
                    exp_color = expected_year_color(year)
                    if alt != f"Year {year}":
                        errors.append(f"L{lineno} [{heading}]: Year badge alt must be 'Year {year}', got '{alt}'")
                    if color != exp_color:
                        errors.append(
                            f"L{lineno} [{heading}]: Year {year} badge must use color '{exp_color}', got '{color}'"
                        )
                else:
                    saw_non_year = True
                    has_type_badge = True
                    if spec not in ALLOWED_TYPE_SPECS:
                        errors.append(f"L{lineno} [{heading}]: Unrecognized type/status badge '{spec}'")
                    if spec.startswith("Format-"):
                        saw_format_badge = True
                    if spec.startswith("GitHub-Repo-") and saw_format_badge:
                        errors.append(
                            f"L{lineno} [{heading}]: GitHub-Repo badge must precede Format-* badges"
                        )

            if not has_type_badge:
                errors.append(f"L{lineno} [{heading}]: At least one type/status badge is required")

        if entry_count == 0:
            errors.append(f"L{sec_lineno} [{heading}]: Section must contain at least one roadmap entry")

        raw_names = [t for _, t in titles]
        sorted_names = sorted(raw_names, key=lambda s: s.lower())
        if raw_names != sorted_names:
            errors.append(
                f"L{sec_lineno} [{heading}]: Entries are not sorted alphabetically: {raw_names} != {sorted_names}"
            )

    return errors


FORBIDDEN_DOCS_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}


def validate_docs_paths(rel_paths: list[str]) -> list[str]:
    errors: list[str] = []
    path_set = set(rel_paths)
    if "index.html" not in path_set:
        errors.append("docs/index.html entry point is missing")
    for p in sorted(rel_paths):
        parts = p.split("/")
        if len(parts) == 1:
            if parts[0] not in {"index.html", "CNAME"}:
                errors.append(f"Unexpected file in docs/ root (must live under docs/pages/): docs/{p}")
        elif parts[0] != "pages":
            errors.append(f"Unexpected subdirectory under docs/ (must live under docs/pages/): docs/{p}")
        suffix = pathlib.PurePosixPath(p).suffix.lower()
        if suffix in FORBIDDEN_DOCS_SUFFIXES:
            errors.append(f"Precompiled or handwritten JS/TS is not allowed under docs/: docs/{p}")
    if not any(p.startswith("pages/") and p.endswith(".eli") for p in rel_paths):
        errors.append("Expected at least one Eliscript (.eli) source file under docs/pages/")
    return errors


def validate_docs_layout(repo_root: pathlib.Path) -> list[str]:
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        return []
    rel_paths = [
        p.relative_to(docs_dir).as_posix()
        for p in docs_dir.rglob("*")
        if p.is_file()
    ]
    errors = validate_docs_paths(rel_paths)
    for rel in rel_paths:
        if rel.endswith(".svg"):
            try:
                ET.parse(docs_dir / rel)
            except ET.ParseError as exc:
                errors.append(f"Invalid SVG XML in docs/{rel}: {exc}")
    return errors


def run_self_tests() -> None:
    valid_doc = """# Awesome Roadmaps

## Contents

- [Web Development](#web-development)

## Web Development
- [Alpha Roadmap](https://github.com/example/alpha) - Alpha learning roadmap. <img alt="Year 2026" src="https://img.shields.io/badge/Year-2026-brightgreen"> <img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-Repo-181717?logo=github"> <img alt="Interactive website" src="https://img.shields.io/badge/Format-Website-0A66C2">
- [Beta Roadmap](https://example.com/beta) - Beta learning article. <img alt="Year 2022" src="https://img.shields.io/badge/Year-2022-yellowgreen"> <img alt="Blog article" src="https://img.shields.io/badge/Blog-Article-0A66C2">

## License

License text.
"""
    assert validate_readme_text(valid_doc) == [], f"Expected valid doc to pass: {validate_readme_text(valid_doc)}"

    # 1. Unsorted entries must fail
    unsorted_doc = valid_doc.replace("Alpha Roadmap", "Zeta Roadmap")
    assert any("not sorted alphabetically" in e for e in validate_readme_text(unsorted_doc))

    # 2. Tracking query parameters must fail
    utm_doc = valid_doc.replace("https://example.com/beta", "https://example.com/beta?utm_source=github")
    assert any("Tracking parameters" in e for e in validate_readme_text(utm_doc))

    # 3. Duplicate URLs (including trailing slash normalization) must fail
    dupe_doc = valid_doc.replace("https://example.com/beta", "https://github.com/example/alpha/")
    assert any("Duplicate URL" in e for e in validate_readme_text(dupe_doc))

    # 4. Wrong year badge color must fail
    color_doc = valid_doc.replace("Year-2022-yellowgreen", "Year-2022-green")
    assert any("must use color 'yellowgreen'" in e for e in validate_readme_text(color_doc))

    # 5. Badge ordering (Format before GitHub-Repo) must fail
    order_doc = valid_doc.replace(
        '<img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-Repo-181717?logo=github"> <img alt="Interactive website" src="https://img.shields.io/badge/Format-Website-0A66C2">',
        '<img alt="Interactive website" src="https://img.shields.io/badge/Format-Website-0A66C2"> <img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-Repo-181717?logo=github">',
    )
    assert any("GitHub-Repo badge must precede Format-*" in e for e in validate_readme_text(order_doc))

    # 6. Missing trailing period must fail
    period_doc = valid_doc.replace("Beta learning article.", "Beta learning article")
    assert any("must end with a period" in e for e in validate_readme_text(period_doc))

    # 7. Valid docs/ Pages layout passes; stray root files or precompiled JS fail
    valid_docs = ["index.html", "CNAME", "pages/app.eli", "pages/styles.css", "pages/logo.svg"]
    assert validate_docs_paths(valid_docs) == []
    assert any("not allowed under docs/" in e for e in validate_docs_paths(valid_docs + ["pages/app.mjs"]))
    assert any("Unexpected file in docs/ root" in e for e in validate_docs_paths(valid_docs + ["styles.css"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readme",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[2] / "README.md",
        help="Path to README.md",
    )
    parser.add_argument("--self-test", action="store_true", help="Run built-in unit self-tests")
    args = parser.parse_args()

    if args.self_test:
        run_self_tests()
        print("Self-tests passed.")

    readme_path = args.readme.resolve()
    text = readme_path.read_text(encoding="utf-8")
    errors = validate_readme_text(text, repo_root=readme_path.parent)
    errors.extend(validate_docs_layout(readme_path.parent))
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    entry_count = sum(1 for line in text.splitlines() if ENTRY_RE.match(line))
    print(f"OK: {readme_path.name} passed validation ({entry_count} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
