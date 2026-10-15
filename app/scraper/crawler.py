import re
import urllib.parse
from collections import Counter
from typing import List, Dict, Any, Optional, Set
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.scraper.cleaner import clean_html_content
from app.scraper.search import resolve_lead_to_web

TARGET_INTERNAL_KEYWORDS = [
    "about",
    "service",
    "solution",
    "product",
    "commercial",
    "business",
    "industr",
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

async def allowed_by_robots(client: httpx.AsyncClient, url: str) -> bool:
    """Checks robots.txt courtesy. If unreachable or errored, defaults to allowed."""
    try:
        p = urllib.parse.urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        resp = await client.get(robots_url, headers=DEFAULT_HEADERS, timeout=4.0)
        if resp.status_code == 200:
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
            return rp.can_fetch(DEFAULT_HEADERS["User-Agent"], url)
        return True
    except Exception:
        return True

def extract_candidate_links(base_url: str, html: str) -> List[str]:
    """Extracts high-priority same-domain subpages."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urllib.parse.urlparse(base_url).netloc.lower().replace("www.", "")
    
    scored: Dict[str, int] = {}
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
            
        full_url = urllib.parse.urljoin(base_url, href).split("#")[0].split("?")[0].rstrip("/")
        parsed = urllib.parse.urlparse(full_url)
        link_domain = parsed.netloc.lower().replace("www.", "")
        
        if link_domain != base_domain or full_url == base_url.rstrip("/"):
            continue
            
        # Skip static media
        if re.search(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|mp4|docx?|xlsx?)$", parsed.path, re.I):
            continue
            
        haystack = (parsed.path + " " + a.get_text(" ")).lower()
        for rank, kw in enumerate(TARGET_INTERNAL_KEYWORDS):
            if kw in haystack:
                scored[full_url] = min(scored.get(full_url, 99), rank)
                break
                
    return [u for u, _ in sorted(scored.items(), key=lambda kv: kv[1])]

async def fetch_page_content(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Fetches a single page and parses clean text and metadata."""
    try:
        resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
        if resp.status_code >= 400:
            return {
                "url": url,
                "status": f"HTTP {resp.status_code}",
                "title": "",
                "meta_description": "",
                "clean_text": "",
                "lines": [],
                "error": f"HTTP {resp.status_code}"
            }
            
        cleaned = clean_html_content(resp.text)
        return {
            "url": str(resp.url),
            "status": "success",
            "title": cleaned["title"],
            "meta_description": cleaned["meta_description"],
            "clean_text": cleaned["text"],
            "lines": cleaned["lines"],
            "error": None
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "title": "",
            "meta_description": "",
            "clean_text": "",
            "lines": [],
            "error": str(e)
        }

async def crawl_lead_data(lead_input: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """
    Coordinates web discovery, robots check, multi-page crawling,
    cross-page boilerplate deduplication, and dockets.
    """
    if max_pages is None:
        max_pages = settings.MAX_CRAWL_PAGES_PER_LEAD
        
    discovery = resolve_lead_to_web(lead_input)
    target_url = discovery.get("resolved_url")
    company_name = discovery.get("company_name", lead_input)
    snippet = discovery.get("snippet", "")
    
    scraped_pages: List[Dict[str, Any]] = []
    data_quality_notes: str = ""
    validation_flags: List[str] = []

    if not target_url:
        return {
            "company_name": company_name,
            "website": None,
            "scraped_pages": [{
                "url": "N/A (Web Search Fallback)",
                "title": discovery.get("title", company_name),
                "status": "fallback_snippet",
                "char_count": len(snippet)
            }],
            "combined_text": f"Business Name: {company_name}\nContext from Web Search:\n{snippet}",
            "meta_snippet": snippet,
            "data_quality_notes": "No direct website URL found. Dossier compiled from search intelligence.",
            "validation_flags": ["Web site not found; reliant on directory snippet"]
        }

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        # Check robots.txt
        is_allowed = await allowed_by_robots(client, target_url)
        if not is_allowed:
            validation_flags.append("Scraping restricted by site's robots.txt policy")

        # Fetch Root Page
        root_res = await fetch_page_content(client, target_url)
        collected_pages = []

        if root_res["clean_text"]:
            collected_pages.append(root_res)
            
            # Fetch Secondary Pages
            if max_pages > 1:
                try:
                    r_raw = await client.get(target_url, headers=DEFAULT_HEADERS, timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
                    candidate_links = extract_candidate_links(str(r_raw.url), r_raw.text)
                    for link in candidate_links[: max_pages - 1]:
                        sub_res = await fetch_page_content(client, link)
                        if sub_res["clean_text"]:
                            collected_pages.append(sub_res)
                except Exception:
                    pass

        # Cross-page boilerplate deduplication:
        # Lines repeated across 3+ pages are shared site headers/footers
        if len(collected_pages) >= 3:
            line_counts = Counter(l.lower() for p in collected_pages for l in set(p["lines"]))
        else:
            line_counts = Counter()

        chunks: List[str] = []
        for p in collected_pages:
            # Filter repeated lines across subpages
            kept_lines = [l for l in p["lines"] if len(collected_pages) < 3 or line_counts[l.lower()] < 2]
            cleaned_body = "\n".join(kept_lines)
            
            scraped_pages.append({
                "url": p["url"],
                "title": p["title"] or "Page",
                "status": p["status"],
                "char_count": len(cleaned_body)
            })
            
            chunks.append(
                f"### PAGE: {p['url']}\n"
                f"Title: {p['title']}\n"
                f"Meta Description: {p['meta_description']}\n"
                f"{cleaned_body}\n"
            )

        if not chunks:
            # Direct crawl returned no readable text (e.g. 403, timeout, or SPA)
            domain_name = urllib.parse.urlparse(target_url).netloc.replace("www.", "")
            fallback_query = f"{company_name} {domain_name}".strip()
            fallback_snippet = snippet
            if not fallback_snippet:
                sec_discovery = resolve_lead_to_web(fallback_query)
                fallback_snippet = sec_discovery.get("snippet", "")
                if not fallback_snippet and sec_discovery.get("search_results"):
                    fallback_snippet = "\n".join(r.get("body", "") for r in sec_discovery["search_results"] if r.get("body"))

            data_quality_notes = f"Direct fetch returned {root_res.get('status') or 'Timeout/Error'}. Using search intelligence fallback."
            validation_flags.append(f"Direct crawl restricted ({root_res.get('status') or 'Timeout'}); synthesized via search engine context")
            
            scraped_pages.append({
                "url": target_url,
                "title": discovery.get("title", company_name),
                "status": root_res.get("status") or "restricted_or_timeout",
                "char_count": len(fallback_snippet)
            })
            chunks.append(
                f"### TARGET: {target_url}\n"
                f"Status: {root_res.get('status') or 'Connection Restricted'}\n"
                f"Search Snippet Intelligence:\n{fallback_snippet}\n"
            )
            snippet = fallback_snippet

    if snippet and snippet not in chunks[0]:
        chunks.append(f"### SEARCH DIRECTORY CONTEXT:\n{snippet}\n")

    full_text = "\n\n".join(chunks).strip()
    if len(full_text) > settings.MAX_TEXT_LENGTH_FOR_LLM:
        full_text = full_text[:settings.MAX_TEXT_LENGTH_FOR_LLM] + "\n...[Content truncated for context safety]..."

    return {
        "company_name": company_name,
        "website": target_url,
        "scraped_pages": scraped_pages,
        "combined_text": full_text,
        "meta_snippet": snippet,
        "data_quality_notes": data_quality_notes,
        "validation_flags": validation_flags
    }
