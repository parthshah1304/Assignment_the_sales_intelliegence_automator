from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SalesBrief(BaseModel):
    company_name: str = Field(..., description="Canonical or extracted company name")
    website: Optional[str] = Field(None, description="Official website URL")
    company_overview: str = Field(..., description="Concise, high-level summary of what the company does")
    core_products_services: str = Field(..., description="Main offerings, products, or service categories")
    target_customer: str = Field(..., description="Target audience or client demographic (e.g. residential vs commercial)")
    b2b_decision: str = Field(..., description="B2B Qualification Decision: 'Yes' or 'No'")
    b2b_confidence: float = Field(..., description="Confidence score for B2B qualification (0 to 100)")
    b2b_reasoning: str = Field(..., description="Concrete justification for why the company is or isn't qualified as B2B")
    sales_questions: List[str] = Field(..., description="Exactly 3 specific, discovery questions for a sales rep")
    key_signals: List[str] = Field(default_factory=list, description="Key operational, fleet, scale, or commercial signals")

class LeadCreate(BaseModel):
    input_raw: str = Field(..., min_length=1, description="Lead URL, company name, or incomplete input")

class LeadBatchCreate(BaseModel):
    leads: List[str] = Field(..., min_length=1, description="List of raw lead strings")

class ScrapedPage(BaseModel):
    url: str
    title: str
    status: str
    char_count: int

class LeadResponse(BaseModel):
    id: int
    input_raw: str
    company_name: Optional[str] = None
    website: Optional[str] = None
    status: str  # "pending", "scraping", "analyzing", "completed", "failed"
    error_message: Optional[str] = None
    company_overview: Optional[str] = None
    core_products_services: Optional[str] = None
    target_customer: Optional[str] = None
    b2b_decision: Optional[str] = None
    b2b_confidence: Optional[float] = None
    b2b_reasoning: Optional[str] = None
    sales_questions: Optional[List[str]] = None
    key_signals: Optional[List[str]] = None
    scraped_pages: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str

class SettingsPayload(BaseModel):
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    max_crawl_pages_per_lead: Optional[int] = None
