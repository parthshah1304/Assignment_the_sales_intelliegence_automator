import os
import re
import json
import logging
from typing import Optional, Dict, Any

from app.config import settings
from app.models import SalesBrief
from app.analyzer.prompt import SYSTEM_PROMPT, generate_analysis_user_prompt
from app.analyzer.mock_engine import generate_mock_sales_brief
from app.database import get_setting

logger = logging.getLogger("sales_intelligence.analyzer")

def clean_json_text(text: str) -> str:
    """Extracts JSON substring if wrapped in markdown code blocks or explanatory text."""
    text = text.strip()
    # Strip ```json ... ``` code fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
    return text

def parse_and_validate_brief(raw_response: str, fallback_name: str, fallback_url: Optional[str], fallback_text: str) -> SalesBrief:
    """Parses raw text into validated SalesBrief, repairing and falling back safely."""
    cleaned = clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
        
        # Ensure B2B decision is strictly 'Yes' or 'No'
        raw_decision = str(data.get("b2b_decision", "")).strip().lower()
        if "yes" in raw_decision:
            data["b2b_decision"] = "Yes"
        elif "no" in raw_decision:
            data["b2b_decision"] = "No"
        else:
            data["b2b_decision"] = "No"
            
        # Ensure confidence is float between 0 and 100
        conf = data.get("b2b_confidence", 85.0)
        try:
            conf_val = float(conf)
            if conf_val <= 1.0 and conf_val > 0.0:
                conf_val *= 100.0  # Normalized 0.85 -> 85
            data["b2b_confidence"] = min(100.0, max(0.0, conf_val))
        except Exception:
            data["b2b_confidence"] = 80.0
            
        # Ensure sales questions list has at least 3 questions
        questions = data.get("sales_questions")
        if not isinstance(questions, list) or len(questions) < 3:
            mock = generate_mock_sales_brief(fallback_name, fallback_url or "", fallback_text)
            data["sales_questions"] = mock.sales_questions
            
        return SalesBrief(**data)
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}. Falling back to semantic engine.")
        return generate_mock_sales_brief(fallback_name, fallback_url or "", fallback_text)

async def analyze_lead(
    company_name: str,
    website: Optional[str],
    dossier_text: str
) -> SalesBrief:
    """
    Main entry point for AI analysis.
    Uses dynamic settings or fallback to mock engine.
    """
    # Check if user updated provider/key via UI settings
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
            model_name = settings.GEMINI_MODEL
            
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
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
            model_name = settings.OPENAI_MODEL
            
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
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
            client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )
            model_name = settings.GROQ_MODEL
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw_text = completion.choices[0].message.content
            if raw_text:
                return parse_and_validate_brief(raw_text, company_name, website, dossier_text)
        except Exception as e:
            logger.error(f"Groq API call failed: {e}. Falling back to mock engine.")

    # 4. Default / Offline Mock Engine Fallback
    logger.info("Using built-in intelligent semantic engine (provider=mock or missing key).")
    return generate_mock_sales_brief(company_name, website or "", dossier_text)
