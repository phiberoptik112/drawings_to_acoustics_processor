"""
RT60 Report Exporter — Generates per-space acoustic report pages (PDF or PNG).

Each page contains:
  • Header with space metadata and RT60 compliance status
  • RT60 frequency-response plot (untreated bare structure, treated, target ± tolerance)
  • Surface material summary table (area, % of total SA, % Sabine contribution)
  • Per-octave-band Sabine absorption table (sabins per material per band)
"""

import os
import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

FREQUENCIES = [125, 250, 500, 1000, 2000, 4000]
FREQ_LABELS = ['125 Hz', '250 Hz', '500 Hz', '1k Hz', '2k Hz', '4k Hz']

# ASTM reference absorption coefficients for bare (untreated) structural surfaces.
# These represent the "hard shell" of the room before any acoustic treatment.
# Sources: Building Acoustics Handbook / ASHRAE Handbook of Fundamentals
BARE_SURFACE_COEFFICIENTS: Dict[str, Dict[int, float]] = {
    'ceiling': {125: 0.05, 250: 0.07, 500: 0.09, 1000: 0.11, 2000: 0.08, 4000: 0.04},
    'wall':    {125: 0.05, 250: 0.07, 500: 0.09, 1000: 0.11, 2000: 0.08, 4000: 0.04},
    'floor':   {125: 0.01, 250: 0.01, 500: 0.02, 1000: 0.02, 2000: 0.02, 4000: 0.02},
}

_COLOR_DARK   = '#1a1a2e'
_COLOR_BLUE   = '#2980b9'
_COLOR_RED    = '#c0392b'
_COLOR_GREY   = '#7f8c8d'
_COLOR_GREEN  = '#27ae60'


