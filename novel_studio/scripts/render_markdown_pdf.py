#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


def build_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    base_font = "STSong-Light"

    body = ParagraphStyle(
        "GuideBody",
        parent=styles["BodyText"],
        fontName=base_font,
        fontSize=10.5,
        leading=16,
        textColor=colors.HexColor("#222222"),
        alignment=TA_LEFT,
        spaceAfter=3,
    )
    heading1 = ParagraphStyle(
        "GuideHeading1",
        parent=styles["Heading1"],
        fontName=base_font,
        fontSize=20,
        leading=26,
        textColor=colors.HexColor("#111111"),
        spaceAfter=10,
        spaceBefore=4,
    )
    heading2 = ParagraphStyle(
        "GuideHeading2",
        parent=styles["Heading2"],
        fontName=base_font,
        fontSize=15.5,
        leading=22,
        textColor=colors.HexColor("#111111"),
        spaceBefore=8,
        spaceAfter=6,
    )
    heading3 = ParagraphStyle(
        "GuideHeading3",
        parent=styles["Heading3"],
        fontName=base_font,
        fontSize=12.5,
        leading=18,
        textColor=colors.HexColor("#222222"),
        spaceBefore=6,
        spaceAfter=5,
    )
    list_style = ParagraphStyle(
        "GuideList",
        parent=body,
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=0,
    )
    return {
        "body": body,
        "heading1": heading1,
        "heading2": heading2,
        "heading3": heading3,
        "list": list_style,
    }


def format_inline(text: str) -> str:
    parts: list[str] = []
    token_re = re.compile(r"(`[^`]+`|\*\*.+?\*\*)")
    cursor = 0

    for match in token_re.finditer(text):
        if match.start() > cursor:
            parts.append(html.escape(text[cursor : match.start()]))

        token = match.group(0)
        if token.startswith("`") and token.endswith("`"):
            # Keep backticks literal and stay on the CJK-capable font.
            parts.append(html.escape(token))
        elif token.startswith("**") and token.endswith("**"):
            parts.append(f"<b>{html.escape(token[2:-2])}</b>")
        else:
            parts.append(html.escape(token))
        cursor = match.end()

    if cursor < len(text):
        parts.append(html.escape(text[cursor:]))
    return "".join(parts)


def flush_paragraph(paragraph_lines: list[str], story: list, styles: dict[str, ParagraphStyle]) -> None:
    if not paragraph_lines:
        return
    text = " ".join(line.strip() for line in paragraph_lines).strip()
    if not text:
        return
    story.append(Paragraph(format_inline(text), styles["body"]))
    story.append(Spacer(1, 2.2 * mm))
    paragraph_lines.clear()


def flush_list(items: list[str], story: list, styles: dict[str, ParagraphStyle], ordered: bool) -> None:
    if not items:
        return
    flowable_items = [
        ListItem(Paragraph(format_inline(item.strip()), styles["list"])) for item in items if item.strip()
    ]
    if not flowable_items:
        items.clear()
        return
    bullet_type = "1" if ordered else "bullet"
    story.append(
        ListFlowable(
            flowable_items,
            bulletType=bullet_type,
            start="1",
            leftIndent=10 * mm,
            bulletFontName=styles["body"].fontName,
            bulletFontSize=styles["body"].fontSize,
        )
    )
    story.append(Spacer(1, 2.2 * mm))
    items.clear()


def markdown_to_story(markdown_text: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    ordered_items: list[str] = []

    bullet_re = re.compile(r"^\s*-\s+(.+)$")
    ordered_re = re.compile(r"^\s*\d+\.\s+(.+)$")

    def flush_all() -> None:
        flush_paragraph(paragraph_lines, story, styles)
        flush_list(list_items, story, styles, ordered=False)
        flush_list(ordered_items, story, styles, ordered=True)

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_all()
            continue

        heading_level = 0
        if stripped.startswith("### "):
            heading_level = 3
        elif stripped.startswith("## "):
            heading_level = 2
        elif stripped.startswith("# "):
            heading_level = 1
        if heading_level:
            flush_all()
            text = stripped[(heading_level + 1) :]
            story.append(Paragraph(format_inline(text), styles[f"heading{heading_level}"]))
            continue

        bullet_match = bullet_re.match(line)
        if bullet_match:
            flush_paragraph(paragraph_lines, story, styles)
            flush_list(ordered_items, story, styles, ordered=True)
            list_items.append(bullet_match.group(1))
            continue

        ordered_match = ordered_re.match(line)
        if ordered_match:
            flush_paragraph(paragraph_lines, story, styles)
            flush_list(list_items, story, styles, ordered=False)
            ordered_items.append(ordered_match.group(1))
            continue

        flush_list(list_items, story, styles, ordered=False)
        flush_list(ordered_items, story, styles, ordered=True)
        paragraph_lines.append(stripped)

    flush_all()
    return story


def render_pdf(input_path: Path, output_path: Path) -> None:
    styles = build_styles()
    markdown_text = input_path.read_text(encoding="utf-8")
    story = markdown_to_story(markdown_text, styles)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=input_path.stem,
        author="NovelStudio",
    )
    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Markdown guide to PDF with Chinese-safe fonts.")
    parser.add_argument("input", help="Input markdown path")
    parser.add_argument("output", help="Output pdf path")
    args = parser.parse_args()
    render_pdf(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
