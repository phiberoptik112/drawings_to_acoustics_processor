"""
PDF Mechanical Schedule Importer (PyMuPDF)
 - Extracts words with coordinates and reconstructs lines using block/line ids
 - Detects header row by keywords (MARK & NUMBER, or NAME/TAG & TYPE/UNIT)
 - Parses subsequent lines into unit records, capturing frequency bands when present
 - Emits verbose debug logs to stdout to aid troubleshooting
"""

from __future__ import annotations

import os
import json
from typing import List, Dict, Any

import fitz  # PyMuPDF
import json
import traceback

# Optional deps for OCR fallback (import robustly when script executed directly)
try:
    import numpy as np  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[DEBUG] numpy import failed: {e}")
    np = None  # type: ignore
try:
    import cv2  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[DEBUG] cv2 import failed: {e}")
    cv2 = None  # type: ignore
try:
    # Try package-relative import
    from .image_table_to_csv import extract_table  # type: ignore
except Exception:
    try:
        # Fallback to same-folder absolute import when run as a script
        import importlib.util, pathlib, sys
        here = pathlib.Path(__file__).resolve().parent
        sys.path.insert(0, str(here))
        spec = importlib.util.spec_from_file_location("image_table_to_csv", str(here / "image_table_to_csv.py"))
        module = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(module)  # type: ignore
        extract_table = module.extract_table  # type: ignore
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG] image_table_to_csv import failed: {e}\n{traceback.format_exc()}")
        extract_table = None  # type: ignore

# Optional pdfplumber fallback
try:
    import pdfplumber  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[DEBUG] pdfplumber import failed: {e}")
    pdfplumber = None  # type: ignore


def _lines_from_words(words: List[tuple]) -> List[List[str]]:
    """Group PyMuPDF words into lines by (block, line) and return token lists."""
    # word tuple: (x0, y0, x1, y1, text, block_no, line_no, word_no)
    from collections import defaultdict
    grouped = defaultdict(list)
    for w in words:
        if len(w) < 8:
            # Defensive guard for older PyMuPDF variations
            x0, y0, x1, y1, text = w[:5]
            blk = 0
            line = int(round(y0))
        else:
            x0, y0, x1, y1, text, blk, line, wno = w
        grouped[(blk, line)].append((x0, text))
    # Sort lines by approximate y (line id preserves order per block), then x
    keys_sorted = sorted(grouped.keys(), key=lambda k: (k[0], k[1]))
    lines: List[List[str]] = []
    for key in keys_sorted:
        items = sorted(grouped[key], key=lambda it: it[0])
        tokens = [t for _x, t in items]
        if tokens:
            lines.append(tokens)
    return lines


def _parse_rows_to_units(rows: List[List[str]], debug: bool = False) -> List[Dict[str, Any]]:
    """Parse table rows (list-of-list of strings) into MechanicalUnit-like dicts.
    Strategy: locate first data row; for each row, take first two tokens as MARK/NUMBER,
    then collect the next >=24 numeric tokens as 3x8 bands (inlet/radiated/outlet).
    If fewer than 24, store what we have under outlet.
    """
    units: List[Dict[str, Any]] = []
    for ri, row in enumerate(rows):
        # Skip empty/short rows
        if len([c for c in row if c.strip()]) < 3:
            continue
        tokens = [str(c).strip() for c in row if c is not None]
        if len(tokens) < 3:
            continue
        # Skip obvious header lines
        if tokens[0].lower() in {"mark", "unit", "unit identification"} or tokens[1].lower() == "number":
            continue
        mark = tokens[0]
        number = tokens[1]
        if not mark or not number:
            continue
        # Collect numeric tokens
        nums = [t for t in tokens[2:] if any(ch.isdigit() for ch in t) and t.replace('.', '').replace('-', '').isdigit()]
        if not nums:
            continue
        name = f"{mark}-{number}"
        unit_type = mark
        band_keys = ["63","125","250","500","1000","2000","4000","8000"]
        inlet_json = radiated_json = outlet_json = None
        if len(nums) >= 24:
            inlet_json = json.dumps({k: v for k, v in zip(band_keys, nums[:8])})
            radiated_json = json.dumps({k: v for k, v in zip(band_keys, nums[8:16])})
            outlet_json = json.dumps({k: v for k, v in zip(band_keys, nums[16:24])})
        else:
            outlet_json = json.dumps({k: v for k, v in zip(band_keys, nums[:8])})
        units.append({
            "name": name,
            "unit_type": unit_type,
            "inlet_levels_json": inlet_json,
            "radiated_levels_json": radiated_json,
            "outlet_levels_json": outlet_json,
        })
    if debug:
        print(f"[DEBUG] OCR rows parsed -> {len(units)} units")
    return units


