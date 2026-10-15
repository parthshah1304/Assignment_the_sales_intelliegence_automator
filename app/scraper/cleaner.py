import re
from bs4 import BeautifulSoup
from typing import Dict, Any

# CSS class or id keywords that typically belong to cookie banners, popups, or tracking
BOILERPLATE_SELECTORS = [
    "[class*='cookie']",
    "[id*='cookie']",
    "[class*='consent']",
    "[id*='consent']",
    "[class*='banner']",
    "[id*='banner']",
    "[class*='modal']",
    "[id*='modal']",
    "[class*='popup']",
    "[id*='popup']",
    "[class*='overlay']",
    "[class*='newsletter']",
    "[id*='newsletter']",
    "[class*='gdpr']",
    "[id*='gdpr']",
    "[aria-label*='cookie' i]",
    "[aria-label*='consent' i]",
]

DISCARD_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "noscript",
    "svg",
    "iframe",
    "object",
    "embed",
    "button",
    "form",
]

def clean_html_content(html: str) -> Dict[str, Any]:
    """
    Parses raw HTML, removes cookie banners, navigation, footers, scripts, and marketing fluff,
    and returns a clean, structured text representation.
    """
    if not html or not html.strip():
        return {"title": "", "text": ""}
        
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Extract Page Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # 2. Remove standard structural non-content tags
    for tag_name in DISCARD_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 3. Remove cookie / consent / overlay / newsletter boilerplate
    for selector in BOILERPLATE_SELECTORS:
        try:
            for el in soup.select(selector):
                # Don't delete body or main containers
                if el.name not in ["body", "html", "main", "article"]:
                    el.decompose()
        except Exception:
            continue

    # 4. Extract meaningful headings and paragraphs
    lines = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        txt = element.get_text(separator=" ", strip=True)
        if not txt:
            continue
        # Filter very short meaningless phrases like 'click here', 'read more'
        if len(txt.split()) <= 2 and txt.lower() in [
            "read more", "click here", "learn more", "submit", "menu", "close", "agree", "accept all"
        ]:
            continue
        
        # Add heading distinction
        if element.name in ["h1", "h2", "h3"]:
            lines.append(f"\n### {txt}\n")
        else:
            lines.append(txt)

    raw_text = "\n".join(lines)
    
    # If the semantic extraction was too sparse, fallback to all stripped strings
    if len(raw_text.split()) < 20:
        raw_text = " ".join(soup.stripped_strings)

    # 5. Clean whitespace and deduplicate repeated lines
    clean_lines = []
    seen = set()
    for line in raw_text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        # Avoid exact duplicates of marketing slogans repeated 5 times
        line_key = line.lower()
        if line_key in seen and len(line_key) > 40:
            continue
        seen.add(line_key)
        clean_lines.append(line)

    final_text = "\n".join(clean_lines)
    return {
        "title": title,
        "text": final_text
    }
