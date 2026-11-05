import re
from typing import Tuple
from app.models.schemas import ContrastResponse

def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert hex string (e.g. #0A192F or 0A192F) to RGB tuple."""
    clean_hex = hex_code.strip().lstrip("#")
    if len(clean_hex) == 3:
        clean_hex = "".join([c * 2 for c in clean_hex])
    if len(clean_hex) != 6:
        raise ValueError(f"Invalid hex color format: {hex_code}")
    
    r = int(clean_hex[0:2], 16)
    g = int(clean_hex[2:4], 16)
    b = int(clean_hex[4:6], 16)
    return r, g, b

def srgb_channel_to_linear(c_srgb: float) -> float:
    """Convert 8-bit sRGB channel (0.0 to 1.0) to linear luminance component."""
    if c_srgb <= 0.04045:
        return c_srgb / 12.92
    return ((c_srgb + 0.055) / 1.055) ** 2.4

def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculate WCAG relative luminance L = 0.2126*R + 0.7152*G + 0.0722*B."""
    r_lin = srgb_channel_to_linear(rgb[0] / 255.0)
    g_lin = srgb_channel_to_linear(rgb[1] / 255.0)
    b_lin = srgb_channel_to_linear(rgb[2] / 255.0)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

def calculate_contrast_ratio(hex1: str, hex2: str) -> ContrastResponse:
    """
    Compute WCAG 2.1 relative luminance contrast ratio between foreground and background.
    Ratio = (L1 + 0.05) / (L2 + 0.05) where L1 is lighter and L2 is darker.
    """
    rgb1 = hex_to_rgb(hex1)
    rgb2 = hex_to_rgb(hex2)
    
    lum1 = relative_luminance(rgb1)
    lum2 = relative_luminance(rgb2)
    
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    ratio = round((lighter + 0.05) / (darker + 0.05), 2)
    
    aa_normal = ratio >= 4.5
    aa_large = ratio >= 3.0
    aaa_normal = ratio >= 7.0
    
    status_parts = []
    if aa_normal:
        status_parts.append("Passes WCAG AA for normal text (>= 4.5:1)")
    elif aa_large:
        status_parts.append("Passes WCAG AA for large text only (>= 3.0:1), fails normal text")
    else:
        status_parts.append("Fails WCAG AA standards (< 3.0:1)")
        
    explanation = f"Contrast ratio is {ratio}:1. {'. '.join(status_parts)}."
    
    return ContrastResponse(
        foreground_hex=hex1,
        background_hex=hex2,
        ratio=ratio,
        wcag_aa_normal_pass=aa_normal,
        wcag_aa_large_pass=aa_large,
        wcag_aaa_normal_pass=aaa_normal,
        explanation=explanation
    )
