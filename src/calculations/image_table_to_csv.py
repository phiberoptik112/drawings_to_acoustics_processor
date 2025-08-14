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
import logging
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional

import cv2
import numpy as np
import pandas as pd
import pytesseract
from PIL import Image


logger = logging.getLogger(__name__)


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
        logger.debug(f"Configured tesseract executable from explicit path: {explicit_path}")
        return

    # If an environment variable is set, honor it; otherwise, best-effort guess on Windows.
    env_path = os.environ.get("TESSERACT_EXE") or os.environ.get("TESSERACT_CMD")
    if env_path and os.path.exists(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        logger.debug(f"Configured tesseract executable from environment: {env_path}")
        return

    default_windows_path = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    if os.name == "nt" and os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path
        logger.debug(f"Configured tesseract executable from Windows default: {default_windows_path}")


def read_image_bgr(image_path: str) -> np.ndarray:
    logger.info(f"Loading image from: {image_path}")
    t0 = time.perf_counter()
    image_bgr = cv2.imread(image_path)
    dt_ms = (time.perf_counter() - t0) * 1000
    if image_bgr is None:
        logger.error(f"Failed to read image: {image_path}")
        raise FileNotFoundError(f"Unable to read image: {image_path}")
    h, w = image_bgr.shape[:2]
    logger.info(f"Loaded image size: {w}x{h} (BGR), load time: {dt_ms:.1f} ms")
    return image_bgr


def preprocess_for_grid(image_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return grayscale, binary, and inverted binary images suitable for grid detection."""
    logger.debug("Preprocessing image for grid detection (grayscale + adaptive threshold)")
    t0 = time.perf_counter()
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Use adaptive threshold to be robust to lighting; invert so lines are white
    bin_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10
    )
    inv = 255 - bin_img
    dt_ms = (time.perf_counter() - t0) * 1000
    logger.debug(
        f"Preprocess complete: gray={gray.shape}, bin={bin_img.shape}, inv={inv.shape}, {dt_ms:.1f} ms"
    )
    return gray, bin_img, inv


def _apply_clahe(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _denoise_gray(gray: np.ndarray) -> np.ndarray:
    # Non-local means denoising for grayscale images
    return cv2.fastNlMeansDenoising(gray, None, h=7, templateWindowSize=7, searchWindowSize=21)


def _rotate_image(image: np.ndarray, angle_deg: float) -> np.ndarray:
    if abs(angle_deg) < 0.05:
        return image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def _estimate_skew_angle(gray: np.ndarray) -> float:
    # Edge detection + Hough transform to infer skew from dominant near-horizontal or near-vertical lines
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180.0, threshold=200)
        if lines is None or len(lines) == 0:
            return 0.0
        angles: List[float] = []
        for rho_theta in lines[:200]:
            rho, theta = rho_theta[0]
            deg = (theta * 180.0 / np.pi)
            # Map to range [-90, 90)
            while deg >= 90.0:
                deg -= 180.0
            while deg < -90.0:
                deg += 180.0
            # Consider near-0 or near-90 lines
            if abs(deg) <= 45.0:
                # Near horizontal: target 0 deg
                angles.append(deg)
            else:
                # Near vertical: target 90 deg → correction towards 0
                correction = deg - (90.0 if deg > 0 else -90.0)
                angles.append(correction)
        if not angles:
            return 0.0
        # Robust central tendency
        median_angle = float(np.median(np.array(angles, dtype=np.float32)))
        return median_angle
    except Exception as exc:
        logger.debug(f"Skew estimation failed: {exc}")
        return 0.0


def preprocess_for_grid_enhanced(image_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    logger.debug("Enhanced preprocessing: deskew + CLAHE + denoise + adaptive threshold")
    t0 = time.perf_counter()
    gray0 = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # CLAHE and denoise before skew estimation to stabilize edges
    gray1 = _apply_clahe(gray0)
    gray1 = _denoise_gray(gray1)
    # Estimate skew and rotate original color image to avoid interpolation artifacts chaining
    angle = _estimate_skew_angle(gray1)
    rotated = _rotate_image(image_bgr, -angle)
    # Recompute grayscale after rotation
    gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
    gray = _apply_clahe(gray)
    gray = _denoise_gray(gray)
    bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)
    inv = 255 - bin_img
    dt_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Enhanced preprocess complete (angle={angle:.2f}°): gray={gray.shape}, {dt_ms:.1f} ms")
    return gray, bin_img, inv, angle


def extract_grid_masks(inv_bin: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Extract horizontal and vertical line masks from inverted binary image."""
    height, width = inv_bin.shape
    # Kernel sizes relative to image dimension for robustness
    horizontal_kernel_width = max(10, width // 100)
    vertical_kernel_height = max(10, height // 100)
    logger.debug(
        f"Extracting grid masks with kernels: hor=({horizontal_kernel_width},1), ver=(1,{vertical_kernel_height})"
    )

    t0 = time.perf_counter()
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_kernel_width, 1))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_kernel_height))

    horizontal_lines = cv2.erode(inv_bin, hor_kernel, iterations=1)
    horizontal_lines = cv2.dilate(horizontal_lines, hor_kernel, iterations=1)

    vertical_lines = cv2.erode(inv_bin, ver_kernel, iterations=1)
    vertical_lines = cv2.dilate(vertical_lines, ver_kernel, iterations=1)

    dt_ms = (time.perf_counter() - t0) * 1000
    logger.debug(
        f"Grid masks extracted: horizontal={horizontal_lines.shape}, vertical={vertical_lines.shape}, {dt_ms:.1f} ms"
    )
    return horizontal_lines, vertical_lines


