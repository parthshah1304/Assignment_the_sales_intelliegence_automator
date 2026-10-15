import pytest
from app.scraper.search import is_url, normalize_url, clean_query_variations

def test_is_url():
    assert is_url("https://www.houstonroofingonline.com") is True
    assert is_url("http://bostonplumbing.com/about") is True
    assert is_url("bostonplumbing.com") is True
    assert is_url("BrightPlay Turf – Chicago IL") is False
    assert is_url("Sunrise Plumbing & Drain Services – Tampa FL") is False

def test_normalize_url():
    assert normalize_url("bostonplumbing.com") == "https://bostonplumbing.com"
    assert normalize_url("https://bostonplumbing.com") == "https://bostonplumbing.com"
    assert normalize_url("http://bostonplumbing.com") == "http://bostonplumbing.com"

def test_clean_query_variations():
    variations = clean_query_variations("BrightPlay Turf – Artificial Turf & Landscaping, Chicago IL")
    assert len(variations) >= 2
    assert any("BrightPlay Turf" in v for v in variations)
