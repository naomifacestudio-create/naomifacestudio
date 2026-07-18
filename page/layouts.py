"""Katalog layout preset-a — implementacioni detalj, nevidljiv editoru."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnSpans:
    mobile: int
    tablet: int
    desktop: int


@dataclass(frozen=True)
class LayoutColumn:
    index: int
    spans: ColumnSpans


@dataclass(frozen=True)
class LayoutPreset:
    id: str
    columns: tuple[LayoutColumn, ...]


LAYOUT_PRESETS: dict[str, LayoutPreset] = {
    "one_full": LayoutPreset(
        id="one_full",
        columns=(
            LayoutColumn(index=0, spans=ColumnSpans(mobile=12, tablet=12, desktop=12)),
        ),
    ),
    "two_equal": LayoutPreset(
        id="two_equal",
        columns=(
            LayoutColumn(index=0, spans=ColumnSpans(mobile=12, tablet=6, desktop=6)),
            LayoutColumn(index=1, spans=ColumnSpans(mobile=12, tablet=6, desktop=6)),
        ),
    ),
    "two_66_33": LayoutPreset(
        id="two_66_33",
        columns=(
            LayoutColumn(index=0, spans=ColumnSpans(mobile=12, tablet=12, desktop=8)),
            LayoutColumn(index=1, spans=ColumnSpans(mobile=12, tablet=12, desktop=4)),
        ),
    ),
    "two_33_66": LayoutPreset(
        id="two_33_66",
        columns=(
            LayoutColumn(index=0, spans=ColumnSpans(mobile=12, tablet=12, desktop=4)),
            LayoutColumn(index=1, spans=ColumnSpans(mobile=12, tablet=12, desktop=8)),
        ),
    ),
    "three_equal": LayoutPreset(
        id="three_equal",
        columns=(
            LayoutColumn(index=0, spans=ColumnSpans(mobile=12, tablet=4, desktop=4)),
            LayoutColumn(index=1, spans=ColumnSpans(mobile=12, tablet=4, desktop=4)),
            LayoutColumn(index=2, spans=ColumnSpans(mobile=12, tablet=4, desktop=4)),
        ),
    ),
}


def get_layout(layout_id: str) -> LayoutPreset | None:
    return LAYOUT_PRESETS.get(layout_id)


def column_span_classes(layout_id: str, column_index: int) -> str:
    layout = get_layout(layout_id)
    if layout is None:
        return "iv-page-col col-mobile-12 col-tablet-12 col-desktop-12"

    for column in layout.columns:
        if column.index == column_index:
            spans = column.spans
            return (
                f"iv-page-col col-mobile-{spans.mobile} "
                f"col-tablet-{spans.tablet} col-desktop-{spans.desktop}"
            )

    return "iv-page-col col-mobile-12 col-tablet-12 col-desktop-12"


def build_columns_for_layout(layout_id: str) -> list[dict[str, Any]]:
    layout = get_layout(layout_id)
    if layout is None:
        return []

    return [
        {
            "id": "",
            "index": column.index,
            "blocks": [],
        }
        for column in layout.columns
    ]