def detect_cell_boxes(grid_mask: np.ndarray) -> List[CellBox]:
    """Detect cell bounding boxes from a grid mask.

    Steps:
      - close small gaps
      - find contours
      - filter by area and aspect ratio
      - return as CellBox sorted by top-left.
    """
    logger.debug("Detecting cell boxes from grid mask")
    t0 = time.perf_counter()
    # Close small gaps to form enclosed rectangles
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(grid_mask, cv2.MORPH_CLOSE, kernel, iterations=3)

    contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    logger.debug(f"Contours found: {len(contours)}")

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
    dt_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Cell boxes detected: {len(boxes)} (min_area={min_area}), {dt_ms:.1f} ms")
    return boxes


def cluster_rows(boxes: List[CellBox], tolerance: Optional[int] = None) -> List[List[CellBox]]:
    """Group cell boxes into rows by y proximity."""
    if not boxes:
        logger.info("No boxes to cluster into rows")
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
    logger.info(f"Clustered into rows: {len(rows)} with tolerance: {tol}")
    return rows


def crop_cell(image_bgr: np.ndarray, box: CellBox, pad: int = 2) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    x0 = max(0, box.x + pad)
    y0 = max(0, box.y + pad)
    x1 = min(w, box.x + box.w - pad)
    y1 = min(h, box.y + box.h - pad)
    crop = image_bgr[y0:y1, x0:x1]
    logger.debug(f"Cropped cell at (x={box.x}, y={box.y}, w={box.w}, h={box.h}) -> crop size: {crop.shape[1]}x{crop.shape[0]}")
    return crop


def ocr_image_to_text(image_bgr: np.ndarray, psm: int = 6, dpi: int = 300, whitelist: Optional[str] = None) -> str:
    logger.debug(f"Running OCR on cell image (psm={psm}, dpi={dpi})")
    t0 = time.perf_counter()
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Binarize and upscale to help OCR
    scale = 2
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_img = Image.fromarray(th)
    try:
        config = f"--psm {psm} -c user_defined_dpi={dpi}"
        if whitelist:
            config += f" -c tessedit_char_whitelist={whitelist}"
        text = pytesseract.image_to_string(pil_img, config=config)
    except Exception as exc:
        logger.exception(f"OCR failed: {exc}")
        text = ""
    # Normalize whitespace and dashes
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    dt_ms = (time.perf_counter() - t0) * 1000
    logger.debug(f"OCR complete: {len(text)} characters, {dt_ms:.1f} ms")
    return text


def extract_table(image_bgr: np.ndarray, enhanced: bool = False) -> List[List[str]]:
    """High-level table extraction pipeline.

    Returns a list of rows, each a list of strings.
    """
    logger.info("Starting high-level table extraction pipeline")
    t0 = time.perf_counter()
    if enhanced:
        _, _, inv, angle = preprocess_for_grid_enhanced(image_bgr)
        logger.info(f"Enhanced preprocess used (deskew angle={angle:.2f}°)")
    else:
        _, _, inv = preprocess_for_grid(image_bgr)
    hor, ver = extract_grid_masks(inv)
    grid = cv2.addWeighted(hor, 0.5, ver, 0.5, 0.0)

    boxes = detect_cell_boxes(grid)
    rows = cluster_rows(boxes)

    # Heuristic sanity check: require at least 1 row and columns >= 2.
    # Originally this required >=2 rows, which caused legitimate single-row
    # tables (e.g., a single extracted row image) to fall back unnecessarily
    # to TSV OCR and often fail. Accept single-row tables if they have
    # multiple columns.
    if len(rows) == 0 or max(len(r) for r in rows) < 2:
        logger.warning(
            "Grid-based extraction insufficient (rows or cols too small). Falling back to Tesseract TSV."
        )
        result = extract_table_tesseract_tsv(image_bgr)
        logger.info(f"Fallback extraction produced {len(result)} rows")
        return result

    extracted: List[List[str]] = []
    for r_idx, row in enumerate(rows):
        values: List[str] = []
        for c_idx, box in enumerate(row):
            cell_img = crop_cell(image_bgr, box)
            txt = ocr_image_to_text(cell_img, psm=(7 if enhanced else 6), dpi=300)
            logger.debug(f"OCR cell r{r_idx}c{c_idx}: '{txt[:30] + ('…' if len(txt) > 30 else '')}'")
            values.append(txt)
        extracted.append(values)
    dt_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        f"Grid-based extraction produced {len(extracted)} rows x {max((len(r) for r in extracted), default=0)} cols in {dt_ms:.1f} ms"
    )
    return extracted


