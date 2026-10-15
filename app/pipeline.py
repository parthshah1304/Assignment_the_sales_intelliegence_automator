"""
Autonomous Sales Research Pipeline.
Contains pure, decoupled business logic with zero framework or database dependencies.
Can be directly imported into CRM webhooks, Celery workers, Lambda functions, or CLI tools.
"""
import logging
from typing import Dict, Any, Optional, Callable, Awaitable

from app.models import SalesBrief
from app.scraper.crawler import crawl_lead_data
from app.analyzer.llm_client import analyze_lead

logger = logging.getLogger("sales_intelligence.pipeline")

async def research_lead(
    lead_input: str,
    max_crawl_pages: Optional[int] = None,
    on_progress: Optional[Callable[[str], Awaitable[None]]] = None
) -> Dict[str, Any]:
    """
    Pure pipeline function for researching a single lead:
    1. Resolves raw input (URL, company name, imperfect location)
    2. Explores website and crawls high-priority subpages (/about, /services, /commercial)
    3. Strips cookie banners, navbars, footers, and template noise
    4. Evaluates lead against the Ideal Customer Profile (icp.md) using AI
    5. Audits verbatim evidence quotes from crawled content
    
    Returns:
        dict: Standardized dossier containing resolved URL, structured brief,
              scraped page audit, and validation flags.
    """
    lead_input = lead_input.strip()
    if not lead_input:
        raise ValueError("Lead input string cannot be empty.")
        
    logger.info(f"Pipeline executing research for: {lead_input}")

    # Step 1 & 2: Web Discovery & Deep Crawling
    if on_progress:
        try:
            await on_progress("scraping")
        except Exception as e:
            logger.debug(f"Progress callback error: {e}")

    crawl_result = await crawl_lead_data(lead_input, max_pages=max_crawl_pages)
    company_name = crawl_result.get("company_name", lead_input)
    website = crawl_result.get("website")
    scraped_pages = crawl_result.get("scraped_pages", [])
    combined_text = crawl_result.get("combined_text", "")

    # Step 3: AI / LLM Analysis & Evidence Grounding
    if on_progress:
        try:
            await on_progress("analyzing")
        except Exception as e:
            logger.debug(f"Progress callback error: {e}")

    brief: SalesBrief = await analyze_lead(company_name, website, combined_text)

    # Step 4: Consolidate crawler flags & validation
    crawler_flags = crawl_result.get("validation_flags", [])
    combined_flags = list(brief.validation_flags) + [f for f in crawler_flags if f not in brief.validation_flags]
    needs_review = brief.needs_review or bool(crawler_flags) or brief.confidence == "low"
    notes = brief.data_quality_notes or crawl_result.get("data_quality_notes", "")

    brief_dict = brief.model_dump()
    brief_dict["needs_review"] = needs_review
    brief_dict["data_quality_notes"] = notes
    brief_dict["validation_flags"] = combined_flags

    return {
        "input_raw": lead_input,
        "company_name": brief.company_name or company_name,
        "website": brief.website or website,
        "brief": brief_dict,
        "scraped_pages": scraped_pages,
        "status": "completed",
        "error": None
    }
