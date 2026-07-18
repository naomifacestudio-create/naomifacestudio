"""Generisanje stabilnih ID-jeva za page JSON čvorove."""

from __future__ import annotations

import secrets


def new_section_id() -> str:
    return f"sec_{secrets.token_hex(6)}"


def new_row_id() -> str:
    return f"row_{secrets.token_hex(6)}"


def new_column_id() -> str:
    return f"col_{secrets.token_hex(6)}"


def new_block_id() -> str:
    return f"blk_{secrets.token_hex(6)}"