def extract_table_tesseract_tsv(image_bgr: np.ndarray) -> List[List[str]]:
    """Fallback extraction using Tesseract TSV; groups words by y midpoint rows.

    This is less accurate than grid-based extraction but ensures we can get a
    best-effort CSV even when line detection fails.
    """
    logger.info("Using Tesseract TSV fallback extraction")
    t0 = time.perf_counter()
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    scale = 2
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_img = Image.fromarray(th)
    try:
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DATAFRAME)
    except Exception as exc:
        logger.exception(f"Tesseract TSV extraction failed: {exc}")
        return []
    data = data.dropna(subset=["text"])  # keep rows with text
    if data.empty:
        logger.warning("Tesseract TSV returned no text data")
        return []

    # Compute row grouping by y center proximity
    data["y_center"] = data["top"] + data["height"] / 2.0
    data.sort_values(["y_center", "left"], inplace=True)

    # Dynamic row threshold from median text height
    median_h = max(10.0, float(data["height"].median()))
    row_tol = median_h * 0.6
    # Prepare column centers globally from x positions
    data["x_center"] = data["left"] + data["width"] / 2.0
    median_w = max(8.0, float(data["width"].median()))
    col_tol = median_w * 1.25
    column_centers: List[float] = []
    for x in data["x_center"].tolist():
        if not column_centers:
            column_centers.append(float(x))
            continue
        diffs = [abs(x - c) for c in column_centers]
        j = int(np.argmin(diffs))
        if diffs[j] <= col_tol:
            # Merge by averaging to stabilize centers
            column_centers[j] = (column_centers[j] + float(x)) / 2.0
        else:
            column_centers.append(float(x))
    column_centers.sort()
    logger.debug(f"Estimated {len(column_centers)} columns (tol={col_tol:.1f})")

    # Group by rows (y) while keeping x positions to map into columns
    row_tokens: List[List[Tuple[float, str]]] = []
    current_row_tokens: List[Tuple[float, str]] = []
    last_y = None
    for _, r in data.iterrows():
        y = float(r["y_center"])
        word = str(r["text"]).strip()
        if not word:
            continue
        if last_y is None:
            current_row_tokens = [(float(r["x_center"]), word)]
            last_y = y
            continue
        if abs(y - last_y) <= row_tol:
            current_row_tokens.append((float(r["x_center"]), word))
            last_y = (last_y + y) / 2.0
        else:
            row_tokens.append(current_row_tokens)
            current_row_tokens = [(float(r["x_center"]), word)]
            last_y = y
    if current_row_tokens:
        row_tokens.append(current_row_tokens)

    # Build rectangular rows by assigning tokens to nearest column center
    rows_out: List[List[str]] = []
    for tokens in row_tokens:
        row_cells = ["" for _ in column_centers]
        # sort tokens by x increasing
        tokens_sorted = sorted(tokens, key=lambda t: t[0])
        for x_c, word in tokens_sorted:
            diffs = [abs(x_c - c) for c in column_centers]
            j = int(np.argmin(diffs))
            if row_cells[j]:
                row_cells[j] += " " + word
            else:
                row_cells[j] = word
        rows_out.append(row_cells)

    dt_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"TSV fallback produced {len(rows_out)} rows x {len(column_centers)} cols in {dt_ms:.1f} ms")
    return rows_out


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
    logger.info(f"CSV saved with shape {df.shape} to: {output_csv}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract table from image and save to CSV.")
    parser.add_argument("--image", required=True, help="Path to input table image (png/jpg).")
    parser.add_argument("--output", required=True, help="Path to output CSV file.")
    parser.add_argument(
        "--tesseract-exe",
        default=None,
        help="Optional path to tesseract executable if not on PATH.",
    )
    parser.add_argument(
        "--enhanced-preprocess",
        action="store_true",
        help="Enable enhanced preprocessing (deskew, CLAHE, denoise) and OCR tuning.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging for image processing steps.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "debug", False) else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger.info("Starting image table to CSV extraction")
    logger.debug(
        f"Arguments: image='{args.image}', output='{args.output}', debug={args.debug}, enhanced={getattr(args, 'enhanced_preprocess', False)}"
    )
    configure_tesseract_executable(args.tesseract_exe)
    image_bgr = read_image_bgr(args.image)
    rows = extract_table(image_bgr, enhanced=getattr(args, "enhanced_preprocess", False))
    if not rows:
        logger.error("Extraction produced 0 rows")
        raise RuntimeError("Failed to extract any table data from the image.")
    save_csv(rows, args.output)
    print(f"Saved CSV: {args.output}")


if __name__ == "__main__":
    main()

