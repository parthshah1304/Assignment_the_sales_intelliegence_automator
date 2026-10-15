# Sales Intelligence Automator

An autonomous AI-powered prospecting engine built for modern B2B sales teams. Given an imperfect list of prospect leads (company names, website URLs, or partial location strings), this system autonomously discovers candidate websites, crawls high-intent internal pages, filters away web noise and cookie banners, and generates structured sales briefs with B2B qualification decisions and hyper-relevant discovery questions.

---

## Key Features

- **Multi-Modal Lead Input**: Accepts direct website URLs, raw company names, or partial geographic hints (e.g. `BrightPlay Turf – Chicago IL` or `Acme Roofing & Construction – Dallas TX`).
- **Autonomous Web Discovery & Deep Crawl**: Employs search engine fallback heuristics to resolve unindexed or incomplete leads to official domains, followed by an asynchronous crawler that navigates high-value pages (`/about`, `/services`, `/commercial`, `/solutions`).
- **Boilerplate & Noise Stripper**: Cleans out cookie banners, GDPR consent overlays, navigation bars, footers, SVGs, and tracking scripts to maximize LLM context efficiency.
- **Strict B2B ICP Evaluation**: Evaluates whether a company qualifies as B2B based on concrete signals (commercial contracts, property management clients, fleet operations, enterprise services) versus pure B2C retail/residential.
- **Actionable Sales Discovery**: Formulates exactly three tailored, high-impact discovery questions ready for sales reps to use on initial calls.
- **Multi-Provider AI Architecture**: Native support for **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o-mini`), **Groq** (`llama-3.3-70b`), and a **Built-In Intelligent Semantic Engine** that runs offline with zero API keys required.
- **Modern Responsive Web UI**: Real-time progress indicators via Server-Sent Events (SSE), search & filtering (B2B Yes vs No), full brief inspector modal, single/batch/CSV uploaders, 1-click preset loader, and CSV/JSON export.

---

## System Architecture

```mermaid
flowchart TD
    subgraph UI ["Web Interface (HTML5 / Tailwind CSS / Vanilla JS)"]
        A1[Single Lead Input] --> B[FastAPI Backend / REST API]
        A2[Bulk Paste List] --> B
        A3[CSV File Upload] --> B
        A4[1-Click 15 Sample Leads] --> B
    end

    subgraph Backend ["FastAPI Pipeline & Background Workers"]
        B --> C[SQLite Persistence Layer (leads.db)]
        B --> D[Research Pipeline Worker]
        D -->|Step 1: Discover| E[Search Resolution Engine (ddgs)]
        D -->|Step 2: Crawl| F[Async HTTP Crawler (httpx + BeautifulSoup)]
        F --> G[Boilerplate & Cookie Stripper]
        G -->|Step 3: Analyze| H{LLM Provider Router}
    end

    subgraph AI ["AI Intelligence Layer"]
        H -->|Cloud LLM| I1[Google Gemini 2.5 Flash]
        H -->|Cloud LLM| I2[OpenAI GPT-4o-mini]
        H -->|Cloud LLM| I3[Groq Llama 3.3]
        H -->|Offline / No Key| I4[Deterministic Semantic Heuristics Engine]
        I1 --> J[Pydantic Schema Validation & JSON Repair]
        I2 --> J
        I3 --> J
        I4 --> J
    end

    J -->|Step 4: Persist & Stream| C
    J -->|SSE Stream| UI
```

---

## Project Structure

```
sales-intelligence-automator/
├── .devcontainer/
│   └── devcontainer.json        # 1-Click GitHub Codespaces configuration
├── app/
│   ├── __init__.py
│   ├── config.py                # Environment and app configuration
│   ├── database.py              # SQLite storage, CRUD, and migrations
│   ├── models.py                # Pydantic schemas for data validation
│   ├── main.py                  # FastAPI application, background tasks, and SSE
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── cleaner.py           # Cookie banner, nav, footer & noise stripper
│   │   ├── search.py            # Search query variations & domain discovery
│   │   └── crawler.py           # Multi-page async crawler & domain navigator
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── prompt.py            # System prompt & structured JSON schema instructions
│   │   ├── llm_client.py        # Multi-provider client (Gemini, OpenAI, Groq)
│   │   └── mock_engine.py       # Offline semantic intelligence fallback
│   └── static/
│       ├── index.html           # Modern responsive dashboard
│       ├── app.js               # Reactive frontend logic, SSE, filtering, modals
│       └── style.css            # Custom animations and scrollbars
├── data/
│   ├── sample_leads.txt         # The 15 input leads specified in assignment
│   └── sample_results.json      # Pre-generated output briefs for all 15 leads
├── scripts/
│   └── process_assignment_leads.py # Batch processor for prompt test suite
├── tests/
│   ├── test_api.py              # API endpoint and export tests
│   ├── test_cleaner.py          # HTML noise reduction tests
│   ├── test_mock_engine.py      # B2B qualification and question logic tests
│   └── test_search.py           # Search query variation tests
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Quick Start & Installation

### Option 1: GitHub Codespaces (Recommended)
1. Open this repository in **GitHub Codespaces**.
2. The `.devcontainer/devcontainer.json` will automatically provision Python 3.11, install dependencies from `requirements.txt`, and forward port `8000`.
3. Start the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Click **Open in Browser** on the port notification to access the web interface.

### Option 2: Local Setup
1. Clone the repository and navigate into the folder:
   ```bash
   git clone <repo-url>
   cd sales-intelligence-automator
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
3. Install required dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. *(Optional)* Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
   Add your `GEMINI_API_KEY` or `OPENAI_API_KEY` if desired. **Note: If no API key is provided, the application automatically runs in Offline Semantic Mode, guaranteeing full functionality out of the box.**

5. Launch the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
6. Open your browser to `http://localhost:8000`.

