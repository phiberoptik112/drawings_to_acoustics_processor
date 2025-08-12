# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportMissingTypeStubs=false
"""
Image Table to CSV Extractor
---------------------------------

This utility extracts tabular data from a scanned table image and exports it
to CSV for downstream database loading. It uses OpenCV to detect the table
grid and Pytesseract for OCR.

Usage (Windows, from project root):

    python -m calc_scripts_fromMD.image_table_to_csv \
        --image "path/to/table_image.png" \
        --output "path/to/output.csv"

If Tesseract is not on PATH, specify the executable:

    --tesseract-exe "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

Dependencies:
  - opencv-python
  - pytesseract (requires Tesseract-OCR installed separately)
  - Pillow
  - pandas, numpy

Tesseract install (Windows):
  Download installer from https://github.com/UB-Mannheim/tesseract/wiki

The code is intentionally verbose and organized into small, testable
functions for clarity and maintainability.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional

import cv2
import numpy as np
import pandas as pd
import pytesseract
from PIL import Image


@dataclass
class CellBox:
    y: int
    x: int
    h: int
    w: int

    @property
    def xyxy(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def configure_tesseract_executable(explicit_path: Optional[str]) -> None:
    """Ensure pytesseract points at a valid tesseract executable.

    On Windows, a common default location is
    C:\\Program Files\\Tesseract-OCR\\tesseract.exe
    """
    if explicit_path:
        pytesseract.pytesseract.tesseract_cmd = explicit_path
        return

    # If an environment variable is set, honor it; otherwise, best-effort guess on Windows.
    env_path = os.environ.get("TESSERACT_EXE") or os.environ.get("TESSERACT_CMD")
    if env_path and os.path.exists(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        return

    default_windows_path = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    if os.name == "nt" and os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path


def read_image_bgr(image_path: str) -> np.ndarray:
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Unable to read image: {image_path}")
    return image_bgr


def preprocess_for_grid(image_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return grayscale, binary, and inverted binary images suitable for grid detection."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Use adaptive threshold to be robust to lighting; invert so lines are white
    bin_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10
    )
    inv = 255 - bin_img
    return gray, bin_img, inv


def extract_grid_masks(inv_bin: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Extract horizontal and vertical line masks from inverted binary image."""
    height, width = inv_bin.shape
    # Kernel sizes relative to image dimension for robustness
    horizontal_kernel_width = max(10, width // 100)
    vertical_kernel_height = max(10, height // 100)

    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_kernel_width, 1))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_kernel_height))

    horizontal_lines = cv2.erode(inv_bin, hor_kernel, iterations=1)
    horizontal_lines = cv2.dilate(horizontal_lines, hor_kernel, iterations=1)

    vertical_lines = cv2.erode(inv_bin, ver_kernel, iterations=1)
    vertical_lines = cv2.dilate(vertical_lines, ver_kernel, iterations=1)

    return horizontal_lines, vertical_lines


