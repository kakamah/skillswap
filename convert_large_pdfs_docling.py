#!/usr/bin/env python3
"""Convert very large PDF batches to Markdown with Docling + CUDA.

This script is optimized for heavy PDFs and long-running batch jobs:
  - Uses Docling with PdfPipelineOptions.
  - Forces CUDA acceleration.
  - Tunes batching/queue controls for lower peak memory.
  - Cleans memory after EACH file (VRAM + RAM).
  - Continues processing even if individual files fail.
"""

from __future__ import annotations

import argparse
import gc
import logging
import sys
import time
from pathlib import Path
from typing import Iterable

import torch
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption

# Defaults requested by user
DEFAULT_INPUT_DIR = Path(r"C:\Users\CoolPC\Desktop\PDF_Big")
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\CoolPC\Desktop\Result")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert large PDF files to Markdown with Docling + CUDA."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing source PDFs (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for Markdown output (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional file limit. 0 means process all discovered PDFs.",
    )
    parser.add_argument(
        "--enable-ocr",
        action="store_true",
        help="Enable OCR. Disabled by default to reduce memory usage.",
    )
    return parser.parse_args()


def configure_logging(output_dir: Path) -> logging.Logger:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "conversion.log"

    logger = logging.getLogger("pdf_to_markdown")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def ensure_cuda_available() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available. Install a CUDA-enabled PyTorch build and NVIDIA drivers."
        )


def configure_docling_for_low_memory(enable_ocr: bool) -> PdfPipelineOptions:
    # Global page-level chunking: process pages in very small batches.
    settings.perf.page_batch_size = 1

    pipeline_options = PdfPipelineOptions(
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CUDA),
    )

    # Keep features minimal for lower memory pressure on very large files.
    pipeline_options.do_ocr = enable_ocr
    pipeline_options.do_table_structure = True
    pipeline_options.do_code_enrichment = False
    pipeline_options.do_formula_enrichment = False
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = False
    pipeline_options.generate_parsed_pages = False
    pipeline_options.force_backend_text = not enable_ocr

    # Threaded-stage controls available on PdfPipelineOptions.
    pipeline_options.ocr_batch_size = 1
    pipeline_options.layout_batch_size = 1
    pipeline_options.table_batch_size = 1
    pipeline_options.queue_max_size = 2
    pipeline_options.batch_polling_interval_seconds = 0.1
    return pipeline_options


def build_converter(pipeline_options: PdfPipelineOptions) -> DocumentConverter:
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def discover_pdfs(input_dir: Path, limit: int) -> list[Path]:
    pdfs = sorted(input_dir.glob("*.pdf"))
    if limit > 0:
        return pdfs[:limit]
    return pdfs


def save_markdown(result, output_file: Path) -> None:
    markdown_text = result.document.export_to_markdown()
    output_file.write_text(markdown_text, encoding="utf-8")


def hard_cleanup_cuda_and_ram() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    gc.collect()


def process_files(
    files: Iterable[Path], output_dir: Path, logger: logging.Logger, enable_ocr: bool
) -> None:
    files = list(files)
    total = len(files)
    success_count = 0
    failure_count = 0
    start_batch = time.perf_counter()

    for idx, pdf_path in enumerate(files, start=1):
        converter = None
        conv_result = None
        started = time.perf_counter()
        logger.info("[%s/%s] Processing Heavy File: %s...", idx, total, pdf_path.name)

        try:
            pipeline_options = configure_docling_for_low_memory(enable_ocr=enable_ocr)
            converter = build_converter(pipeline_options)

            conv_result = converter.convert(pdf_path, raises_on_error=False)
            if conv_result.status not in (
                ConversionStatus.SUCCESS,
                ConversionStatus.PARTIAL_SUCCESS,
            ):
                raise RuntimeError(f"Docling status: {conv_result.status}")

            output_file = output_dir / f"{pdf_path.stem}.md"
            save_markdown(conv_result, output_file)
            elapsed = time.perf_counter() - started
            success_count += 1
            logger.info("Completed: %s (%.2f sec)", pdf_path.name, elapsed)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            failure_count += 1
            logger.exception(
                "FAILED: %s after %.2f sec | error=%s", pdf_path.name, elapsed, exc
            )
        finally:
            # Mandatory cleanup per file to reduce OOM risk in long runs.
            del conv_result
            del converter
            hard_cleanup_cuda_and_ram()

    batch_elapsed = time.perf_counter() - start_batch
    logger.info(
        "Batch finished. total=%s success=%s failed=%s elapsed=%.2f sec",
        total,
        success_count,
        failure_count,
        batch_elapsed,
    )


def main() -> int:
    args = parse_args()
    logger = configure_logging(args.output_dir)

    try:
        ensure_cuda_available()
    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        return 1

    if not args.input_dir.exists():
        logger.error("Input directory does not exist: %s", args.input_dir)
        return 1

    pdf_files = discover_pdfs(args.input_dir, args.limit)
    if not pdf_files:
        logger.warning("No PDF files found in: %s", args.input_dir)
        return 0

    logger.info("Discovered %s PDF file(s). Output dir: %s", len(pdf_files), args.output_dir)
    process_files(pdf_files, args.output_dir, logger, enable_ocr=args.enable_ocr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
