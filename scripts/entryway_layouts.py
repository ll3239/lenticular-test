"""Layout presets: same cell sizes, different rectangular arrangements."""

from __future__ import annotations

from dataclasses import dataclass

from generate_entryway_storage_box import Compartment, Layout

# Fixed cell sizes from hand sketch (mm)
COL = 100.0
FRONT = 100.0
MID = 80.0
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
    """Standard 200×210 cell block offset by (x0, y0)."""
    xl, xr = x0, x0 + COL
    return (
        Compartment("earphones_other", xl, xl + COL, y0, y0 + FRONT, 48),
        Compartment("essential_oils", xr, xr + COL, y0, y0 + FRONT, 82),
        Compartment("keys", xl, xl + COL, y0 + FRONT, y0 + FRONT + 20, 22),
        Compartment("card_1", xl, xl + COL, y0 + FRONT + 20, y0 + FRONT + 40, 12),
        Compartment("card_2", xl, xl + COL, y0 + FRONT + 40, y0 + FRONT + 60, 12),
        Compartment("receipts", xl, xl + COL, y0 + FRONT + 60, y0 + FRONT + MID, 28),
        Compartment("power_bank_1", xr, xr + COL, y0 + FRONT, y0 + FRONT + 30, 112),
        Compartment("power_bank_2", xr, xr + COL, y0 + FRONT + 30, y0 + FRONT + 60, 112),
        Compartment("data_cable", xr, xr + COL, y0 + FRONT + 60, y0 + FRONT + MID, 32),
    )


def _letters_band(x0: float, x1: float, y0: float) -> Compartment:
    return Compartment("letters", x0, x1, y0, y0 + LETTERS, 25)


LAYOUT_PRESETS: dict[str, LayoutPreset] = {
    "classic": LayoutPreset(
        id="classic",
        name_zh="经典紧凑",
        name_en="Classic",
        tagline="200×210 贴墙放，最省空间",
        style="minimal",
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
    return [
        {
            "id": p.id,
            "name_zh": p.name_zh,
            "name_en": p.name_en,
            "tagline": p.tagline,
            "style": p.style,
            "internal_mm": {"width": p.w_int, "length": p.l_int},
            "stl": f"output/layouts/entryway_{p.id}.stl",
            "png": f"output/layouts/entryway_{p.id}_top.png",
        }
        for p in LAYOUT_PRESETS.values()
    ]