### Option 3: Docker
```bash
docker-compose up --build
```
Navigate to `http://localhost:8000`.

---

## How to Use the Web Interface

1. **Preloaded 15 Assignment Leads**:
   Click the **"Load 15 Assignment Leads"** button in the header bar. The system will load and process all 15 assigned leads through the pipeline.
2. **Adding Leads**:
   - **Quick Add Lead**: Enter a single URL (`https://www.houstonroofingonline.com`) or business name (`BrightPlay Turf – Chicago IL`).
   - **Bulk Paste Leads**: Paste a list of URLs and names line-by-line.
   - **Upload CSV**: Upload any CSV file containing lead URLs or names in the first column.
3. **Filtering & Searching**:
   - Filter leads by **All**, **B2B Qualified (Yes)**, or **B2C / Not B2B (No)**.
   - Use the instant search box to filter by company name, industry, or overview keyword.
4. **Inspecting the Sales Brief**:
   Click **"View Brief"** on any completed card to open the modal containing:
   - High-level Company Overview
   - Core Products & Services
   - Target Customer Demographics
   - B2B Decision with Evidence-backed Reasoning and Confidence %
   - **Three Tailored Discovery Questions** (with one-click clipboard copy buttons)
   - Operational Signals & Scraped Source Pages with character counts
5. **Exporting Data**:
   Click **"Export CSV"** or **"Export JSON"** in the toolbar to download the dossier for direct CRM import.
6. **Configuring AI Settings**:
   Click the **Settings** icon (top right) to toggle between Gemini, OpenAI, Groq, or the Offline Semantic Engine, and adjust scraping depth per lead.

---

## Running the Automated Test Suite

Run unit and integration tests using `pytest`:
```bash
pytest -v
```

All 11 tests verify:
- API endpoints (`/api/health`, `/api/leads`, `/api/stats`, `/api/leads/export/csv`)
- HTML boilerplate & cookie banner elimination
- Query variation extraction & URL normalization
- B2B qualification accuracy and discovery question generation

To re-run the 15 assigned leads from the CLI:
```bash
python scripts/process_assignment_leads.py
```

---

## Design Notes

### 1. Overall System Architecture & Tooling Rationale
The system is architected as an asynchronous, event-driven web intelligence pipeline. We chose **FastAPI** as the backend backbone due to its native asynchronous runtime (`async`/`await`), built-in **Pydantic V2** data validation, and lightweight footprint compared to heavy frameworks like Django. Scraping is coordinated asynchronously with `httpx`, which allows non-blocking HTTP requests with realistic browser header spoofing and connection pooling. For parsing and extraction, **BeautifulSoup4** with `lxml` was chosen for its battle-tested DOM traversal and fine-grained element decomposition. The persistence layer relies on **SQLite3**, providing zero-config, portable relational storage with ACID guarantees, perfectly suited for rapid CRM prototyping and containerized deployments. For the frontend, we opted for clean HTML5, Tailwind CSS, Lucide icons, and modern JavaScript with Server-Sent Events (SSE). This eliminates complex node compilation/build pipelines while delivering a real-time reactive user experience.

### 2. Edge Case Handling & Web Scraping Resilience
Real-world sales prospecting involves imperfect, incomplete, or noisy inputs. Our system handles these challenges via a multi-layered defense strategy:
- **Imperfect Lead Resolution**: If an input is a plain company name or geographical description rather than a URL, the `search.py` module generates query permutations and interfaces with search discovery engines to identify the official company domain. If public search engines rate-limit or an entity lacks an active domain, the pipeline extracts directory metadata and synthesizes a fallback dossier rather than crashing.
- **Aggressive Noise Filtering**: Company websites are saturated with intrusive cookie consent modals, GDPR overlays, navigation menus, and legal footers. The `cleaner.py` module uses targeted CSS selector heuristics (`[class*="cookie"]`, `[id*="consent"]`, `[aria-label*="cookie"]`) alongside structural decomposition (`<nav>`, `<footer>`, `<header>`, `<script>`, `<style>`) and text de-duplication to extract only high-signal content.
- **Network Resilience & Layout Variations**: Sites with anti-bot shields (HTTP 403 / Cloudflare) or broken subpages are caught gracefully. The crawler records individual page statuses, falls back to search directory snippets when a direct page scrape fails, and truncates token volume within LLM context safety bounds.

### 3. Strict LLM Evaluation & Future Improvements
To prevent LLM hallucinations and enforce deterministic output, the system uses strict prompt engineering coupled with Pydantic JSON schema enforcement (`response_mime_type="application/json"` in Gemini and `response_format={"type": "json_object"}` in OpenAI). The prompt defines unambiguous qualification boundaries: a business is classified as B2B only if it provides commercial contracting, business-to-business services, property management support, or wholesale accounts; pure direct-to-consumer businesses (such as retail bakeries or residential lawn mowing) are classified as "No". In case an LLM wraps output in markdown code fences or outputs minor JSON errors, an automated sanitization and regex extraction layer repairs the response. Additionally, a built-in deterministic semantic engine provides an instant offline fallback.

**Future Improvements with More Development Time**:
- **Headless Browser Rendering**: Integrating Playwright or Puppeteer for Single Page Applications (SPAs) built with React/Angular that require JavaScript execution to render.
- **Direct CRM Bi-Directional Sync**: Adding automated webhooks and OAuth connectors for HubSpot, Salesforce, and Apollo.io to push qualified leads directly into sales cadences.
- **Automated Sales Outreach Drafting**: Extending the brief generator to automatically draft personalized, hyper-tailored cold email sequences or LinkedIn connection notes based on the three discovery questions.
