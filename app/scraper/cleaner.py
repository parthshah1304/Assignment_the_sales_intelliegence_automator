import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List

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
    "aside",
    "select",
    "dialog",
]

BOILERPLATE_LINE = re.compile(
    r"all rights reserved|©|privacy policy|terms (of|&) (use|service)|skip to (main )?content|"
    r"accept (all )?cookies|we use cookies|sign up for|subscribe to|powered by|website by|"
    r"^(home|menu|search|login|log in|contact us|get a (free )?quote|call (us )?now)$", re.I
)

def clean_html_content(html: str) -> Dict[str, Any]:
    """
    Parses raw HTML, removes cookie banners, navigation, footers, scripts, and marketing fluff,
    and returns a clean, structured text representation.
    """
    if not html or not html.strip():
        return {"title": "", "meta_description": "", "text": "", "lines": []}
        
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Extract Page Title & Meta Description
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_desc = (md.get("content") or "").strip() if md else ""

    # 2. Remove standard structural non-content tags
    for tag_name in DISCARD_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 3. Remove cookie / consent / overlay / newsletter boilerplate
    for selector in BOILERPLATE_SELECTORS:
        try:
            for el in soup.select(selector):
                if el.name not in ["body", "html", "main", "article"]:
                    el.decompose()
        except Exception:
            continue

    # 4. Extract meaningful headings and paragraphs
    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines: List[str] = []
    seen = set()

    for element in root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        txt = element.get_text(separator=" ", strip=True)
        txt = re.sub(r"\s+", " ", txt).strip()
        if not txt or len(txt) < 3 or BOILERPLATE_LINE.search(txt):
            continue
        
        low = txt.lower()
        if low in seen:
            continue
        seen.add(low)

        if element.name in ["h1", "h2", "h3"]:
            lines.append(f"### {txt}")
        else:
            lines.append(txt)

    if len(lines) < 3:
        # Fallback to stripped strings if semantic tags were absent
        for raw in root.stripped_strings:
            clean = re.sub(r"\s+", " ", raw).strip()
            if len(clean) >= 4 and not BOILERPLATE_LINE.search(clean) and clean.lower() not in seen:
                seen.add(clean.lower())
                lines.append(clean)

    final_text = "\n".join(lines)
    return {
        "title": title,
        "meta_description": meta_desc,
        "text": final_text,
        "lines": lines
    }
