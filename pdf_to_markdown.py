#!/usr/bin/env python3
"""
Convert a PDF book to Markdown using PyMuPDF (fitz).

Primary strategy:
- Extract text page-by-page with PyMuPDF.
- Reconstruct readable paragraphs/lists/headings with heuristics.
- Use PDF bookmarks (TOC) to improve heading structure where possible.
- Insert image placeholders and page separators.
- Mark OCR-required pages when text is not extractable, with optional OCR fallback.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
from statistics import median
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    print(
        "Error: PyMuPDF is not installed.\n"
        "Install it with: pip install pymupdf",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


DEFAULT_PDF_PATH = r"C:\Users\drago\Downloads\23things.pdf"
PAGE_SEPARATOR = "\n\n---\n\n"

BULLET_RE = re.compile(r"^\s*([•◦▪●◉○\-–—*])\s+(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\(?\d+[\.\)]|[A-Za-z][\.\)])\s+(.*)$")
WHITESPACE_RE = re.compile(r"\s+")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
TABLE_SPLIT_RE = re.compile(r"\s{2,}|\t+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a PDF to Markdown using PyMuPDF."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=DEFAULT_PDF_PATH,
        help=f"Path to input PDF (default: {DEFAULT_PDF_PATH})",
    )
    parser.add_argument(
        "--ocr-needed",
        action="store_true",
        help="Run OCR only for pages with no extractable text.",
    )
    parser.add_argument(
        "--ocr-lang",
        default="eng",
        help="Tesseract language code for optional OCR (default: eng).",
    )
    parser.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Optional full path to tesseract executable.",
    )
    return parser.parse_args()


def normalize_spaces(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.strip())


def cleanup_markdown(md_text: str) -> str:
    md_text = md_text.replace("\r\n", "\n").replace("\r", "\n")
    md_text = MULTI_BLANK_RE.sub("\n\n", md_text)
    return md_text.strip()


def get_output_path(pdf_path: Path) -> Path:
    return pdf_path.with_suffix(".md")


def build_toc_map(doc: fitz.Document) -> dict[int, list[tuple[int, str]]]:
    toc_map: dict[int, list[tuple[int, str]]] = {}
    try:
        toc = doc.get_toc(simple=True)  # [level, title, page_number]
    except Exception:
        return toc_map

    for item in toc:
        if len(item) < 3:
            continue
        level, title, page_no = item[0], item[1], item[2]
        if not isinstance(page_no, int) or page_no < 1:
            continue
        clean_title = normalize_spaces(str(title))
        if not clean_title:
            continue
        toc_map.setdefault(page_no, []).append((max(1, min(6, int(level))), clean_title))
    return toc_map


def estimate_body_font_size(doc: fitz.Document, max_samples: int = 40) -> float:
    total_pages = len(doc)
    if total_pages == 0:
        return 11.0

    step = max(1, total_pages // max_samples)
    page_indexes = list(range(0, total_pages, step))[:max_samples]
    samples: list[float] = []

    for index in page_indexes:
        try:
            page = doc[index]
            d = page.get_text("dict")
        except Exception:
            continue
        for block in d.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = float(span.get("size", 0.0) or 0.0)
                    if not text or size <= 0:
                        continue
                    weight = max(1, min(8, len(text) // 20 + 1))
                    samples.extend([round(size, 1)] * weight)

    if not samples:
        return 11.0

    return float(median(samples))


def rects_overlap(a: fitz.Rect, b: fitz.Rect) -> bool:
    return a.intersects(b)


def extract_tables(page: fitz.Page) -> list[dict[str, Any]]:
    tables_out: list[dict[str, Any]] = []
    try:
        finder = page.find_tables()
    except Exception:
        return tables_out

    tables = getattr(finder, "tables", None)
    if not tables:
        return tables_out

    for table in tables:
        try:
            rows = table.extract() or []
        except Exception:
            rows = []
        if not rows:
            continue
        bbox = fitz.Rect(table.bbox)
        tables_out.append({"bbox": bbox, "rows": rows})
    return tables_out


def is_probable_table_block(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    scored = 0
    for line in lines:
        if TABLE_SPLIT_RE.search(line) or "|" in line:
            scored += 1
    return scored >= max(2, len(lines) // 2)


def rows_to_plain_text(rows: list[list[Any]], page_num: int) -> str:
    cleaned_rows: list[list[str]] = []
    for row in rows:
        cleaned = [normalize_spaces("" if cell is None else str(cell)) for cell in row]
        if any(cleaned):
            cleaned_rows.append(cleaned)

    if not cleaned_rows:
        return f"[Table on page {page_num}]"

    col_count = max(len(r) for r in cleaned_rows)
    col_widths = [0] * col_count
    for row in cleaned_rows:
        for idx in range(col_count):
            cell = row[idx] if idx < len(row) else ""
            col_widths[idx] = max(col_widths[idx], len(cell))

    lines = [f"[Table on page {page_num}]"]
    for row in cleaned_rows:
        padded_cells = []
        for idx in range(col_count):
            cell = row[idx] if idx < len(row) else ""
            padded_cells.append(cell.ljust(col_widths[idx]))
        lines.append(" | ".join(padded_cells).rstrip())
    return "\n".join(lines)


def detect_list_item(line_text: str) -> tuple[str, bool]:
    bullet_match = BULLET_RE.match(line_text)
    if bullet_match:
        return f"- {normalize_spaces(bullet_match.group(2))}", True

    num_match = NUMBERED_RE.match(line_text)
    if num_match:
        return f"1. {normalize_spaces(num_match.group(2))}", True

    return "", False


def infer_heading_level(text: str, size: float, bold: bool, body_size: float) -> int | None:
    clean = normalize_spaces(text)
    if not clean:
        return None
    if len(clean) > 120:
        return None
    if clean.isdigit():
        return None
    if BULLET_RE.match(clean) or NUMBERED_RE.match(clean):
        return None

    ratio = size / max(body_size, 1.0)
    all_caps = clean.upper() == clean and any(c.isalpha() for c in clean)
    short_title = len(clean.split()) <= 12

    if ratio >= 1.9:
        return 1
    if ratio >= 1.6:
        return 2
    if ratio >= 1.35:
        return 3
    if (bold and ratio >= 1.12 and short_title and not clean.endswith(".")) or (
        all_caps and ratio >= 1.05 and short_title
    ):
        return 4
    return None


def should_start_new_paragraph(
    prev_line: dict[str, Any] | None, current_line: dict[str, Any], median_height: float
) -> bool:
    if prev_line is None:
        return False

    prev_text = prev_line["text"].rstrip()
    curr_text = current_line["text"].lstrip()
    vertical_gap = current_line["y0"] - prev_line["y1"]

    if vertical_gap > max(3.0, median_height * 0.8):
        return True
    if prev_text.endswith((".", "!", "?", ":", ";")) and curr_text[:1].isupper():
        return True
    return False


def merge_line_into_paragraph(paragraph: str, new_line: str) -> str:
    new_line = normalize_spaces(new_line)
    if not paragraph:
        return new_line

    if paragraph.endswith("-") and re.match(r"^[a-z\u00C0-\u024F]", new_line):
        return paragraph[:-1] + new_line

    if paragraph.endswith(("/", "—", "–")):
        return paragraph + new_line

    return f"{paragraph} {new_line}"


def block_lines_to_markdown(lines: list[dict[str, Any]], body_size: float) -> str:
    if not lines:
        return ""

    heights = [max(1.0, line["y1"] - line["y0"]) for line in lines]
    median_height = float(median(heights)) if heights else 12.0

    out: list[str] = []
    paragraph = ""
    prev_line: dict[str, Any] | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph.strip():
            out.append(paragraph.strip())
        paragraph = ""

    for line in lines:
        raw_text = line["text"]
        clean_text = normalize_spaces(raw_text)
        if not clean_text:
            flush_paragraph()
            prev_line = None
            continue

        list_line, is_list = detect_list_item(clean_text)
        heading_level = infer_heading_level(clean_text, line["size"], line["bold"], body_size)

        if is_list:
            flush_paragraph()
            out.append(list_line)
            prev_line = None
            continue

        if heading_level is not None:
            flush_paragraph()
            out.append(f"{'#' * heading_level} {clean_text}")
            prev_line = None
            continue

        if should_start_new_paragraph(prev_line, line, median_height):
            flush_paragraph()

        paragraph = merge_line_into_paragraph(paragraph, clean_text)
        prev_line = line

    flush_paragraph()
    return "\n\n".join(out)


def extract_text_lines_from_block(block: dict[str, Any]) -> list[dict[str, Any]]:
    lines_out: list[dict[str, Any]] = []
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        if not spans:
            continue

        text_parts: list[str] = []
        max_size = 0.0
        is_bold = False

        for span in spans:
            span_text = span.get("text", "")
            if span_text:
                text_parts.append(span_text)
            size = float(span.get("size", 0.0) or 0.0)
            max_size = max(max_size, size)
            font_name = str(span.get("font", "")).lower()
            if "bold" in font_name:
                is_bold = True

        text = "".join(text_parts)
        if not text.strip():
            continue

        bbox = line.get("bbox", [0, 0, 0, 0])
        lines_out.append(
            {
                "text": text,
                "size": max_size,
                "bold": is_bold,
                "y0": float(bbox[1]),
                "y1": float(bbox[3]),
            }
        )
    return lines_out


def try_ocr_page(
    page: fitz.Page, ocr_lang: str = "eng", tesseract_cmd: str | None = None
) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image_bytes = pix.tobytes("png")
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang=ocr_lang)
    return cleanup_markdown(text)


def page_to_markdown(
    page: fitz.Page,
    page_num: int,
    body_size: float,
    toc_map: dict[int, list[tuple[int, str]]],
    use_ocr_when_needed: bool,
    ocr_lang: str,
    tesseract_cmd: str | None,
) -> str:
    sections: list[tuple[float, str]] = []

    for level, title in toc_map.get(page_num, []):
        sections.append((-1.0, f"{'#' * level} {title}"))

    tables = extract_tables(page)
    table_rects = [item["bbox"] for item in tables]
    for table in tables:
        y = float(table["bbox"].y0)
        sections.append((y, rows_to_plain_text(table["rows"], page_num)))

    page_dict = page.get_text("dict")
    any_extractable_text = False

    for block in page_dict.get("blocks", []):
        btype = block.get("type")
        bbox = fitz.Rect(block.get("bbox", [0, 0, 0, 0]))
        y = float(bbox.y0)

        if btype == 1:
            sections.append((y, f"[Image on page {page_num}]"))
            continue

        if btype != 0:
            continue

        if any(rects_overlap(bbox, trect) for trect in table_rects):
            continue

        block_lines = extract_text_lines_from_block(block)
        if not block_lines:
            continue

        line_texts = [ln["text"] for ln in block_lines if ln["text"].strip()]
        if line_texts:
            any_extractable_text = True
        if is_probable_table_block([normalize_spaces(t) for t in line_texts]):
            table_plain = "\n".join(normalize_spaces(t) for t in line_texts if normalize_spaces(t))
            if table_plain:
                sections.append((y, f"[Table-like text on page {page_num}]\n{table_plain}"))
            continue

        md_text = block_lines_to_markdown(block_lines, body_size)
        if md_text:
            sections.append((y, md_text))

    sections.sort(key=lambda item: item[0])
    page_md = "\n\n".join(chunk for _, chunk in sections if chunk.strip())
    page_md = cleanup_markdown(page_md)

    if page_md:
        return page_md

    if use_ocr_when_needed:
        ocr_text = try_ocr_page(page, ocr_lang=ocr_lang, tesseract_cmd=tesseract_cmd)
        if ocr_text:
            return f"[OCR fallback used on page {page_num}]\n\n{ocr_text}"

    if not any_extractable_text:
        return f"[OCR REQUIRED ON PAGE {page_num}]"
    return ""


def convert_pdf_to_markdown(
    pdf_path: Path,
    output_path: Path,
    use_ocr_when_needed: bool = False,
    ocr_lang: str = "eng",
    tesseract_cmd: str | None = None,
) -> Path:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Path is not a file: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF (possibly corrupted): {pdf_path}\n{exc}") from exc

    with doc:
        total_pages = len(doc)
        if total_pages == 0:
            raise RuntimeError("PDF is empty (0 pages).")

        print(f"Opened PDF: {pdf_path}")
        print(f"Total pages: {total_pages}")
        print("Estimating body font size...")
        body_size = estimate_body_font_size(doc)
        print(f"Estimated body font size: {body_size:.2f}")

        toc_map = build_toc_map(doc)
        if toc_map:
            print(f"Detected bookmarks/TOC entries on {len(toc_map)} page(s).")
        else:
            print("No bookmarks/TOC found or readable.")

        with output_path.open("w", encoding="utf-8", newline="\n") as out:
            first_written = False
            for idx in range(total_pages):
                page_num = idx + 1
                print(f"[{page_num}/{total_pages}] Processing page {page_num}...")
                try:
                    page = doc[idx]
                    md = page_to_markdown(
                        page=page,
                        page_num=page_num,
                        body_size=body_size,
                        toc_map=toc_map,
                        use_ocr_when_needed=use_ocr_when_needed,
                        ocr_lang=ocr_lang,
                        tesseract_cmd=tesseract_cmd,
                    ).strip()
                except Exception as exc:
                    print(
                        f"Warning: Failed to process page {page_num}: {exc}. "
                        "Skipping this page.",
                        file=sys.stderr,
                    )
                    continue

                if not md:
                    continue

                if first_written:
                    out.write(PAGE_SEPARATOR)
                out.write(md)
                first_written = True

    return output_path


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.pdf_path).expanduser()
    output_path = get_output_path(pdf_path)

    try:
        result = convert_pdf_to_markdown(
            pdf_path=pdf_path,
            output_path=output_path,
            use_ocr_when_needed=args.ocr_needed,
            ocr_lang=args.ocr_lang,
            tesseract_cmd=args.tesseract_cmd,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 3

    print(f"\nMarkdown file generated: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