class RTReportExporter:
    """Generates RT60 acoustic report figures and exports them to PDF or PNG."""

    def __init__(self):
        self._materials_enhanced: Optional[Dict] = None
        self._materials_broad: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Material database helpers
    # ------------------------------------------------------------------

    def _get_materials_enhanced(self) -> Dict:
        if self._materials_enhanced is None:
            for module_path in ('data.enhanced_materials', 'src.data.enhanced_materials'):
                try:
                    import importlib
                    mod = importlib.import_module(module_path)
                    self._materials_enhanced = mod.MATERIALS_WITH_NRC
                    break
                except ImportError:
                    continue
            if self._materials_enhanced is None:
                self._materials_enhanced = {}
        return self._materials_enhanced

    def _get_materials_broad(self) -> Dict:
        if self._materials_broad is None:
            for module_path in ('calculations.rt60_calculator', 'src.calculations.rt60_calculator'):
                try:
                    import importlib
                    mod = importlib.import_module(module_path)
                    calc = mod.RT60Calculator()
                    self._materials_broad = calc.materials_db
                    break
                except Exception:
                    continue
            if self._materials_broad is None:
                self._materials_broad = {}
        return self._materials_broad

    def _lookup_material(self, material_key: str) -> Tuple[Dict[int, float], str, float]:
        """
        Look up a material in available databases.
        Returns (coefficients_by_freq, display_name, nrc).
        Tries the enhanced materials DB first (int-keyed coefficients),
        then the broader RT60 materials DB (string-keyed coefficients).
        """
        enhanced = self._get_materials_enhanced()
        if material_key in enhanced:
            mat = enhanced[material_key]
            raw = mat.get('absorption_coefficients', {})
            coeffs = {f: float(raw.get(f, 0.0)) for f in FREQUENCIES}
            return coeffs, mat.get('name', material_key), float(mat.get('nrc', 0.0))

        broad = self._get_materials_broad()
        if material_key in broad:
            mat = broad[material_key]
            raw = mat.get('coefficients', {})
            base = float(mat.get('nrc', mat.get('absorption_coeff', 0.0)))
            if raw:
                coeffs = {f: float(raw.get(str(f), base)) for f in FREQUENCIES}
            else:
                coeffs = {f: base for f in FREQUENCIES}
            return coeffs, mat.get('name', material_key), base

        return {f: 0.0 for f in FREQUENCIES}, material_key, 0.0

    # ------------------------------------------------------------------
    # Data computation
    # ------------------------------------------------------------------

    def _get_total_surface_area(self, space) -> float:
        """Safe total surface area calculation that avoids lazy-loaded relationships."""
        floor_area = space.floor_area or 0.0
        ceiling_area = space.ceiling_area if space.ceiling_area is not None else floor_area
        wall_area = space.wall_area or 0.0
        return floor_area + ceiling_area + wall_area

    def _compute_treated_analysis(self, space) -> Tuple[Dict[int, float], List[Dict], float]:
        """
        Build per-material surface analysis using the space's assigned materials.

        Returns:
            rt60_by_freq      – {freq: seconds} Sabine-formula RT60 at each octave band
            surface_analysis  – list of per-material dicts (see keys below)
            total_sabines_nrc – total NRC-weighted sabins for the room
        """
        volume = space.volume or 0.0
        if volume <= 0:
            return {f: 0.0 for f in FREQUENCIES}, [], 0.0

        ceiling_area = space.ceiling_area if space.ceiling_area is not None else (space.floor_area or 0.0)
        wall_area    = space.wall_area or 0.0
        floor_area   = space.floor_area or 0.0

        ceiling_mats = space.get_all_ceiling_materials()
        wall_mats    = space.get_all_wall_materials()
        floor_mats   = space.get_all_floor_materials()

        surface_groups = [
            ('Ceiling', ceiling_mats, ceiling_area),
            ('Wall',    wall_mats,    wall_area),
            ('Floor',   floor_mats,   floor_area),
        ]

        surface_analysis: List[Dict] = []
        total_absorption_by_freq: Dict[int, float] = {f: 0.0 for f in FREQUENCIES}
        total_sabines_nrc = 0.0

        for surf_type, mat_keys, total_area in surface_groups:
            if not mat_keys or total_area <= 0:
                continue
            area_per = total_area / len(mat_keys)
            for mat_key in mat_keys:
                coeffs, name, nrc = self._lookup_material(mat_key)
                absorption_by_freq = {f: area_per * coeffs[f] for f in FREQUENCIES}
                nrc_sabins = area_per * nrc
                for f in FREQUENCIES:
                    total_absorption_by_freq[f] += absorption_by_freq[f]
                total_sabines_nrc += nrc_sabins
                surface_analysis.append({
                    'surface_type':        surf_type,
                    'material_name':       name,
                    'material_key':        mat_key,
                    'area':                area_per,
                    'nrc':                 nrc,
                    'absorption_by_frequency': absorption_by_freq,
                    'total_absorption_nrc':    nrc_sabins,
                })

        rt60_by_freq: Dict[int, float] = {}
        for f in FREQUENCIES:
            a = total_absorption_by_freq[f]
            rt60_by_freq[f] = (0.049 * volume / a) if a > 0 else 999.9

        return rt60_by_freq, surface_analysis, total_sabines_nrc

    def _compute_untreated_rt60(self, space) -> Dict[int, float]:
        """
        Compute RT60 assuming bare structural surfaces (ASTM reference values).
        Ignores any assigned acoustic materials.
        """
        volume = space.volume or 0.0
        if volume <= 0:
            return {f: 0.0 for f in FREQUENCIES}

        ceiling_area = space.ceiling_area if space.ceiling_area is not None else (space.floor_area or 0.0)
        wall_area    = space.wall_area or 0.0
        floor_area   = space.floor_area or 0.0

        rt60: Dict[int, float] = {}
        for f in FREQUENCIES:
            a = (
                ceiling_area * BARE_SURFACE_COEFFICIENTS['ceiling'][f]
                + wall_area  * BARE_SURFACE_COEFFICIENTS['wall'][f]
                + floor_area * BARE_SURFACE_COEFFICIENTS['floor'][f]
            )
            rt60[f] = (0.049 * volume / a) if a > 0 else 999.9
        return rt60

    def _get_target_and_tolerance(self, space) -> Tuple[float, float]:
        """Return (target_rt60, tolerance) for this space."""
        target = space.target_rt60 if space.target_rt60 else 0.8
        tolerance = 0.1
        room_type = space.room_type or 'custom'
        for module_path in ('data.enhanced_materials', 'src.data.enhanced_materials'):
            try:
                import importlib
                mod = importlib.import_module(module_path)
                preset = mod.ROOM_TYPE_PRESETS.get(room_type, {})
                tolerance = preset.get('tolerance', 0.1)
                break
            except ImportError:
                continue
        return float(target), float(tolerance)

    def _average_rt60_speech(self, rt60_by_freq: Dict[int, float]) -> float:
        """Average RT60 across speech frequencies (250–4k Hz), excluding invalid values."""
        vals = [v for f, v in rt60_by_freq.items() if f in (250, 500, 1000, 2000, 4000) and 0 < v < 99]
        return sum(vals) / len(vals) if vals else 0.0

    # ------------------------------------------------------------------
    # Figure generation
    # ------------------------------------------------------------------

    def generate_space_figure(self, space):
        """
        Generate a letter-size (8.5×11) matplotlib Figure for one space.
        Returns a Figure object; caller is responsible for closing it.
        """
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker

        treated_rt60, surface_analysis, total_sabines_nrc = self._compute_treated_analysis(space)
        untreated_rt60 = self._compute_untreated_rt60(space)
        target, tolerance = self._get_target_and_tolerance(space)
        total_surface_area = max(self._get_total_surface_area(space), 1.0)

        fig = plt.figure(figsize=(8.5, 11))
        fig.patch.set_facecolor('white')

        # Normalized layout constants (y: 0 = bottom, 1 = top of figure)
        LM = 0.090  # left margin (normalized)
        RM = 0.955  # right edge
        W  = RM - LM

        HEADER_TOP   = 0.970
        HEADER_BOT   = 0.900
        DIVIDER_Y    = 0.898

        PLOT_TOP     = 0.883
        PLOT_BOT     = 0.565

        SECT2_LABEL_Y = 0.552   # "Surface Material Summary" label y
        SURF_TOP     = 0.540
        SURF_BOT     = 0.318

        SECT3_LABEL_Y = 0.305
        BAND_TOP     = 0.293
        BAND_BOT     = 0.048

        # ---- Header ----
        room_type_label = (space.room_type or 'Custom').replace('_', ' ').title()
        volume_str  = f"{space.volume:,.0f} cu ft" if space.volume else "N/A"
        area_str    = f"{space.floor_area:.0f} sf"  if space.floor_area else "N/A"
        target_str  = f"{target:.2f} s ± {tolerance:.2f} s"

        fig.text(LM, HEADER_TOP, space.name,
                 fontsize=14, fontweight='bold', va='top', color=_COLOR_DARK)
        fig.text(LM, HEADER_TOP - 0.024,
                 f"Room Type: {room_type_label}   |   Volume: {volume_str}"
                 f"   |   Floor Area: {area_str}   |   Target RT60: {target_str}",
                 fontsize=8, va='top', color='#444444')

        avg_treated = self._average_rt60_speech(treated_rt60)
        compliant   = abs(avg_treated - target) <= tolerance
        status_text  = 'COMPLIANT' if compliant else 'NON-COMPLIANT'
        status_color = _COLOR_GREEN if compliant else _COLOR_RED
        fig.text(RM, HEADER_TOP,
                 f"Avg RT60 (speech): {avg_treated:.2f}s   Status: {status_text}",
                 fontsize=8, va='top', ha='right',
                 color=status_color, fontweight='bold')

        # Thin divider line
        div_ax = fig.add_axes([LM, DIVIDER_Y, W, 0.0025])
        div_ax.set_facecolor(_COLOR_DARK)
        div_ax.set_xticks([])
        div_ax.set_yticks([])
        for sp in div_ax.spines.values():
            sp.set_visible(False)

        # ---- RT60 Plot ----
        ax_plot = fig.add_axes([LM + 0.01, PLOT_BOT, W - 0.02, PLOT_TOP - PLOT_BOT])

        freq_x       = FREQUENCIES
        treated_y    = [min(treated_rt60.get(f, 0.0), 12.0) for f in freq_x]
        untreated_y  = [min(untreated_rt60.get(f, 0.0), 12.0) for f in freq_x]
        target_y     = [target] * len(freq_x)
        target_lo    = [target - tolerance] * len(freq_x)
        target_hi    = [target + tolerance] * len(freq_x)

        ax_plot.set_xscale('log')
        ax_plot.set_xlim(88, 5600)
        ax_plot.set_xticks(freq_x)
        ax_plot.set_xticklabels(FREQ_LABELS, fontsize=8)
        ax_plot.xaxis.set_minor_formatter(ticker.NullFormatter())
        ax_plot.tick_params(axis='x', which='minor', bottom=False)
        ax_plot.set_xlabel('Octave Band Center Frequency (Hz)', fontsize=8.5)
        ax_plot.set_ylabel('Reverberation Time  RT60 (s)', fontsize=8.5)
        ax_plot.set_title('RT60 Frequency Response', fontsize=10, fontweight='bold', pad=5)
        ax_plot.grid(True, which='major', alpha=0.30, linewidth=0.6)
        ax_plot.grid(True, which='minor', alpha=0.10, linewidth=0.4)

        # Target band
        ax_plot.fill_between(freq_x, target_lo, target_hi,
                             alpha=0.15, color=_COLOR_BLUE, zorder=1,
                             label=f'Target band (±{tolerance:.2f}s)')
        ax_plot.plot(freq_x, target_y, color=_COLOR_BLUE, linewidth=1.6,
                     linestyle='--', marker='s', markersize=4, zorder=2,
                     label=f'Target RT60 ({target:.2f}s)')

        # Untreated (bare structure)
        ax_plot.plot(freq_x, untreated_y, color=_COLOR_GREY, linewidth=1.5,
                     linestyle=':', marker='^', markersize=5, zorder=3,
                     label='Untreated — bare structure')

        # Treated
        ax_plot.plot(freq_x, treated_y, color=_COLOR_RED, linewidth=2.2,
                     linestyle='-', marker='o', markersize=5, zorder=4,
                     label='Treated — current materials')

        # Compliance dots overlaid on treated curve
        for f, rt60_val in zip(freq_x, treated_y):
            dot_c = _COLOR_GREEN if abs(rt60_val - target) <= tolerance else _COLOR_RED
            ax_plot.plot(f, rt60_val, 'o', color=dot_c, markersize=9, alpha=0.35, zorder=5)

        # Value labels on treated curve
        for f, y_val in zip(freq_x, treated_y):
            if y_val < 11:
                ax_plot.annotate(f'{y_val:.2f}', (f, y_val),
                                 textcoords='offset points', xytext=(0, 7),
                                 ha='center', fontsize=6.5, color=_COLOR_RED)

        ax_plot.legend(fontsize=7.5, loc='upper right', framealpha=0.85)

        # ---- Surface material summary (section 2) ----
        fig.text(LM, SECT2_LABEL_Y + 0.003,
                 'Surface Material Summary',
                 fontsize=9, fontweight='bold', va='top', color=_COLOR_DARK)

        ax_surf = fig.add_axes([LM, SURF_BOT, W, SURF_TOP - SURF_BOT])
        ax_surf.axis('off')

        surf_col_labels = ['Surface', 'Material', 'Area (sf)', '% Total SA', '% Sabine Contrib.']
        surf_rows: List[List[str]] = []
        for surf in surface_analysis:
            pct_sa     = (surf['area'] / total_surface_area * 100) if total_surface_area > 0 else 0.0
            pct_sabine = (surf['total_absorption_nrc'] / total_sabines_nrc * 100) if total_sabines_nrc > 0 else 0.0
            surf_rows.append([
                surf['surface_type'],
                _truncate(surf['material_name'], 42),
                f"{surf['area']:.0f}",
                f"{pct_sa:.1f}%",
                f"{pct_sabine:.1f}%",
            ])

        if surf_rows:
            surf_tbl = ax_surf.table(
                cellText=surf_rows,
                colLabels=surf_col_labels,
                loc='upper center',
                cellLoc='center',
                bbox=[0.0, 0.0, 1.0, 1.0],
            )
            surf_tbl.auto_set_font_size(False)
            surf_tbl.set_fontsize(7.5)
            _style_table(surf_tbl, len(surf_rows), len(surf_col_labels))
            col_widths = [0.11, 0.50, 0.12, 0.135, 0.135]
            _set_col_widths(surf_tbl, col_widths, len(surf_rows))
        else:
            ax_surf.text(0.5, 0.5, 'No surface materials assigned to this space.',
                         ha='center', va='center', fontsize=9, color='#666666',
                         transform=ax_surf.transAxes)

        # ---- Per-band Sabine contribution (section 3) ----
        fig.text(LM, SECT3_LABEL_Y + 0.003,
                 'Per-Octave-Band Sabine Absorption (sabins by material)',
                 fontsize=9, fontweight='bold', va='top', color=_COLOR_DARK)

        ax_band = fig.add_axes([LM, BAND_BOT, W, BAND_TOP - BAND_BOT])
        ax_band.axis('off')

        band_col_labels = ['Surface', 'Material', '125 Hz', '250 Hz', '500 Hz', '1k Hz', '2k Hz', '4k Hz']
        band_rows: List[List[str]] = []
        for surf in surface_analysis:
            row = [surf['surface_type'], _truncate(surf['material_name'], 40)]
            for f in FREQUENCIES:
                row.append(f"{surf['absorption_by_frequency'].get(f, 0):.1f}")
            band_rows.append(row)

        # Totals row
        if surface_analysis:
            totals = ['', 'TOTAL']
            for f in FREQUENCIES:
                totals.append(f"{sum(s['absorption_by_frequency'].get(f, 0) for s in surface_analysis):.1f}")
            band_rows.append(totals)

        if band_rows:
            band_tbl = ax_band.table(
                cellText=band_rows,
                colLabels=band_col_labels,
                loc='upper center',
                cellLoc='center',
                bbox=[0.0, 0.0, 1.0, 1.0],
            )
            band_tbl.auto_set_font_size(False)
            band_tbl.set_fontsize(7.5)
            data_rows = len(band_rows) - 1  # totals row is last
            _style_table(band_tbl, data_rows, len(band_col_labels))
            # Style totals row distinctly
            for col_idx in range(len(band_col_labels)):
                cell = band_tbl[len(band_rows), col_idx]
                cell.set_facecolor('#d5e8f5')
                cell.set_text_props(fontweight='bold')
            band_col_widths = [0.10, 0.38, 0.085, 0.085, 0.085, 0.085, 0.085, 0.085]
            _set_col_widths(band_tbl, band_col_widths, len(band_rows))
        else:
            ax_band.text(0.5, 0.5, 'No surface materials assigned to this space.',
                         ha='center', va='center', fontsize=9, color='#666666',
                         transform=ax_band.transAxes)

        # ---- Footer ----
        fig.text(LM, 0.018,
                 'Acoustic Analysis Tool  |  RT60 Reverberation Report',
                 fontsize=6.5, color='#aaaaaa', va='bottom')
        fig.text(RM, 0.018,
                 f'Generated: {date.today().strftime("%B %d, %Y")}',
                 fontsize=6.5, color='#aaaaaa', va='bottom', ha='right')

        return fig

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    def export_pdf(self, space_ids: List[int], output_path: str,
                   progress_callback=None) -> Tuple[bool, str]:
        """
        Export a multi-page PDF — one page per space.
        Returns (success, message).
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages

            spaces = self._load_spaces(space_ids)
            if not spaces:
                return False, 'No spaces found for the selected IDs.'

            with PdfPages(output_path) as pdf:
                for i, space in enumerate(spaces):
                    if progress_callback:
                        progress_callback(i, len(spaces), space.name)
                    try:
                        fig = self.generate_space_figure(space)
                        pdf.savefig(fig, dpi=150, bbox_inches='tight')
                        plt.close(fig)
                    except Exception as exc:
                        logger.warning(f"Failed to generate report page for '{space.name}': {exc}",
                                       exc_info=True)

            return True, f'Exported {len(spaces)} page(s) to:\n{output_path}'
        except Exception as exc:
            logger.error(f'PDF export failed: {exc}', exc_info=True)
            return False, str(exc)

    def export_png(self, space_ids: List[int], output_folder: str,
                   progress_callback=None) -> Tuple[bool, str]:
        """
        Export one PNG image per space into output_folder.
        Returns (success, message).
        """
        try:
            import matplotlib.pyplot as plt

            os.makedirs(output_folder, exist_ok=True)
            spaces = self._load_spaces(space_ids)
            if not spaces:
                return False, 'No spaces found for the selected IDs.'

            exported: List[str] = []
            for i, space in enumerate(spaces):
                if progress_callback:
                    progress_callback(i, len(spaces), space.name)
                try:
                    fig = self.generate_space_figure(space)
                    safe = ''.join(
                        c if c.isalnum() or c in (' ', '-', '_') else '_'
                        for c in space.name
                    ).strip() or f'Space_{space.id}'
                    filepath = os.path.join(output_folder, f'{safe}_RT60_Report.png')
                    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    exported.append(filepath)
                except Exception as exc:
                    logger.warning(f"Failed to export PNG for '{space.name}': {exc}", exc_info=True)

            return True, f'Exported {len(exported)} image(s) to:\n{output_folder}'
        except Exception as exc:
            logger.error(f'PNG export failed: {exc}', exc_info=True)
            return False, str(exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_spaces(self, space_ids: List[int]):
        """Load Space ORM objects with surface_materials eagerly loaded."""
        try:
            from models import get_session
            from models.space import Space
            from sqlalchemy.orm import selectinload

            session = get_session()
            try:
                spaces = (
                    session.query(Space)
                    .options(selectinload(Space.surface_materials))
                    .filter(Space.id.in_(space_ids))
                    .order_by(Space.name)
                    .all()
                )
                # Trigger eager attribute access while session is still open
                for sp in spaces:
                    _ = sp.name, sp.volume, sp.floor_area, sp.ceiling_area
                    _ = sp.wall_area, sp.ceiling_height, sp.target_rt60, sp.room_type
                    _ = [sm.material_key for sm in sp.surface_materials]
                return spaces
            finally:
                session.close()
        except Exception as exc:
            logger.error(f'Failed to load spaces: {exc}', exc_info=True)
            return []


# ------------------------------------------------------------------
# Module-level helpers (not part of the class)
# ------------------------------------------------------------------

def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len - 1] + '…'


def _style_table(table, data_row_count: int, col_count: int):
    """Apply header styling and alternate row shading to a matplotlib Table."""
    for col in range(col_count):
        cell = table[0, col]
        cell.set_facecolor(_COLOR_DARK)
        cell.set_text_props(color='white', fontweight='bold')
    for row in range(1, data_row_count + 1):
        bg = '#f4f6f8' if row % 2 == 0 else 'white'
        for col in range(col_count):
            table[row, col].set_facecolor(bg)


def _set_col_widths(table, widths: List[float], total_rows: int):
    """Set column widths for all rows of a matplotlib Table."""
    for col_idx, cw in enumerate(widths):
        for row_idx in range(total_rows + 1):
            table[row_idx, col_idx].set_width(cw)
