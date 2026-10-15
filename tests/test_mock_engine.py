import pytest
from app.analyzer.mock_engine import generate_mock_sales_brief

def test_mock_engine_commercial_roofing():
    text = "We are Houston Roofing Online. We specialize in commercial flat roofing, TPO systems, and general contractor repairs."
    brief = generate_mock_sales_brief("Houston Roofing Online", "https://www.houstonroofingonline.com", text)
    
    assert brief.company_name == "Houston Roofing Online"
    assert brief.b2b_decision == "Yes"
    assert brief.b2b_confidence >= 80.0
    assert len(brief.sales_questions) == 3
    assert "roof" in brief.core_products_services.lower()

def test_mock_engine_b2c_bakery():
    text = "Red Truck Bakery makes handcrafted fruit pies, cakes, and artisan breads shipped to your door."
    brief = generate_mock_sales_brief("Red Truck Bakery", "https://www.redtruckbakery.com", text)
    
    assert brief.b2b_decision == "No"
    assert "retail" in brief.target_customer.lower() or "consumer" in brief.target_customer.lower()
    assert len(brief.sales_questions) == 3
