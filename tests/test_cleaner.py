import pytest
from app.scraper.cleaner import clean_html_content

def test_clean_html_removes_scripts_and_styles():
    html = """
    <html>
        <head>
            <title>Test Business Corp</title>
            <script>alert('malicious')</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <header>Header navigation menu</header>
            <nav><a href="/home">Home</a><a href="/about">About</a></nav>
            <div id="cookie-banner" class="cookie-consent-overlay">
                Please accept cookies to continue! Accept All
            </div>
            <main>
                <h1>Welcome to Test Business Corp</h1>
                <p>We provide commercial HVAC and mechanical systems engineering to enterprise facilities.</p>
            </main>
            <footer>Copyright 2026. All rights reserved. Privacy Policy.</footer>
        </body>
    </html>
    """
    result = clean_html_content(html)
    text = result["text"]
    title = result["title"]
    
    assert title == "Test Business Corp"
    assert "Welcome to Test Business Corp" in text
    assert "commercial HVAC and mechanical systems" in text
    # Verify boilerplate elements were eliminated
    assert "alert('malicious')" not in text
    assert "body { color: red; }" not in text
    assert "Please accept cookies" not in text
    assert "Header navigation menu" not in text
    assert "Privacy Policy" not in text

def test_clean_html_empty():
    res = clean_html_content("")
    assert res["title"] == ""
    assert res["text"] == ""
