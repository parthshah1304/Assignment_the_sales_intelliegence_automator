import re
import urllib.parse
from typing import List, Dict, Any, Optional, Set
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.scraper.cleaner import clean_html_content
from app.scraper.search import resolve_lead_to_web, normalize_url

TARGET_INTERNAL_KEYWORDS = [
    "about",
    "service",
    "solution",
    "product",
    "commercial",
    "residential",
    "company",
    "who-we-are",
    "what-we-do",
    "overview",
    "contact",
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

def extract_candidate_links(base_url: str, html: str) -> List[str]:
    """
    Extracts relevant internal links for sales intelligence
    (e.g. /about, /services, /commercial).
    """
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urllib.parse.urlparse(base_url).netloc.lower().replace("www.", "")
    
    candidates: List[str] = []
    seen: Set[str] = {base_url.rstrip("/")}
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
            continue
            
        full_url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(full_url)
        link_domain = parsed.netloc.lower().replace("www.", "")
        
        # Ensure it's internal to the same domain
        if link_domain != base_domain:
            continue
            
        norm_link = full_url.split("#")[0].split("?")[0].rstrip("/")
        if norm_link in seen:
            continue
            
        path_lower = parsed.path.lower()
        anchor_text = a.get_text(strip=True).lower()
        
        # Check if the path or anchor text contains sales-valuable keywords
        matches_keyword = any(
            kw in path_lower or kw in anchor_text
            for kw in TARGET_INTERNAL_KEYWORDS
        )
        
        if matches_keyword:
            seen.add(norm_link)
            candidates.append(full_url)
            
    return candidates

async def fetch_page_content(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Fetches a single page and cleans its HTML."""
    try:
        resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
        if resp.status_code >= 400:
            return {
                "url": url,
                "status": f"HTTP {resp.status_code}",
                "title": "",
                "clean_text": "",
                "error": f"HTTP Error {resp.status_code}"
            }
            
        cleaned = clean_html_content(resp.text)
        return {
            "url": str(resp.url),
            "status": "success",
            "title": cleaned["title"],
            "clean_text": cleaned["text"],
            "error": None
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "title": "",
            "clean_text": "",
            "error": str(e)
        }

async def crawl_lead_data(lead_input: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """
    Main scraping coordinator:
    1. Resolves lead input (URL or query) to website & metadata
    2. Fetches root page
    3. Discovers internal about/service pages
    4. Fetches and cleans up to max_pages
    5. Returns unified text dossier for LLM ingestion
    """
    if max_pages is None:
        max_pages = settings.MAX_CRAWL_PAGES_PER_LEAD
        
    discovery = resolve_lead_to_web(lead_input)
    target_url = discovery.get("resolved_url")
    company_name = discovery.get("company_name", lead_input)
    snippet = discovery.get("snippet", "")
    
    scraped_pages: List[Dict[str, Any]] = []
    combined_texts: List[str] = []
    
    # If no URL was discovered (e.g. offline business or rate limit)
    if not target_url:
        return {
            "company_name": company_name,
            "website": None,
            "scraped_pages": [
                {
                    "url": "N/A (Web Search Fallback)",
                    "title": discovery.get("title", company_name),
                    "status": "fallback_snippet",
                    "char_count": len(snippet)
                }
            ],
            "combined_text": f"Business Name / Query: {lead_input}\nContext from Web Discovery:\n{snippet}",
            "meta_snippet": snippet
        }

    # Asynchronous HTTP crawl
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        # Step 1: Fetch root/initial URL
        first_page = await fetch_page_content(client, target_url)
        
        if first_page["clean_text"]:
            page_info = {
                "url": first_page["url"],
                "title": first_page["title"] or "Home / Landing",
                "status": "success",
                "char_count": len(first_page["clean_text"])
            }
            scraped_pages.append(page_info)
            combined_texts.append(
                f"=== SOURCE PAGE: {first_page['title']} ({first_page['url']}) ===\n"
                f"{first_page['clean_text']}\n"
            )
            
            # Step 2: Discover and crawl secondary pages if max_pages > 1
            if max_pages > 1:
                # Raw html fetch to extract links if needed
                try:
                    r_root = await client.get(target_url, headers=DEFAULT_HEADERS, timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
                    sub_links = extract_candidate_links(str(r_root.url), r_root.text)
                    
                    for sub_url in sub_links[:max_pages - 1]:
                        sub_res = await fetch_page_content(client, sub_url)
                        if sub_res["clean_text"]:
                            scraped_pages.append({
                                "url": sub_res["url"],
                                "title": sub_res["title"] or "Subpage",
                                "status": "success",
                                "char_count": len(sub_res["clean_text"])
                            })
                            combined_texts.append(
                                f"=== SOURCE PAGE: {sub_res['title']} ({sub_res['url']}) ===\n"
                                f"{sub_res['clean_text']}\n"
                            )
                except Exception:
                    pass
        else:
            # Website fetch failed (blocked / 403 / down) -> Fallback to search snippet
            scraped_pages.append({
                "url": target_url,
                "title": discovery.get("title", company_name),
                "status": first_page.get("status", "failed"),
                "char_count": len(snippet)
            })
            combined_texts.append(
                f"=== TARGET URL: {target_url} (Direct scrape restricted or down) ===\n"
                f"Web Search Intelligence & Snippet:\n{snippet}\n"
            )

    # Append search discovery snippet if available for extra context
    if snippet:
        combined_texts.append(f"=== SEARCH ENGINE DIRECTORY SNIPPET ===\n{snippet}\n")
        
    full_text = "\n".join(combined_texts).strip()
    
    # Truncate text safely if exceeding LLM window limit
    if len(full_text) > settings.MAX_TEXT_LENGTH_FOR_LLM:
        full_text = full_text[:settings.MAX_TEXT_LENGTH_FOR_LLM] + "\n...[Content truncated for model context]..."

    return {
        "company_name": company_name,
        "website": target_url,
        "scraped_pages": scraped_pages,
        "combined_text": full_text,
        "meta_snippet": snippet
    }