def _ocr_page_to_units(page: fitz.Page, debug: bool = False) -> List[Dict[str, Any]]:
    """Render page to PNG and call the existing image extractor as a subprocess,
    then parse the resulting CSV.
    """
    import tempfile, os, subprocess, sys, csv as csvmod
    # Render to 300 DPI PNG
    zoom = 300.0 / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    with tempfile.TemporaryDirectory() as td:
        img_path = os.path.join(td, "page.png")
        csv_path = os.path.join(td, "table.csv")
        pix.save(img_path)
        # Call image_table_to_csv.py CLI
        script_path = os.path.join(os.path.dirname(__file__), "image_table_to_csv.py")
        cmd = [sys.executable, script_path, "--image", img_path, "--output", csv_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if debug:
            print(f"[DEBUG] OCR subprocess rc={result.returncode}")
            if result.stdout:
                print(f"[DEBUG] OCR stdout: {result.stdout[:1000]}")
            if result.stderr:
                print(f"[DEBUG] OCR stderr: {result.stderr[:1000]}")
        if result.returncode != 0 or not os.path.exists(csv_path):
            return []
        rows: List[List[str]] = []
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csvmod.reader(f)
            for row in reader:
                rows.append(row)
        if debug:
            print(f"[DEBUG] OCR CSV rows: {len(rows)}")
            if rows:
                print(f"[DEBUG] OCR CSV first row: {rows[0]}")
        return _parse_rows_to_units(rows, debug=debug)


def _plumber_extract_units(pdf_path: str, debug: bool = False) -> List[Dict[str, Any]]:
    """Use pdfplumber to extract table cells into rows, then parse."""
    if pdfplumber is None:
        if debug:
            print("[DEBUG] pdfplumber not available")
        return []
    units: List[Dict[str, Any]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pi, page in enumerate(pdf.pages, start=1):
                # Try line-based table extraction first
                settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_x_tolerance": 5,
                    "intersection_y_tolerance": 5,
                }
                tables = page.extract_tables(table_settings=settings) or []
                if debug:
                    print(f"[DEBUG] pdfplumber page {pi}: {len(tables)} tables (lines strategy)")
                if not tables:
                    # Fallback to default extraction
                    tables = page.extract_tables() or []
                    if debug:
                        print(f"[DEBUG] pdfplumber page {pi}: {len(tables)} tables (default strategy)")
                for ti, table in enumerate(tables):
                    # table is List[List[str|None]]
                    rows: List[List[str]] = []
                    for r in table:
                        if r is None:
                            continue
                        # Keep original columns; coerce None->""
                        rows.append([c.strip() if isinstance(c, str) else "" for c in r])
                    parsed = _parse_rows_to_units(rows, debug=debug)
                    units.extend(parsed)
                    if debug:
                        print(f"[DEBUG] pdfplumber page {pi} table {ti}: parsed {len(parsed)} units")
    except Exception as e:
        if debug:
            print(f"[DEBUG] pdfplumber error: {e}\n{traceback.format_exc()}")
    return units


def extract_units_from_pdf(pdf_path: str, debug: bool = False) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    units: List[Dict[str, Any]] = []

    for pi, page in enumerate(doc, start=1):
        words = page.get_text("words") or []
        lines = _lines_from_words(words)
        if debug:
            print(f"[DEBUG] Page {pi}: {len(words)} words, {len(lines)} lines")
            for idx, row in enumerate(lines[:20]):
                print(f"[DEBUG] L{idx:02d}: {' '.join(row)}")

        if not lines:
            # Likely a scanned/image-only PDF — try pdfplumber first, then OCR
            if debug:
                print(f"[DEBUG] Page {pi}: no text lines; trying pdfplumber")
            pl_units = _plumber_extract_units(pdf_path, debug=debug)
            if pl_units:
                units.extend(pl_units)
            else:
                if debug:
                    print(f"[DEBUG] Page {pi}: pdfplumber found nothing; invoking OCR fallback")
                units.extend(_ocr_page_to_units(page, debug=debug))
            continue

        # Find header by presence of key markers
        header_idx = None
        header: List[str] = []
        for i, row in enumerate(lines[:200]):
            lower = [t.lower() for t in row]
            has_mark_number = ("mark" in lower and "number" in lower)
            has_name_type = (any(x in lower for x in ["name", "tag"]) and any(x in lower for x in ["type", "unit", "unit type"]))
            freq_hint = any(x in lower for x in ["63", "125", "250", "500", "1k", "1000"])  # hint only
            if has_mark_number or has_name_type or freq_hint:
                header_idx = i
                header = row
                break

        if header_idx is None:
            if debug:
                print(f"[DEBUG] Page {pi}: No header detected in text; trying pdfplumber then OCR")
            pl_units = _plumber_extract_units(pdf_path, debug=debug)
            if pl_units:
                units.extend(pl_units)
            else:
                units.extend(_ocr_page_to_units(page, debug=debug))
            continue

        data_rows = lines[header_idx + 1 :]
        header_lower = [h.lower() for h in header]

        def find_idx(keys: List[str]) -> int | None:
            for key in keys:
                if key in header_lower:
                    return header_lower.index(key)
            return None

        idx_name = find_idx(["name", "tag", "id"])  # typical naming column
        idx_type = find_idx(["type", "unit", "unit type"]) 
        idx_mark = find_idx(["mark"]) 
        idx_number = find_idx(["number"]) 

        # Frequency columns
        idxs_freq = {
            "63": find_idx(["63"]),
            "125": find_idx(["125"]),
            "250": find_idx(["250"]),
            "500": find_idx(["500"]),
            "1000": find_idx(["1k", "1000"]),
            "2000": find_idx(["2k", "2000"]),
            "4000": find_idx(["4k", "4000"]),
            "8000": find_idx(["8k", "8000"]),
        }

        if debug:
            print(f"[DEBUG] Page {pi}: header tokens = {header}")
            print(f"[DEBUG] indices: name={idx_name}, type={idx_type}, mark={idx_mark}, number={idx_number}, freq={idxs_freq}")

        page_units_before = len(units)
        for li, row in enumerate(data_rows, start=header_idx + 2):
            # Extract core name/type from available columns; otherwise synthesize from mark/number
            name = row[idx_name] if idx_name is not None and idx_name < len(row) else ""
            unit_type = row[idx_type] if idx_type is not None and idx_type < len(row) else ""

            if not name and (idx_mark is not None or idx_number is not None):
                mark = row[idx_mark] if idx_mark is not None and idx_mark < len(row) else ""
                number = row[idx_number] if idx_number is not None and idx_number < len(row) else ""
                mark_clean = "".join(ch for ch in mark if ch.isalnum() or ch in ("-", "_"))
                number_clean = "".join(ch for ch in number if ch.isalnum() or ch in ("-", "_"))
                if mark_clean and number_clean:
                    name = f"{mark_clean}-{number_clean}"
                    unit_type = mark_clean
                elif mark_clean:
                    name = mark_clean
                    unit_type = mark_clean

            # Heuristic: stop if line is clearly not data (too few tokens)
            if not name and len(row) < 3:
                continue
            if not name:
                # Try using the first token as a last resort
                name = row[0] if row else ""
            if not name:
                continue

            # Frequency preview across three sections if available
            # Extract numeric tokens after mark/number to allow fallback within header-based mode
            numeric_tokens = [t for t in row[2:] if any(ch.isdigit() for ch in t) and t.replace('.', '').replace('-', '').isdigit()]
            if len(numeric_tokens) >= 24:
                inlet_vals = numeric_tokens[:8]
                radiated_vals = numeric_tokens[8:16]
                outlet_vals = numeric_tokens[16:24]
                inlet_json = json.dumps({k: v for k, v in zip(["63","125","250","500","1000","2000","4000","8000"], inlet_vals)})
                radiated_json = json.dumps({k: v for k, v in zip(["63","125","250","500","1000","2000","4000","8000"], radiated_vals)})
                outlet_json = json.dumps({k: v for k, v in zip(["63","125","250","500","1000","2000","4000","8000"], outlet_vals)})
            else:
                bands = {}
                for band, col in idxs_freq.items():
                    if col is not None and col < len(row):
                        bands[band] = row[col]
                inlet_json = None
                radiated_json = None
                outlet_json = json.dumps(bands) if bands else None

            # Extra columns
            extras = {}
            for i, cell in enumerate(row):
                if i >= len(header):
                    continue
                label = header[i]
                base_keys = {"name","tag","id","type","unit","unit type","mark","number"}
                if label.lower() in base_keys or label in idxs_freq:
                    continue
                if cell:
                    extras[label] = cell

            units.append({
                "name": name,
                "unit_type": unit_type,
                "inlet_levels_json": inlet_json,
                "radiated_levels_json": radiated_json,
                "outlet_levels_json": outlet_json,
                "extra_json": json.dumps(extras) if extras else None,
            })

        if debug:
            added = len(units) - page_units_before
            print(f"[DEBUG] Page {pi}: parsed {added} rows")

    return units


def main(pdf_path: str, output_json: str, debug: bool = False) -> None:
    units = extract_units_from_pdf(pdf_path, debug=debug)
    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(units, f, indent=2)
    print(f"Extracted {len(units)} units -> {output_json}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract mechanical schedule from PDF")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    main(args.pdf, args.output, debug=args.debug)


