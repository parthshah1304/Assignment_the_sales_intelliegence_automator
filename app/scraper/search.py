import re
from typing import Optional, Dict, Any, List
from ddgs import DDGS

# Exclude ad links and tracking redirects where possible
BLOCKED_DOMAINS = [
    "bing.com/aclick",
    "google.com/aclk",
    "doubleclick.net",
]

def is_url(text: str) -> bool:
    """Checks whether the text looks like an HTTP/HTTPS URL or domain."""
    text = text.strip()
    return bool(re.match(r"^(https?:\/\/|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})", text, re.IGNORECASE))

def normalize_url(url: str) -> str:
    """Ensures a URL starts with http:// or https://."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url

def clean_query_variations(lead_str: str) -> List[str]:
    """Generates query variations from an imperfect lead string."""
    clean = lead_str.replace("–", "-").replace("—", "-")
    variations = []
    
    # Variation 1: Original text without special dashes
    variations.append(re.sub(r"\s+", " ", clean).strip())
    
    # Variation 2: Part before dash + location (e.g. Acme Roofing & Construction Dallas TX)
    parts = clean.split("-")
    if len(parts) > 1:
        comp_name = parts[0].strip()
        loc = parts[-1].strip()
        variations.append(f"{comp_name} {loc}")
        variations.append(comp_name)
    
    # Variation 3: Strip punctuation
    stripped = re.sub(r"[^\w\s]", " ", clean)
    variations.append(re.sub(r"\s+", " ", stripped).strip())
    
    # Deduplicate while preserving order
    out = []
    for v in variations:
        if v and v not in out:
            out.append(v)
    return out

def resolve_lead_to_web(lead_input: str) -> Dict[str, Any]:
    """
    Takes an input string (URL or company name/description),
    determines if it's already a URL or searches the web to discover the company website.
    Returns:
        {
            "is_url": bool,
            "resolved_url": Optional[str],
            "title": str,
            "snippet": str,
            "company_name": str,
            "search_results": List[dict]
        }
    """
    lead_input = lead_input.strip()
    
    # If the user already provided a URL
    if is_url(lead_input):
        target_url = normalize_url(lead_input)
        # Extract provisional company name from domain
        domain = re.sub(r"^https?:\/\/(www\.)?", "", target_url).split("/")[0]
        base_name = domain.split(".")[0].replace("-", " ").title()
        return {
            "is_url": True,
            "resolved_url": target_url,
            "title": base_name,
            "snippet": "",
            "company_name": base_name,
            "search_results": []
        }
        
    # Otherwise, it's a company name / imperfect text
    provisional_name = lead_input.split("–")[0].split("-")[0].strip()
    queries = clean_query_variations(lead_input)
    
    collected_results: List[Dict[str, str]] = []
    
    for q in queries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(q, max_results=3))
                if results:
                    for r in results:
                        href = r.get("href", "")
                        # skip blocked ad click trackers
                        if any(b in href for b in BLOCKED_DOMAINS):
                            continue
                        collected_results.append(r)
                if collected_results:
                    break
        except Exception:
            continue

    if collected_results:
        top = collected_results[0]
        resolved_url = top.get("href")
        title = top.get("title", provisional_name)
        snippet = top.get("body", "")
        return {
            "is_url": False,
            "resolved_url": resolved_url,
            "title": title,
            "snippet": snippet,
            "company_name": provisional_name,
            "search_results": collected_results
        }
        
    # Fallback if search returns nothing (e.g. fictional company name or blocked rate-limit)
    return {
        "is_url": False,
        "resolved_url": None,
        "title": provisional_name,
        "snippet": f"Business lead: {lead_input}. Local business record with no indexed public website.",
        "company_name": provisional_name,
        "search_results": []
    }
