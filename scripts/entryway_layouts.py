"""Layout presets: same cell sizes, different rectangular arrangements."""

from __future__ import annotations

from dataclasses import dataclass

from generate_entryway_storage_box import Compartment, Layout

# Fixed cell sizes from hand sketch (mm)
COL = 100.0
FRONT = 100.0
MID = 98.0
DIVIDER = 2.0
LEFT_RECEIPTS_SPAN = 20.0 + DIVIDER / 2
LEFT_CARD_SPAN = 25.0 + DIVIDER
RIGHT_CABLE_SPAN = 24.0 + DIVIDER  # shallow front bay
RIGHT_PB_SPAN = MID - RIGHT_CABLE_SPAN  # rear bay (≥60 mm clear)
LETTERS = 30.0


@dataclass(frozen=True)
class LayoutPreset:
    id: str
    name_zh: str
    name_en: str
    tagline: str
    style: str  # 3D style id
    layout: Layout | None = None  # grid-based; None = custom compartments
    custom_compartments: tuple[Compartment, ...] | None = None

    @property
    def compartments(self) -> tuple[Compartment, ...]:
        if self.custom_compartments is not None:
            return self.custom_compartments
        assert self.layout is not None
        return self.layout.compartments()

    @property
    def w_int(self) -> float:
        if self.layout is not None:
            return self.layout.w_int
        return max(c.x1 for c in self.compartments)

    @property
    def l_int(self) -> float:
        if self.layout is not None:
            return self.layout.l_int
        return max(c.y1 for c in self.compartments)

    def is_grid(self) -> bool:
        return self.layout is not None


def _core_grid(x0: float, y0: float) -> tuple[Compartment, ...]:
    """Compact cell block offset by (x0, y0)."""
    xl, xr = x0, x0 + COL
    ym = y0 + FRONT
    y_r1 = y0 + LEFT_RECEIPTS_SPAN
    y_c1 = y_r1 + LEFT_CARD_SPAN
    y_c2 = y_c1 + LEFT_CARD_SPAN
    y_cable1 = ym + RIGHT_CABLE_SPAN
    return (
        Compartment("earphones_other", xl, xl + COL, y0, y0 + FRONT, 48),
        Compartment("essential_oils", xl, xl + COL, ym, ym + MID, 82),
        Compartment("receipts", xr, xr + COL, y0, y_r1, 20),
        Compartment("card_1", xr, xr + COL, y_r1, y_c1, 12),
        Compartment("card_2", xr, xr + COL, y_c1, y_c2, 12),
        Compartment("misc_cards", xr, xr + COL, y_c2, y0 + FRONT, 28),
        Compartment("data_cable", xr, xr + COL, ym, y_cable1, 32),
        Compartment("power_banks", xr, xr + COL, y_cable1, ym + MID, 112),
    )


def _row_four_compartments() -> tuple[Compartment, ...]:
    """Four large bays in one row (door side), letters band at back — 400×130 mm."""
    y_r1 = LEFT_RECEIPTS_SPAN
    y_c1 = y_r1 + LEFT_CARD_SPAN
    y_c2 = y_c1 + LEFT_CARD_SPAN
    return (
        Compartment("earphones_other", 0, COL, 0, FRONT, 48),
        Compartment("essential_oils", COL, 2 * COL, 0, FRONT, 82),
        Compartment("receipts", 2 * COL, 3 * COL, 0, y_r1, 20),
        Compartment("card_1", 2 * COL, 3 * COL, y_r1, y_c1, 12),
        Compartment("card_2", 2 * COL, 3 * COL, y_c1, y_c2, 12),
        Compartment("misc_cards", 2 * COL, 3 * COL, y_c2, FRONT, 28),
        Compartment("data_cable", 3 * COL, 4 * COL, 0, RIGHT_CABLE_SPAN, 32),
        Compartment("power_banks", 3 * COL, 4 * COL, RIGHT_CABLE_SPAN, MID, 112),
        Compartment("letters", 0, 4 * COL, FRONT, FRONT + LETTERS, 25),
    )


def _letters_band(x0: float, x1: float, y0: float) -> Compartment:
    return Compartment("letters", x0, x1, y0, y0 + LETTERS, 25)


LAYOUT_PRESETS: dict[str, LayoutPreset] = {
    "row_four": LayoutPreset(
        id="row_four",
        name_zh="横长一行四格",
        name_en="Row of Four",
        tagline="400×130 四格一排，信件在最后（靠墙）",
        style="rounded",
        custom_compartments=_row_four_compartments(),
    ),
    "classic": LayoutPreset(
        id="classic",
        name_zh="经典紧凑",
        name_en="Classic",
        tagline="202×229 内腔 · 2 mm 挡板 · P1S 一次打印",
        style="rounded",
        layout=Layout(gutter=0, margin_x=0, margin_y=0),
    ),
    "landscape": LayoutPreset(
        id="landscape",
        name_zh="横长分块",
        name_en="Landscape Gaps",
        tagline="248×236 块间留缝，横长方形",
        style="rounded",
        layout=Layout(gutter=8, margin_x=20, margin_y=5),
    ),
    "mail_spine": LayoutPreset(
        id="mail_spine",
        name_zh="信件侧栏",
        name_en="Mail Spine",
        tagline="230×210 右侧竖信件槽，主区更整",
        style="chamfer",
        custom_compartments=(
            *_core_grid(0, 0),
            Compartment("letters", 200, 230, 0, 210, 25),
        ),
    ),
    "terrace": LayoutPreset(
        id="terrace",
        name_zh="阶梯宽边",
        name_en="Terrace",
        tagline="242×238 宽边距，像台阶托盘",
        style="tiered",
        layout=Layout(gutter=6, margin_x=18, margin_y=8),
    ),
    "gallery": LayoutPreset(
        id="gallery",
        name_zh="展示宽盒",
        name_en="Gallery",
        tagline="252×238 大留白，像陈列盒",
        style="accent",
        layout=Layout(gutter=10, margin_x=21, margin_y=4),
    ),
}


def preset_catalog() -> list[dict]:
    catalog = []
    for p in LAYOUT_PRESETS.values():
        with_brim_w = p.w_int + 4.0 + 10.0
        with_brim_l = p.l_int + 4.0 + 10.0
        catalog.append({
            "id": p.id,
            "name_zh": p.name_zh,
            "name_en": p.name_en,
            "tagline": p.tagline,
            "style": p.style,
            "internal_mm": {"width": p.w_int, "length": p.l_int},
            "p1s_with_5mm_brim_mm": {"width": with_brim_w, "length": with_brim_l},
            "p1s_compatible": with_brim_w <= 256.0 and with_brim_l <= 256.0,
            "stl": f"output/layouts/entryway_{p.id}.stl",
            "png": f"output/layouts/entryway_{p.id}_top.png",
        })
    return catalog
