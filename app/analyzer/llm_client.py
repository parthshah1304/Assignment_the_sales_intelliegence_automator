import os
import re
import json
import logging
from typing import Optional, Dict, Any, List

from app.config import settings
from app.models import SalesBrief
from app.analyzer.prompt import SYSTEM_PROMPT, generate_analysis_user_prompt
from app.analyzer.mock_engine import generate_mock_sales_brief
from app.database import get_setting

logger = logging.getLogger("sales_intelligence.analyzer")

def clean_json_text(text: str) -> str:
    """Extracts JSON substring if wrapped in markdown code blocks or explanatory text."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
    return text

def normalize_text_for_matching(s: str) -> str:
    """Normalize text for literal substring quote matching."""
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()

def enforce_evidence_grounding(brief_data: dict, content: str) -> dict:
    """
    Validates that quotes in 'evidence' literally exist in the scraped website text.
    If the LLM claims 'Yes' without any verifiable quote in the text,
    it is downgraded to 'No' and flagged for human review.
    """
    flags = list(brief_data.get("validation_flags", []))
    haystack = normalize_text_for_matching(content)
    
    raw_evidence = brief_data.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raw_evidence = []
        
    verified_quotes = []
    for q in raw_evidence:
        if isinstance(q, str) and q.strip():
            norm_q = normalize_text_for_matching(q)
            if norm_q and norm_q in haystack:
                verified_quotes.append(q.strip())

    dropped_count = len(raw_evidence) - len(verified_quotes)
    if dropped_count > 0:
        flags.append(f"{dropped_count} unverifiable quote(s) discarded")
        
    brief_data["evidence"] = verified_quotes

    # Grounding enforcement: If B2B is Yes but no quote can be verified in the actual website text
    if not content.strip():
        brief_data["confidence"] = "low"
        brief_data["b2b_confidence"] = 50.0
        flags.append("No website content found; brief compiled from business name only")
    elif brief_data.get("b2b_decision") == "Yes" and not verified_quotes:
        brief_data["b2b_decision"] = "No"
        brief_data["confidence"] = "low"
        brief_data["b2b_confidence"] = 55.0
        orig_reason = brief_data.get("b2b_reasoning", "")
        brief_data["b2b_reasoning"] = (
            "Overridden to No: model proposed B2B Yes but cited no verifiable quotes in the crawled content. "
            f"Original reasoning: {orig_reason}"
        )
        flags.append("Yes downgraded to No (no verifiable quote found in website text)")

    brief_data["needs_review"] = brief_data.get("confidence") == "low" or bool(flags)
    brief_data["validation_flags"] = flags
    return brief_data

def parse_and_validate_brief(raw_response: str, fallback_name: str, fallback_url: Optional[str], fallback_text: str) -> SalesBrief:
    """Parses raw text into validated SalesBrief, repairing and enforcing evidence."""
    cleaned = clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
        
        # Ensure B2B decision is strictly 'Yes' or 'No'
        raw_decision = str(data.get("b2b_decision", "")).strip().lower()
        if "yes" in raw_decision:
            data["b2b_decision"] = "Yes"
        else:
            data["b2b_decision"] = "No"
            
        # Ensure confidence level and score
        conf_lvl = str(data.get("confidence", "high")).strip().lower()
        if conf_lvl not in ("high", "medium", "low"):
            conf_lvl = "medium"
        data["confidence"] = conf_lvl
        
        conf = data.get("b2b_confidence", 85.0)
        try:
            conf_val = float(conf)
            if conf_val <= 1.0 and conf_val > 0.0:
                conf_val *= 100.0
            data["b2b_confidence"] = min(100.0, max(0.0, conf_val))
        except Exception:
            data["b2b_confidence"] = 80.0
            
        # Ensure questions list has at least 3 questions
        questions = data.get("sales_questions")
        if not isinstance(questions, list) or len(questions) < 3:
            mock = generate_mock_sales_brief(fallback_name, fallback_url or "", fallback_text)
            data["sales_questions"] = mock.sales_questions

        # Enforce grounding against the scraped text
        grounded = enforce_evidence_grounding(data, fallback_text)
        return SalesBrief(**grounded)
        
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}. Falling back to semantic engine.")
        return generate_mock_sales_brief(fallback_name, fallback_url or "", fallback_text)

async def analyze_lead(
    company_name: str,
    website: Optional[str],
    dossier_text: str
) -> SalesBrief:
    """Main entry point for AI analysis with multi-provider routing and grounding."""
    provider = get_setting("llm_provider", settings.LLM_PROVIDER).lower()
    gemini_key = get_setting("gemini_api_key", settings.GEMINI_API_KEY) or os.environ.get("GEMINI_API_KEY", "")
    openai_key = get_setting("openai_api_key", settings.OPENAI_API_KEY) or os.environ.get("OPENAI_API_KEY", "")
    groq_key = get_setting("groq_api_key", settings.GROQ_API_KEY) or os.environ.get("GROQ_API_KEY", "")

    user_prompt = generate_analysis_user_prompt(company_name, website or "", dossier_text)

    # 1. Google Gemini Provider
    if provider == "gemini" and gemini_key:
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json"
                ),
            )
            if response.text:
                return parse_and_validate_brief(response.text, company_name, website, dossier_text)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}. Falling back to mock engine.")

    # 2. OpenAI Provider
    elif provider == "openai" and openai_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_key)
            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_text = completion.choices[0].message.content
            if raw_text:
                return parse_and_validate_brief(raw_text, company_name, website, dossier_text)
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}. Falling back to mock engine.")

    # 3. Groq Provider
    elif provider == "groq" and groq_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
            completion = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_text = completion.choices[0].message.content
            if raw_text:
                return parse_and_validate_brief(raw_text, company_name, website, dossier_text)
        except Exception as e:
            logger.error(f"Groq API call failed: {e}. Falling back to mock engine.")

    # 4. Built-in Offline Semantic Engine Fallback
    logger.info("Using built-in intelligent semantic engine (provider=mock or missing key).")
    return generate_mock_sales_brief(company_name, website or "", dossier_text)