def detect_cell_boxes(grid_mask: np.ndarray) -> List[CellBox]:
    """Detect cell bounding boxes from a grid mask.

    Steps:
      - close small gaps
      - find contours
      - filter by area and aspect ratio
      - return as CellBox sorted by top-left.
    """
    # Close small gaps to form enclosed rectangles
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(grid_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes: List[CellBox] = []
    area_img = grid_mask.shape[0] * grid_mask.shape[1]
    min_area = max(100, int(area_img * 0.00002))  # heuristic
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < min_area:
            continue
        # Filter very elongated shapes (likely lines rather than cells)
        if w < 8 or h < 8:
            continue
        boxes.append(CellBox(y=y, x=x, h=h, w=w))

    # Sort by y then x
    boxes.sort(key=lambda b: (b.y, b.x))
    return boxes


def cluster_rows(boxes: List[CellBox], tolerance: Optional[int] = None) -> List[List[CellBox]]:
    """Group cell boxes into rows by y proximity."""
    if not boxes:
        return []

    median_height = int(np.median([b.h for b in boxes]))
    tol = tolerance or max(10, median_height // 2)

    rows: List[List[CellBox]] = []
    current_row: List[CellBox] = [boxes[0]]
    current_y = boxes[0].y
    for b in boxes[1:]:
        if abs(b.y - current_y) <= tol:
            current_row.append(b)
        else:
            current_row.sort(key=lambda c: c.x)
            rows.append(current_row)
            current_row = [b]
            current_y = b.y

    current_row.sort(key=lambda c: c.x)
    rows.append(current_row)
    return rows


def crop_cell(image_bgr: np.ndarray, box: CellBox, pad: int = 2) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    x0 = max(0, box.x + pad)
    y0 = max(0, box.y + pad)
    x1 = min(w, box.x + box.w - pad)
    y1 = min(h, box.y + box.h - pad)
    return image_bgr[y0:y1, x0:x1]


def ocr_image_to_text(image_bgr: np.ndarray) -> str:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Binarize and upscale to help OCR
    scale = 2
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_img = Image.fromarray(th)
    text = pytesseract.image_to_string(pil_img, config="--psm 6")
    # Normalize whitespace and dashes
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    return text


def extract_table(image_bgr: np.ndarray) -> List[List[str]]:
    """High-level table extraction pipeline.

    Returns a list of rows, each a list of strings.
    """
    _, _, inv = preprocess_for_grid(image_bgr)
    hor, ver = extract_grid_masks(inv)
    grid = cv2.addWeighted(hor, 0.5, ver, 0.5, 0.0)

    boxes = detect_cell_boxes(grid)
    rows = cluster_rows(boxes)

    # Heuristic sanity check: require at least 2 rows and columns >= 2
    if len(rows) < 2 or max(len(r) for r in rows) < 2:
        # Fallback to Tesseract TSV-based extraction
        return extract_table_tesseract_tsv(image_bgr)

    extracted: List[List[str]] = []
    for row in rows:
        values: List[str] = []
        for box in row:
            cell_img = crop_cell(image_bgr, box)
            values.append(ocr_image_to_text(cell_img))
        extracted.append(values)
    return extracted


def extract_table_tesseract_tsv(image_bgr: np.ndarray) -> List[List[str]]:
    """Fallback extraction using Tesseract TSV; groups words by y midpoint rows.

    This is less accurate than grid-based extraction but ensures we can get a
    best-effort CSV even when line detection fails.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    scale = 2
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_img = Image.fromarray(th)
    data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DATAFRAME)
    data = data.dropna(subset=["text"])  # keep rows with text
    if data.empty:
        return []

    # Compute row grouping by y center proximity
    data["y_center"] = data["top"] + data["height"] / 2.0
    data.sort_values(["y_center", "left"], inplace=True)

    # Dynamic row threshold from median text height
    median_h = max(10.0, float(data["height"].median()))
    row_tol = median_h * 0.6

    rows: List[List[str]] = []
    current_row: List[str] = []
    last_y = None
    for _, r in data.iterrows():
        y = float(r["y_center"])
        word = str(r["text"]).strip()
        if not word:
            continue
        if last_y is None:
            current_row = [word]
            last_y = y
            continue
        if abs(y - last_y) <= row_tol:
            current_row.append(word)
            last_y = (last_y + y) / 2.0
        else:
            rows.append([" ".join(current_row)])
            current_row = [word]
            last_y = y
    if current_row:
        rows.append([" ".join(current_row)])

    return rows


def normalize_rows_to_rectangular(table_rows: List[List[str]]) -> List[List[str]]:
    if not table_rows:
        return table_rows
    max_cols = max(len(r) for r in table_rows)
    normalized: List[List[str]] = []
    for r in table_rows:
        row = list(r)
        if len(row) < max_cols:
            row.extend([""] * (max_cols - len(row)))
        normalized.append(row)
    return normalized


def save_csv(rows: List[List[str]], output_csv: str) -> None:
    rows = normalize_rows_to_rectangular(rows)
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    df.to_csv(output_csv, index=False, header=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract table from image and save to CSV.")
    parser.add_argument("--image", required=True, help="Path to input table image (png/jpg).")
    parser.add_argument("--output", required=True, help="Path to output CSV file.")
    parser.add_argument(
        "--tesseract-exe",
        default=None,
        help="Optional path to tesseract executable if not on PATH.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_tesseract_executable(args.tesseract_exe)
    image_bgr = read_image_bgr(args.image)
    rows = extract_table(image_bgr)
    if not rows:
        raise RuntimeError("Failed to extract any table data from the image.")
    save_csv(rows, args.output)
    print(f"Saved CSV: {args.output}")


if __name__ == "__main__":
    main()

