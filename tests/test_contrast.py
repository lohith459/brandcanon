import pytest
from app.core.contrast import calculate_contrast_ratio, hex_to_rgb

def test_hex_to_rgb():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("FFF") == (255, 255, 255)
    assert hex_to_rgb("#0A192F") == (10, 25, 47)
    with pytest.raises(ValueError):
        hex_to_rgb("invalid")

def test_high_contrast_passes_wcag():
    # FinEdge Navy on White
    res = calculate_contrast_ratio("#0A192F", "#FFFFFF")
    assert res.ratio > 14.0
    assert res.wcag_aa_normal_pass is True
    assert res.wcag_aaa_normal_pass is True

def test_low_contrast_fails_wcag():
    # Light gray on white
    res = calculate_contrast_ratio("#D0D0D0", "#FFFFFF")
    assert res.ratio < 3.0
    assert res.wcag_aa_normal_pass is False
    assert res.wcag_aa_large_pass is False
