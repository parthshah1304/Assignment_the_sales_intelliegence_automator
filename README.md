# Sales Intelligence Automator

**Author**: Parth Shah  
**GitHub Repository**: [https://github.com/parthshah1304/Assignment_the_sales_intelliegence_automator.git](https://github.com/parthshah1304/Assignment_the_sales_intelliegence_automator.git)

---

## Overview

Our sales team spends over 15 hours per week researching prospective leads before discovery calls. This manual process typically involves visiting a prospective company’s website, understanding what they do, determining whether they fit our Ideal Customer Profile (ICP), and preparing relevant discovery questions.

**Sales Intelligence Automator** is an autonomous AI-powered prospecting system designed to automate this entire research workflow. It accepts a list of potential leads—ranging from direct website URLs to raw business names and partial geographic hints—explores the web, crawls high-intent pages, strips boilerplate and cookie banners, and generates a structured, evidence-grounded **Sales Brief** for each prospect.

---

## Key Features

- **Tolerant Lead Ingestion**:
  - Direct website URLs (e.g. `https://www.houstonroofingonline.com`)
  - Company names + imperfect location strings (e.g. `BrightPlay Turf – Artificial Turf & Landscaping, Chicago IL`)
  - Free-form text area, single lead quick-add, CSV file upload, and a 1-click preset button to load the 15 assignment leads.
- **Autonomous Web Discovery & Deep Multi-Page Crawl**:
  - Resolves bare company names to candidate websites using search engine heuristics while filtering out aggregators (Yelp, YellowPages, social media).
  - Crawls root domain and prioritizes high-value sales pages (`/about`, `/services`, `/commercial`, `/solutions`).
  - Courtesy check: Respects `robots.txt` directives before scraping.
- **Aggressive Boilerplate & Noise Elimination**:
  - Strips cookie banners, GDPR consent overlays, navigation bars, footers, modal overlays, SVGs, and tracking scripts.
  - Cross-page line frequency deduplication: identifies and purges template text repeated across subpages.
- **Strict Evidence-Grounded B2B Evaluation (`icp.md`)**:
  - Uses an explicit, configurable Ideal Customer Profile ([`icp.md`](file:///k:/assignment_tasl/icp.md)).
  - B2B qualification decision is strictly **Yes** or **No**.
  - **Verbatim Evidence Verification**: Requires the LLM to cite exact quotes from the crawled text. A verification audit confirms quotes literally exist in the scraped content; any "Yes" without verifiable quotes is automatically downgraded to "No" and flagged for human review.
- **Three Discovery Sales Questions**:
  - Formulates exactly three non-generic, high-impact discovery questions tailored to the company's specific service lines, commercial capacity, or operational scaling challenges.
- **Multi-Model AI Support with Zero-Setup Offline Mode**:
  - Supported cloud models: **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o-mini`), and **Groq** (`llama-3.3-70b`).
  - **Built-In Intelligent Semantic Fallback**: Operates 100% out of the box with zero external API keys needed, ensuring effortless evaluation and reliable offline execution.
- **Modern Responsive Web Interface**:
  - Real-time pipeline updates via Server-Sent Events (SSE).
  - Instant filtering (All, B2B Qualified, B2C / Unqualified), live search, full modal inspector with copyable questions, and 1-click CSV/JSON export.

---

## System Architecture

```mermaid
flowchart TD
    subgraph UI ["Web Interface (HTML5 / Tailwind CSS / SSE)"]
        A1[Single Lead Input] --> B[FastAPI Application]
        A2[Bulk Multi-Line Input] --> B
        A3[CSV / Text Upload] --> B
        A4[1-Click Assignment Leads] --> B
    end

    subgraph Pipeline ["Research & Scrape Engine"]
        B --> C[(SQLite Database: leads.db)]
        B --> D[Background Pipeline Runner]
        D -->|Step 1: Discover| E[Search Resolution (ddgs / DuckDuckGo)]
        D -->|Step 2: Scrape & Crawl| F[Async HTTP Crawler (httpx + BeautifulSoup)]
        F --> G[robots.txt Check & Candidate Page Selection]
        G --> H[Boilerplate, Cookie & Template Stripper]
    end

    subgraph Intelligence ["AI Analysis & Grounding Layer"]
        H --> I{LLM Provider Router}
        I -->|Cloud LLM| J1[Google Gemini 2.5 Flash]
        I -->|Cloud LLM| J2[OpenAI GPT-4o-mini]
        I -->|Cloud LLM| J3[Groq Llama 3.3]
        I -->|Offline / No Key| J4[Deterministic Semantic Heuristic Engine]
        J1 --> K[Pydantic Schema Validation & JSON Repair]
        J2 --> K
        J3 --> K
        J4 --> K
        K --> L[Verbatim Evidence Substring Grounding Check]
    end

    L -->|Step 3: Persist| C
    L -->|Step 4: Live Event Stream| UI
```

---

## Project Structure

```
sales-intelligence-automator/
├── .devcontainer/
│   └── devcontainer.json        # 1-Click GitHub Codespaces environment
├── app/
│   ├── config.py                # Pydantic V2 configuration & env variables
│   ├── database.py              # SQLite storage, CRUD, schema migrations
│   ├── models.py                # Pydantic schemas (SalesBrief, LeadResponse)
│   ├── pipeline.py              # Decoupled pure research pipeline function
│   ├── main.py                  # FastAPI application, background pipeline & SSE
│   ├── scraper/
│   │   ├── cleaner.py           # Cookie banner, nav, footer, noise stripper
│   │   ├── search.py            # Search query variations & domain discovery
│   │   └── crawler.py           # Multi-page crawler, robots check, line dedupe
│   ├── analyzer/
│   │   ├── prompt.py            # System prompt with embedded icp.md
│   │   ├── llm_client.py        # Multi-provider client & evidence grounding audit
│   │   └── mock_engine.py       # Offline semantic intelligence fallback
│   └── static/
│       ├── index.html           # Modern responsive dashboard UI
│       ├── app.js               # Reactive frontend logic, SSE, filtering, modals
│       └── style.css            # Animations and modal styling
├── data/
│   ├── sample_leads.txt         # The 15 input leads from the assignment
│   └── sample_results.json      # Pre-generated output briefs for all 15 leads
├── scripts/
│   └── process_assignment_leads.py # Batch runner for processing test leads
├── tests/
│   ├── test_api.py              # API endpoint, CRM webhook, and export tests
│   ├── test_cleaner.py          # HTML noise reduction tests
│   ├── test_grounding.py        # Verbatim evidence grounding & override tests
│   ├── test_mock_engine.py      # B2B qualification and question logic tests
│   └── test_search.py           # Search query variation tests
├── icp.md                       # Explicit, editable Ideal Customer Profile
├── Dockerfile                   # Docker deployment
├── docker-compose.yml           # Docker Compose orchestration
├── requirements.txt             # Python dependencies
└── README.md                    # Setup instructions & Design Notes
```

---

## Setup & Running Instructions

### Option 1: GitHub Codespaces (Recommended)
1. Fork or open this repository in **GitHub Codespaces**.
2. The included `.devcontainer/devcontainer.json` will automatically configure Python 3.11, install all packages from `requirements.txt`, and forward port `8000`.
3. Launch the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Click **Open in Browser** when prompted.

### Option 2: Local Setup
1. Clone the repository and navigate to the project root:
   ```bash
   git clone https://github.com/parthshah1304/Assignment_the_sales_intelliegence_automator.git
   cd Assignment_the_sales_intelliegence_automator
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # On macOS / Linux:
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. *(Optional)* Configure API Keys:
   ```bash
   cp .env.example .env
   ```
   Add your `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `GROQ_API_KEY`.  
   **Note**: If no API key is set, the system automatically uses the **Built-In Offline Semantic Engine**, guaranteeing that all features, crawling, and brief generations work smoothly out of the box!
5. Start the web application:
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```
6. Open your browser to `http://localhost:8000`.

### Option 3: Docker
```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## How to Use the Web Interface

1. **Preloaded 15 Assignment Leads**:
   Click the **"Load 15 Assignment Leads"** button in the header. The system immediately queues and processes all 15 assigned leads with live SSE progress updates.
2. **Adding Custom Leads**:
   - **Quick Add**: Input single URLs (`https://www.bostonplumbing.com`) or business queries (`BrightPlay Turf – Chicago IL`).
   - **Bulk Paste**: Paste any multi-line list of leads.
   - **Upload CSV**: Upload any `.csv` or `.txt` file containing leads in the first column.
3. **Filtering & Searching**:
   - Filter leads by **All**, **B2B Qualified (Yes)**, or **B2C / Not B2B (No)**.
   - Use the live search bar to query by company name, industry keyword, or overview text.
4. **Detailed Brief Modal**:
   Click **"View Brief"** on any card to inspect:
   - Full Company Overview & Core Products/Services
   - Target Customer Demographics
   - B2B Decision with Evidence-backed Reasoning and Confidence %
   - **Verbatim Evidence Quotes** extracted directly from the crawled website
   - **Three Discovery Sales Questions** (with one-click clipboard copy buttons)
   - Operational Signals, Data Quality Notes, and Scraped Source Links
5. **Exporting Data**:
   Click **Export CSV** or **Export JSON** to download the completed prospect dataset for CRM import.
6. **Configuring AI Provider**:
   Click the **Settings** icon to switch providers (Gemini, OpenAI, Groq, or Offline Mode) and adjust crawl depth.

---

## Automated Test Suite

Run unit and integration tests using `pytest`:
```bash
pytest -v
```

All **16 test cases** pass with zero warnings, validating:
- API endpoints (`/api/health`, `/api/leads`, `/api/stats`, `/api/leads/export/csv`)
- CRM Webhook ingestion (`POST /api/webhook/crm-lead`)
- Pure microservice pipeline execution (`POST /api/pipeline/direct-research`)
- HTML boilerplate and cookie banner stripping
- Verbatim evidence substring grounding & automatic override on hallucinated quotes
- Search query normalization and variation generation
- Industry classification and discovery question generation

To re-process the 15 assigned leads via CLI:
```bash
python scripts/process_assignment_leads.py
```

---

## Design Notes

### 1. Overall System Architecture & Tooling Rationale
The system is architected as an asynchronous, event-driven web research and qualification pipeline. We chose **FastAPI** as the application framework due to its native asynchronous runtime (`async`/`await`), built-in data validation via **Pydantic V2**, automatic OpenAPI documentation (`/docs`), and lightweight performance. Scraping is executed using `httpx`, which enables non-blocking HTTP requests with connection pooling, timeouts, and realistic browser headers. For HTML processing, **BeautifulSoup4** with `lxml` was chosen for its robust DOM traversal and decomposition capabilities. The persistence layer utilizes **SQLite3** with lightweight schema migrations, providing a zero-configuration, self-contained relational store that supports concurrent read/write operations without requiring external database services. For the frontend, we chose pure HTML5, Tailwind CSS, Lucide icons, and Vanilla JavaScript with Server-Sent Events (SSE). This delivers an instant, reactive user experience without requiring node build tools or heavy client-side frameworks.

### 2. Edge Case Handling & Web Scraping Resilience
Real-world sales leads are frequently noisy, incomplete, or formatted inconsistently. Our pipeline handles these edge cases systematically:
- **Imperfect Lead Input & Domain Discovery**: When an input lacks a direct URL (e.g. `Joe's Backyard Landscaping – Phoenix AZ`), the `search.py` module cleans query variations and queries search engines to discover the business's official website while excluding directory aggregators (Yelp, YellowPages, social platforms). If a business lacks an indexed website or is unreachable, the system synthesizes a fallback profile from directory search snippets rather than crashing.
- **Aggressive Boilerplate & Noise Filtering**: Modern websites are cluttered with cookie banners, GDPR consent dialogs, promotional overlays, and legal footers. The `cleaner.py` module targets these elements using specific CSS selector heuristics (`[class*="cookie"]`, `[id*="consent"]`, `[aria-label*="cookie"]`) alongside structural decomposition (`<nav>`, `<footer>`, `<header>`, `<script>`, `<style>`). Furthermore, when crawling multiple subpages, cross-page line frequency deduplication identifies and removes repeating header/footer template strings.
- **Site Blocking & Layout Differences**: Websites employing bot shields (HTTP 403 / Cloudflare) or rendering via JavaScript are caught gracefully. The crawler records page-level fetch statuses, respects `robots.txt` courtesy rules, falls back to search engine directory snippets when direct scraping fails, and enforces a character limit (12,000 characters) to keep prompts within LLM context safety bounds.

### 3. Strict LLM Evaluation & Future Improvements
To ensure reliable, hallucination-free B2B qualification, the system uses strict prompt engineering grounded by an explicit Ideal Customer Profile defined in [`icp.md`](file:///k:/assignment_tasl/icp.md). The LLM is instructed at temperature `0.0` with structured JSON enforcement (`response_mime_type="application/json"` in Gemini and `response_format={"type": "json_object"}` in OpenAI). A business is classified as B2B only if the crawled content provides explicit evidence of commercial contracting, property management services, wholesale accounts, or B2B clients; pure direct-to-consumer businesses (such as residential lawn mowing or retail bakeries) are strictly classified as "No". 

**Evidence Grounding Audit**: A "Yes" decision requires the model to return verbatim quotes from the scraped text. Before persisting, the backend runs a substring verification audit: if the quoted text does not literally exist in the crawled content, the quotes are discarded, the decision is automatically overridden to "No", and the lead is flagged with `needs_review = True`. 

**Future Improvements with More Time**:
- **Headless Browser Integration**: Adding a Playwright or Puppeteer worker pool to fully render complex Single Page Applications (SPAs) built with client-side React/Vue.
- **Bi-Directional CRM Sync**: Building direct OAuth connectors and webhooks for HubSpot, Salesforce, and Apollo.io to push qualified leads and discovery briefs directly into sales rep workflows.
- **Automated Outreach Generation**: Generating personalized, multi-touch cold email sequences and LinkedIn outreach messages based on the three synthesized discovery questions.

---

## AI / LLM Implementation Details (Assignment FAQ)

### 1. Where the LLM is Used in the System
The LLM is invoked at the core synthesis step of the pipeline in [`app/analyzer/llm_client.py`](file:///k:/assignment_tasl/app/analyzer/llm_client.py) after the multi-page crawler and boilerplate filter have produced a clean, consolidated text dossier. It performs three critical cognitive tasks:
1. **Semantic Extraction**: Synthesizing the high-level Company Overview, Core Products/Services, and Target Customer Demographics.
2. **Strict ICP Qualification**: Evaluating the company against the Ideal Customer Profile defined in [`icp.md`](file:///k:/assignment_tasl/icp.md) to render a binary **B2B Yes/No** decision, accompanied by an evidence-backed rationale and verbatim quotes.
3. **Discovery Question Formulation**: Generating exactly three tailored, high-impact sales discovery questions that a sales executive can directly use on an introductory call.

### 2. Why We Chose That Model & Endpoint (Local vs. Cloud)
- **Primary Cloud Model**: **Google Gemini 2.5 Flash** (via the OpenAI-compatible endpoint or Google GenAI SDK).
  - *Rationale*: Sub-second latency, generous free-tier quotas (15 RPM / 1M TPM), long context windows (over 1M tokens), and native support for deterministic JSON schema output.
  - *Flexibility*: We also support **OpenAI GPT-4o-mini** and **Groq Llama 3.3 70B** through unified environment variables.
- **Local / Offline Fallback Engine**:
  - *Rationale*: To eliminate dependencies on paid API keys or network latency during evaluation, the prototype includes an intelligent rule-based semantic analyzer (`app/analyzer/mock_engine.py`). This guarantees the code can be evaluated immediately with zero configuration.

### 3. Limitations of the AI Component
- **Visibility Restricted to Crawled Text**: The LLM can only evaluate content that the scraper successfully extracts. If a website relies heavily on client-side JavaScript hydration or behind-login portals, the LLM receives less context and triggers the `needs_review` fallback flag.
- **Rate Limits on Free Tiers**: Cloud providers (e.g. Gemini or OpenAI free tier) enforce RPM thresholds that require exponential backoff on large batch runs.
- **Hallucination Risk**: Even with low temperature, LLMs may extrapolate commercial capabilities. We mitigate this through our **Verbatim Evidence Substring Grounding** check, which automatically overrides unsubstantiated "Yes" decisions.

---

## Technical Interview Walkthrough Guide

The assignment notes that the interview will cover 5 key areas. Here is how our architecture addresses each:

### 1. Problem Understanding
* **Core Problem**: Sales reps spend 15+ hours/week manually browsing websites, reading "About" pages, determining ICP fit, and writing call questions.
* **Our Approach**: We automated this research into a 4-stage pipeline: **Ingestion** (tolerant of raw text/URLs) ➔ **Discovery & Deep Crawl** (multi-page + robots check) ➔ **Noise Reduction** (cookie/nav/footer/template deduplication) ➔ **Strict Grounded Qualification** (ICP schema + verbatim evidence check + discovery questions).

### 2. System Design & Implementation
* **Scraping Strategy & Pagination**: Instead of blindly scraping links, `pick_links` ranks same-domain URLs using high-intent keywords (`/about`, `/services`, `/commercial`, `/solutions`). It avoids pagination loops and media files (`.pdf`, `.jpg`, `.zip`).
* **Sponsored Listings & Directory Filtering**: The `search.py` module maintains a directory blocklist (`yelp.com`, `yellowpages.com`, `facebook.com`, `bbb.org`) and unrolls search redirects so we only crawl the company's authentic website.
* **Platform & Layout Differences**: Rather than relying on fragile CSS selectors, we use semantic HTML fallback parsing: checking `<main>`, `<article>`, and `<h1>-<h3>` headings first, then falling back to stripped text, followed by cross-page line frequency deduplication to remove repeated site-wide templates.

### 3. AI Evaluation Logic & Specification Validation
* **Prompt Design**: System prompt embeds the exact rules from `icp.md` and enforces temperature `0.0`.
* **Strict Schema Validation**: Pydantic models enforce exact types, strict `Yes`/`No` decisions, exactly 3 discovery questions ending in `?`, and verbatim evidence quotes.
* **Evidence Substring Verification**: A custom grounding audit checks if quoted evidence exists literally in the crawled text. If an LLM hallucinates a quote, the quote is discarded and the decision is downgraded to "No".

### 4. Code Review (GitHub Codespaces)
* Clean separation of concerns:
  - `app/scraper/`: Web discovery, crawler, and cleaner.
  - `app/analyzer/`: LLM client, prompts, and offline semantic fallback.
  - `app/database.py`: SQLite storage with automatic schema migrations.
  - `app/main.py`: FastAPI endpoints and SSE event streaming.
  - `app/static/`: Reactive single-page dashboard with zero build step.

### 5. Live Modifications Readiness
* **Adding a new LLM provider**: Simply add a route in `llm_client.py`.
* **Modifying ICP criteria**: Edit `icp.md` directly without touching Python code.
* **Adjusting crawl depth**: Tweak `MAX_CRAWL_PAGES_PER_LEAD` via UI settings or `.env`.
* **Adding CRM webhooks**: Implement an outgoing `httpx.post` in `main.py:process_single_lead_pipeline`.

