import os
import io
import csv
import json
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    LeadCreate,
    LeadBatchCreate,
    LeadResponse,
    SettingsPayload
)
from app.database import (
    init_db,
    create_lead,
    get_lead,
    list_leads,
    update_lead_status,
    update_lead_brief,
    delete_lead,
    clear_all_leads,
    get_setting,
    set_setting
)
from app.pipeline import research_lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sales_intelligence")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized successfully via lifespan.")
    yield

app = FastAPI(
    title="Sales Intelligence Automator",
    description="Automated web research, scraping, and AI analysis for B2B sales discovery",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory queue / event bus for SSE progress updates
sse_subscribers = []

async def broadcast_lead_update(lead_id: int, status: str, company_name: Optional[str] = None):
    payload = json.dumps({
        "lead_id": lead_id,
        "status": status,
        "company_name": company_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    for queue in list(sse_subscribers):
        try:
            await queue.put(payload)
        except Exception:
            if queue in sse_subscribers:
                sse_subscribers.remove(queue)

async def process_single_lead_pipeline(lead_id: int, input_raw: str):
    """
    Executes the full pipeline for a lead via the decoupled research_lead engine:
    1. Status: scraping -> crawls root & subpages with boilerplate filtering
    2. Status: analyzing -> sends dossier to LLM
    3. Status: completed -> stores structured brief
    """
    try:
        logger.info(f"Starting research pipeline for Lead #{lead_id}: {input_raw}")
        update_lead_status(lead_id, "scraping")
        await broadcast_lead_update(lead_id, "scraping")

        async def progress_callback(stage: str):
            update_lead_status(lead_id, stage)
            await broadcast_lead_update(lead_id, stage)

        max_crawl_pages = int(get_setting("max_crawl_pages", str(settings.MAX_CRAWL_PAGES_PER_LEAD)))
        result = await research_lead(input_raw, max_crawl_pages=max_crawl_pages, on_progress=progress_callback)
        
        brief = result["brief"]
        company_name = result["company_name"]
        website = result["website"]
        scraped_pages = result["scraped_pages"]

        # Step 3: Persist structured brief in DB
        update_lead_brief(
            lead_id=lead_id,
            company_name=company_name,
            website=website,
            company_overview=brief.get("company_overview"),
            core_products_services=brief.get("core_products_services"),
            target_customer=brief.get("target_customer"),
            b2b_decision=brief.get("b2b_decision"),
            b2b_confidence=brief.get("b2b_confidence"),
            b2b_reasoning=brief.get("b2b_reasoning"),
            sales_questions=brief.get("sales_questions"),
            key_signals=brief.get("key_signals"),
            scraped_pages=scraped_pages,
            confidence=brief.get("confidence"),
            evidence=brief.get("evidence"),
            needs_review=brief.get("needs_review", False),
            data_quality_notes=brief.get("data_quality_notes", ""),
            validation_flags=brief.get("validation_flags", [])
        )

        logger.info(f"Successfully completed analysis for Lead #{lead_id} ({company_name}) - B2B: {brief.get('b2b_decision')}")
        await broadcast_lead_update(lead_id, "completed", company_name)

    except Exception as e:
        logger.error(f"Error processing Lead #{lead_id} ({input_raw}): {e}", exc_info=True)
        update_lead_status(lead_id, "failed", error_message=str(e))
        await broadcast_lead_update(lead_id, "failed")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

@app.post("/api/webhook/crm-lead", status_code=202)
def crm_lead_webhook(payload: LeadCreate, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for CRM integrations (e.g., Salesforce, HubSpot, Zapier).
    Accepts raw lead information asynchronously and executes the intelligence pipeline.
    """
    lead_id = create_lead(payload.input_raw)
    background_tasks.add_task(process_single_lead_pipeline, lead_id, payload.input_raw)
    return {
        "status": "accepted",
        "lead_id": lead_id,
        "input_raw": payload.input_raw,
        "message": "Lead ingested successfully from CRM webhook. Research pipeline running in background."
    }

@app.post("/api/pipeline/direct-research")
async def direct_research_endpoint(payload: LeadCreate):
    """
    Direct synchronous endpoint for external microservices or CRM functions
    that request an immediate structured dossier without saving to database.
    """
    try:
        max_crawl_pages = int(get_setting("max_crawl_pages", str(settings.MAX_CRAWL_PAGES_PER_LEAD)))
        result = await research_lead(payload.input_raw, max_crawl_pages=max_crawl_pages)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_dashboard_stats():
    leads = list_leads()
    total = len(leads)
    completed = sum(1 for l in leads if l["status"] == "completed")
    b2b_yes = sum(1 for l in leads if str(l.get("b2b_decision")).lower() == "yes")
    b2b_no = sum(1 for l in leads if str(l.get("b2b_decision")).lower() == "no")
    pending = sum(1 for l in leads if l["status"] in ("pending", "scraping", "analyzing"))
    failed = sum(1 for l in leads if l["status"] == "failed")
    return {
        "total": total,
        "completed": completed,
        "b2b_yes": b2b_yes,
        "b2b_no": b2b_no,
        "pending": pending,
        "failed": failed
    }

@app.post("/api/leads", response_model=LeadResponse)
def create_single_lead(payload: LeadCreate, background_tasks: BackgroundTasks):
    lead_id = create_lead(payload.input_raw)
    background_tasks.add_task(process_single_lead_pipeline, lead_id, payload.input_raw)
    lead = get_lead(lead_id)
    return lead

@app.post("/api/leads/batch")
def create_batch_leads(payload: LeadBatchCreate, background_tasks: BackgroundTasks):
    created_ids = []
    for item in payload.leads:
        item_str = item.strip()
        if item_str:
            lid = create_lead(item_str)
            created_ids.append(lid)
            background_tasks.add_task(process_single_lead_pipeline, lid, item_str)
    return {"message": f"Queued {len(created_ids)} leads for processing.", "lead_ids": created_ids}

@app.post("/api/leads/upload-csv")
async def upload_csv_leads(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    content = await file.read()
    decoded = content.decode("utf-8-sig", errors="ignore")
    reader = csv.reader(io.StringIO(decoded))
    
    queued = []
    for row in reader:
        if not row:
            continue
        first_col = row[0].strip()
        if first_col and first_col.lower() not in ("url", "company", "lead", "name", "website"):
            lid = create_lead(first_col)
            queued.append(lid)
            background_tasks.add_task(process_single_lead_pipeline, lid, first_col)
            
    return {"message": f"Successfully imported {len(queued)} leads from file.", "lead_ids": queued}

@app.post("/api/leads/seed-sample")
def seed_sample_leads(background_tasks: BackgroundTasks):
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_leads.txt")
    if not os.path.exists(sample_path):
        sample_path = "data/sample_leads.txt"
        
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="sample_leads.txt not found")
        
    with open(sample_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
        
    queued = []
    for lead_text in lines:
        lid = create_lead(lead_text)
        queued.append(lid)
        background_tasks.add_task(process_single_lead_pipeline, lid, lead_text)
        
    return {"message": f"Loaded and queued all {len(queued)} assignment leads.", "count": len(queued)}

@app.get("/api/leads", response_model=List[LeadResponse])
def get_leads(
    b2b_filter: Optional[str] = Query(None, description="'Yes', 'No', or None"),
    search: Optional[str] = Query(None, description="Search query")
):
    return list_leads(b2b_filter=b2b_filter, search=search)

@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
def get_single_lead(lead_id: int):
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.post("/api/leads/{lead_id}/rerun")
def rerun_lead(lead_id: int, background_tasks: BackgroundTasks):
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    update_lead_status(lead_id, "pending")
    background_tasks.add_task(process_single_lead_pipeline, lead_id, lead["input_raw"])
    return {"message": f"Lead #{lead_id} queued for re-analysis."}

@app.delete("/api/leads/{lead_id}")
def remove_lead(lead_id: int):
    success = delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": f"Lead #{lead_id} deleted."}

@app.delete("/api/leads")
def remove_all():
    clear_all_leads()
    return {"message": "All leads deleted."}

@app.get("/api/leads/export/csv")
def export_leads_csv():
    leads = list_leads()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Input Lead", "Company Name", "Website", "B2B Qualified?", "Confidence Level", "Confidence %",
        "Needs Review?", "Company Overview", "Core Products / Services", "Target Customer",
        "B2B Reasoning", "Evidence Quotes", "Sales Question 1", "Sales Question 2", "Sales Question 3", "Key Signals", "Validation Flags"
    ])
    
    for l in leads:
        sq = l.get("sales_questions") or []
        q1 = sq[0] if len(sq) > 0 else ""
        q2 = sq[1] if len(sq) > 1 else ""
        q3 = sq[2] if len(sq) > 2 else ""
        signals_str = "; ".join(l.get("key_signals") or [])
        evidence_str = " | ".join(l.get("evidence") or [])
        flags_str = "; ".join(l.get("validation_flags") or [])
        
        writer.writerow([
            l["id"],
            l["input_raw"],
            l.get("company_name") or "",
            l.get("website") or "",
            l.get("b2b_decision") or "",
            l.get("confidence") or "high",
            l.get("b2b_confidence") or "",
            "Yes" if l.get("needs_review") else "No",
            l.get("company_overview") or "",
            l.get("core_products_services") or "",
            l.get("target_customer") or "",
            l.get("b2b_reasoning") or "",
            evidence_str,
            q1, q2, q3,
            signals_str,
            flags_str
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_leads_briefs.csv"}
    )

@app.get("/api/leads/export/json")
def export_leads_json():
    leads = list_leads()
    return JSONResponse(
        content=leads,
        headers={"Content-Disposition": "attachment; filename=sales_leads_briefs.json"}
    )

@app.get("/api/settings")
def get_app_settings():
    provider = get_setting("llm_provider", settings.LLM_PROVIDER)
    gemini_key = get_setting("gemini_api_key", settings.GEMINI_API_KEY) or ""
    openai_key = get_setting("openai_api_key", settings.OPENAI_API_KEY) or ""
    groq_key = get_setting("groq_api_key", settings.GROQ_API_KEY) or ""
    
    def mask_key(k: str) -> str:
        if not k:
            return ""
        if len(k) <= 8:
            return "********"
        return k[:4] + "..." + k[-4:]

    return {
        "llm_provider": provider,
        "gemini_api_key_masked": mask_key(gemini_key),
        "has_gemini_key": bool(gemini_key),
        "openai_api_key_masked": mask_key(openai_key),
        "has_openai_key": bool(openai_key),
        "groq_api_key_masked": mask_key(groq_key),
        "has_groq_key": bool(groq_key),
        "gemini_model": settings.GEMINI_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "groq_model": settings.GROQ_MODEL,
        "max_crawl_pages": int(get_setting("max_crawl_pages", str(settings.MAX_CRAWL_PAGES_PER_LEAD)))
    }

@app.post("/api/settings")
def update_app_settings(payload: SettingsPayload):
    if payload.llm_provider:
        set_setting("llm_provider", payload.llm_provider.lower())
    if payload.gemini_api_key is not None and payload.gemini_api_key.strip():
        set_setting("gemini_api_key", payload.gemini_api_key.strip())
    if payload.openai_api_key is not None and payload.openai_api_key.strip():
        set_setting("openai_api_key", payload.openai_api_key.strip())
    if payload.groq_api_key is not None and payload.groq_api_key.strip():
        set_setting("groq_api_key", payload.groq_api_key.strip())
    if payload.max_crawl_pages_per_lead is not None:
        set_setting("max_crawl_pages", str(payload.max_crawl_pages_per_lead))
        
    return {"message": "Settings updated successfully."}

@app.get("/api/leads/stream/progress")
async def stream_progress():
    """SSE endpoint for live client updates without aggressive polling."""
    async def event_generator():
        queue = asyncio.Queue()
        sse_subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            if queue in sse_subscribers:
                sse_subscribers.remove(queue)
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Sales Intelligence Automator Backend Running</h1>"
