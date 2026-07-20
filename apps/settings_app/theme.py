"""Helpers for brand/appearance CSS variables."""

from __future__ import annotations


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def parse_hex(color: str, fallback: str = '#6366f1') -> str:
    raw = (color or '').strip().lstrip('#')
    if len(raw) == 3:
        raw = ''.join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return fallback
    try:
        int(raw, 16)
    except ValueError:
        return fallback
    return f'#{raw.lower()}'


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = parse_hex(color)
    raw = color.lstrip('#')
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f'#{_clamp(r):02x}{_clamp(g):02x}{_clamp(b):02x}'


def mix(color: str, other: str, weight: float) -> str:
    """Mix color toward other by weight (0..1)."""
    r1, g1, b1 = hex_to_rgb(color)
    r2, g2, b2 = hex_to_rgb(other)
    w = max(0.0, min(1.0, weight))
    return rgb_to_hex(
        int(r1 * (1 - w) + r2 * w),
        int(g1 * (1 - w) + g2 * w),
        int(b1 * (1 - w) + b2 * w),
    )


def darken(color: str, amount: float = 0.12) -> str:
    return mix(color, '#000000', amount)


def lighten(color: str, amount: float = 0.18) -> str:
    return mix(color, '#ffffff', amount)


def with_alpha(color: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(color)
    a = max(0.0, min(1.0, alpha))
    return f'rgba({r}, {g}, {b}, {a:.3f})'


def rgb_csv(color: str) -> str:
    r, g, b = hex_to_rgb(color)
    return f'{r}, {g}, {b}'


RADIUS_PRESETS = {
    'soft': {'radius': '18px', 'radius_sm': '12px', 'radius_xs': '8px'},
    'medium': {'radius': '14px', 'radius_sm': '10px', 'radius_xs': '6px'},
    'sharp': {'radius': '8px', 'radius_sm': '6px', 'radius_xs': '4px'},
}


def build_theme_vars(
    primary: str,
    *,
    radius_style: str = 'medium',
) -> dict[str, str]:
    primary = parse_hex(primary)
    primary_dark = darken(primary, 0.14)
    primary_light = lighten(primary, 0.16)
    radius = RADIUS_PRESETS.get(radius_style, RADIUS_PRESETS['medium'])
    return {
        'primary': primary,
        'primary_dark': primary_dark,
        'primary_light': primary_light,
        'primary_subtle': with_alpha(primary, 0.12),
        'primary_rgb': rgb_csv(primary),
        'primary_dark_rgb': rgb_csv(primary_dark),
        'primary_light_rgb': rgb_csv(primary_light),
        'sidebar_active_bg': with_alpha(primary, 0.18),
        'sidebar_active_border': primary,
        'glow_primary': with_alpha(primary, 0.35),
        'glow_primary_soft': with_alpha(primary, 0.22),
        'radius': radius['radius'],
        'radius_sm': radius['radius_sm'],
        'radius_xs': radius['radius_xs'],
        # Dark-mode brand pair (lighter primary for contrast on dark surfaces)
        'dark_primary': primary_light,
        'dark_primary_dark': primary,
        'dark_primary_light': primary_dark,
        'dark_primary_subtle': with_alpha(primary_light, 0.16),
        'dark_primary_rgb': rgb_csv(primary_light),
        'dark_sidebar_active_bg': with_alpha(primary_light, 0.18),
        'dark_sidebar_active_border': primary_light,
        'dark_glow_primary': with_alpha(primary_light, 0.4),
    }
