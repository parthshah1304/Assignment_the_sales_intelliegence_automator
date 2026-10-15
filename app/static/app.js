// Sales Intelligence Automator Frontend Logic

let currentLeads = [];
let currentFilter = 'all';
let currentSearch = '';

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initEventSource();
    fetchLeads();
    fetchStats();
    fetchSettings();
    initEventListeners();
});

// Tab Switcher
function initTabs() {
    const tabSingle = document.getElementById('tabSingle');
    const tabBulk = document.getElementById('tabBulk');
    const tabCSV = document.getElementById('tabCSV');

    const panelSingle = document.getElementById('panelSingle');
    const panelBulk = document.getElementById('panelBulk');
    const panelCSV = document.getElementById('panelCSV');

    const setActive = (activeTab, activePanel) => {
        [tabSingle, tabBulk, tabCSV].forEach(t => {
            t.className = 'tab-btn px-3 py-1.5 text-xs font-medium rounded-md text-slate-600 hover:text-slate-900';
        });
        [panelSingle, panelBulk, panelCSV].forEach(p => p.classList.add('hidden'));

        activeTab.className = 'tab-btn px-3 py-1.5 text-xs font-medium rounded-md bg-white text-slate-800 shadow-sm border border-slate-200';
        activePanel.classList.remove('hidden');
        lucide.createIcons();
    };

    tabSingle.addEventListener('click', () => setActive(tabSingle, panelSingle));
    tabBulk.addEventListener('click', () => setActive(tabBulk, panelBulk));
    tabCSV.addEventListener('click', () => setActive(tabCSV, panelCSV));
}

// Server-Sent Events (Live Pipeline updates)
function initEventSource() {
    try {
        const evtSource = new EventSource('/api/leads/stream/progress');
        evtSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            fetchLeads(false);
            fetchStats();
        };
        evtSource.onerror = () => {
            // If SSE disconnects, fallback to gentle polling every 4s
            setTimeout(fetchLeads, 4000);
        };
    } catch (e) {
        console.warn('SSE not supported or failed, using polling fallback.');
    }
}

// Fetch Leads from Backend
async function fetchLeads(showLoading = false) {
    try {
        const res = await fetch('/api/leads');
        currentLeads = await res.json();
        renderLeads();
    } catch (e) {
        console.error('Failed to fetch leads:', e);
    }
}

// Fetch Dashboard Metrics
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('statTotal').innerText = stats.total;
        document.getElementById('statCompleted').innerText = stats.completed;
        document.getElementById('statB2BYes').innerText = stats.b2b_yes;
        document.getElementById('statPending').innerText = stats.pending;
    } catch (e) {
        console.error('Failed to fetch stats:', e);
    }
}

// Render Leads Grid
function renderLeads() {
    const container = document.getElementById('leadsContainer');
    const emptyState = document.getElementById('emptyState');

    let filtered = currentLeads.filter(lead => {
        // Filter by B2B status
        if (currentFilter === 'yes' && String(lead.b2b_decision).toLowerCase() !== 'yes') return false;
        if (currentFilter === 'no' && String(lead.b2b_decision).toLowerCase() !== 'no') return false;

        // Search query
        if (currentSearch) {
            const q = currentSearch.toLowerCase();
            const raw = (lead.input_raw || '').toLowerCase();
            const name = (lead.company_name || '').toLowerCase();
            const overview = (lead.company_overview || '').toLowerCase();
            const prod = (lead.core_products_services || '').toLowerCase();
            return raw.includes(q) || name.includes(q) || overview.includes(q) || prod.includes(q);
        }
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    container.innerHTML = filtered.map(lead => createLeadCardHtml(lead)).join('');
    lucide.createIcons();
}

function createLeadCardHtml(lead) {
    const isCompleted = lead.status === 'completed';
    const isScraping = lead.status === 'scraping';
    const isAnalyzing = lead.status === 'analyzing';
    const isFailed = lead.status === 'failed';

    let statusBadge = '';
    if (isCompleted) {
        const isB2B = String(lead.b2b_decision).toLowerCase() === 'yes';
        const b2bClass = isB2B 
            ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
            : 'bg-rose-100 text-rose-800 border-rose-200';
        statusBadge = `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${b2bClass}">
                B2B ${lead.b2b_decision || 'N/A'}
            </span>
        `;
    } else if (isScraping) {
        statusBadge = `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
                <i data-lucide="compass" class="w-3 h-3 mr-1 animate-spin"></i> Scraping Web...
            </span>
        `;
    } else if (isAnalyzing) {
        statusBadge = `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200 animate-pulse">
                <i data-lucide="cpu" class="w-3 h-3 mr-1 animate-spin"></i> AI Analyzing...
            </span>
        `;
    } else if (isFailed) {
        statusBadge = `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200">
                <i data-lucide="alert-triangle" class="w-3 h-3 mr-1"></i> Failed
            </span>
        `;
    } else {
        statusBadge = `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">
                Queued
            </span>
        `;
    }

    const title = lead.company_name || lead.input_raw;
    const website = lead.website ? `<a href="${lead.website}" target="_blank" class="text-xs text-brand-600 hover:underline flex items-center truncate max-w-[200px]" onclick="event.stopPropagation()">${lead.website.replace(/^https?:\/\//, '')} <i data-lucide="external-link" class="w-2.5 h-2.5 ml-1 inline"></i></a>` : `<span class="text-xs text-slate-400">Offline / No URL</span>`;

    const overviewTeaser = lead.company_overview 
        ? `<p class="text-xs text-slate-600 line-clamp-3 leading-relaxed">${escapeHtml(lead.company_overview)}</p>` 
        : (isFailed ? `<p class="text-xs text-rose-500 font-mono">${escapeHtml(lead.error_message || 'Error occurred during research')}</p>` : `<p class="text-xs text-slate-400 italic">Gathering intelligence from the web...</p>`);

    const pagesScrapedCount = lead.scraped_pages ? lead.scraped_pages.length : 0;
    const confLevel = (lead.confidence || 'high').toUpperCase();
    const reviewBadge = lead.needs_review ? `
        <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200" title="Flagged for human review">
            <i data-lucide="alert-circle" class="w-2.5 h-2.5 mr-1"></i> Review
        </span>
    ` : '';

    return `
        <div class="bg-white rounded-xl border border-slate-200 shadow-xs hover:shadow-md transition p-5 flex flex-col justify-between space-y-4">
            <div>
                <!-- Top Row: Title & Badge -->
                <div class="flex items-start justify-between gap-2 mb-2">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center space-x-2">
                            <h3 class="text-sm font-bold text-slate-900 truncate" title="${escapeHtml(title)}">${escapeHtml(title)}</h3>
                            ${reviewBadge}
                        </div>
                        <div class="mt-0.5">${website}</div>
                    </div>
                    <div>${statusBadge}</div>
                </div>

                <!-- Middle Content -->
                <div class="mt-3">
                    ${overviewTeaser}
                </div>
            </div>

            <!-- Bottom Row: Meta & Actions -->
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div class="flex items-center space-x-2">
                    <span title="Pages Analyzed" class="inline-flex items-center">
                        <i data-lucide="file-text" class="w-3.5 h-3.5 mr-1 text-slate-400"></i>
                        ${pagesScrapedCount} page${pagesScrapedCount === 1 ? '' : 's'}
                    </span>
                    ${lead.b2b_confidence ? `<span class="text-slate-400">•</span> <span class="font-semibold text-slate-700">${confLevel} · ${Math.round(lead.b2b_confidence)}%</span>` : ''}
                </div>

                <div class="flex items-center space-x-2">
                    ${isCompleted ? `
                        <button onclick="openBriefModal(${lead.id})" class="px-2.5 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-800 hover:bg-slate-200 transition">
                            View Brief
                        </button>
                    ` : ''}
                    <button onclick="rerunLead(${lead.id})" title="Rerun Analysis" class="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100">
                        <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
                    </button>
                    <button onclick="deleteLeadItem(${lead.id})" title="Delete Lead" class="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50">
                        <i data-lucide="trash" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Open Detailed Sales Brief Modal
function openBriefModal(leadId) {
    const lead = currentLeads.find(l => l.id === leadId);
    if (!lead) return;

    document.getElementById('modalCompanyName').innerText = lead.company_name || lead.input_raw;
    const webLink = document.getElementById('modalWebsite');
    if (lead.website) {
        webLink.href = lead.website;
        webLink.querySelector('span').innerText = lead.website;
        webLink.classList.remove('hidden');
    } else {
        webLink.classList.add('hidden');
    }

    const isB2B = String(lead.b2b_decision).toLowerCase() === 'yes';
    const badge = document.getElementById('modalB2BBadge');
    badge.innerText = `B2B ${lead.b2b_decision || 'N/A'}`;
    badge.className = isB2B 
        ? 'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300' 
        : 'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-300';

    document.getElementById('modalOverview').innerText = lead.company_overview || 'No overview available.';
    document.getElementById('modalProducts').innerText = lead.core_products_services || 'No product details extracted.';
    document.getElementById('modalAudience').innerText = lead.target_customer || 'Not specified.';
    const confLevel = (lead.confidence || 'high').toUpperCase();
    document.getElementById('modalConfidence').innerText = `Confidence: ${confLevel} (${Math.round(lead.b2b_confidence || 80)}%)`;
    document.getElementById('modalReasoning').innerText = lead.b2b_reasoning || 'No specific reasoning provided.';

    // Verbatim Evidence Quotes
    const evList = document.getElementById('modalEvidenceList');
    const evidence = lead.evidence || [];
    if (evidence.length > 0) {
        evList.innerHTML = evidence.map(q => `
            <blockquote class="pl-3 border-l-2 border-brand-500 text-xs text-slate-700 italic bg-white p-2 rounded shadow-2xs">
                "${escapeHtml(q)}"
            </blockquote>
        `).join('');
    } else {
        evList.innerHTML = `<p class="text-xs text-slate-400 italic">No verbatim quotes cited.</p>`;
    }

    // Review / Data Quality Banner
    const warnBox = document.getElementById('modalReviewWarning');
    const warnDetails = document.getElementById('modalReviewDetails');
    const flags = lead.validation_flags || [];
    const notes = lead.data_quality_notes || '';
    if (lead.needs_review || flags.length > 0 || notes) {
        let items = [...flags];
        if (notes && !items.includes(notes)) items.push(notes);
        warnDetails.innerHTML = items.map(f => `<div>• ${escapeHtml(f)}</div>`).join('');
        warnBox.classList.remove('hidden');
    } else {
        warnBox.classList.add('hidden');
    }

    // Questions List
    const qList = document.getElementById('modalQuestions');
    const questions = lead.sales_questions || [];
    if (questions.length > 0) {
        qList.innerHTML = questions.map((q, idx) => `
            <li class="bg-white p-3 rounded-lg border border-brand-200/60 shadow-xs flex items-start justify-between gap-3">
                <div class="flex items-start space-x-2">
                    <span class="w-5 h-5 rounded-full bg-brand-100 text-brand-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">${idx + 1}</span>
                    <span class="text-slate-800 leading-snug">${escapeHtml(q)}</span>
                </div>
                <button onclick="copyToClipboard('${escapeJsString(q)}', this)" class="shrink-0 p-1 text-slate-400 hover:text-brand-600 rounded hover:bg-brand-50" title="Copy Question">
                    <i data-lucide="copy" class="w-4 h-4"></i>
                </button>
            </li>
        `).join('');
    } else {
        qList.innerHTML = `<li class="text-xs text-slate-500 italic">No discovery questions generated.</li>`;
    }

    // Signals
    const sigDiv = document.getElementById('modalSignals');
    const signals = lead.key_signals || [];
    if (signals.length > 0) {
        sigDiv.innerHTML = signals.map(s => `
            <span class="inline-flex items-center px-2 py-1 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                <i data-lucide="tag" class="w-3 h-3 mr-1 text-slate-400"></i> ${escapeHtml(s)}
            </span>
        `).join('');
    } else {
        sigDiv.innerHTML = `<span class="text-xs text-slate-400 italic">None detected</span>`;
    }

    // Sources
    const srcDiv = document.getElementById('modalSources');
    const sources = lead.scraped_pages || [];
    if (sources.length > 0) {
        srcDiv.innerHTML = sources.map(p => `
            <div class="flex items-center justify-between py-1 border-b border-slate-100 last:border-0">
                <a href="${p.url}" target="_blank" class="truncate max-w-[260px] text-brand-600 hover:underline">
                    ${escapeHtml(p.title || p.url)}
                </a>
                <span class="text-[10px] text-slate-400">${p.char_count || 0} chars</span>
            </div>
        `).join('');
    } else {
        srcDiv.innerHTML = `<span class="text-slate-400 italic">No web sources</span>`;
    }

    document.getElementById('modalBrief').classList.remove('hidden');
    lucide.createIcons();
}

// Copy to Clipboard
function copyToClipboard(text, btnElement) {
    navigator.clipboard.writeText(text).then(() => {
        const original = btnElement.innerHTML;
        btnElement.innerHTML = `<i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>`;
        lucide.createIcons();
        setTimeout(() => {
            btnElement.innerHTML = original;
            lucide.createIcons();
        }, 1500);
    });
}

// Event Listeners Initialization
function initEventListeners() {
    // Single Lead Form
    document.getElementById('formSingleLead').addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('inputSingleLead');
        const val = input.value.trim();
        if (!val) return;

        try {
            await fetch('/api/leads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input_raw: val })
            });
            input.value = '';
            fetchLeads();
            fetchStats();
        } catch (err) {
            alert('Failed to submit lead: ' + err);
        }
    });

    // Bulk Lead Form
    document.getElementById('formBulkLead').addEventListener('submit', async (e) => {
        e.preventDefault();
        const textarea = document.getElementById('inputBulkLead');
        const lines = textarea.value.split('\n').map(l => l.trim()).filter(Boolean);
        if (lines.length === 0) return;

        try {
            await fetch('/api/leads/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ leads: lines })
            });
            textarea.value = '';
            fetchLeads();
            fetchStats();
        } catch (err) {
            alert('Failed to submit batch: ' + err);
        }
    });

    // 1-Click Preset Button
    document.getElementById('btnLoadSample').addEventListener('click', async () => {
        if (!confirm('Load and research the 15 leads from the assignment prompt?')) return;
        try {
            const res = await fetch('/api/leads/seed-sample', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            fetchLeads();
            fetchStats();
        } catch (err) {
            alert('Failed to load sample leads: ' + err);
        }
    });

    // CSV File Drag & Drop / Input
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileCsvInput');
    dropArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            const formData = new FormData();
            formData.append('file', e.target.files[0]);
            try {
                const res = await fetch('/api/leads/upload-csv', { method: 'POST', body: formData });
                const data = await res.json();
                alert(data.message);
                fetchLeads();
                fetchStats();
            } catch (err) {
                alert('CSV upload failed: ' + err);
            }
        }
    });

    // Filter Buttons
    document.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(b => {
                b.className = 'filter-pill px-2.5 py-1 rounded-md hover:text-slate-900';
            });
            btn.className = 'filter-pill px-2.5 py-1 rounded-md bg-white text-slate-900 shadow-xs';
            currentFilter = btn.dataset.filter;
            renderLeads();
        });
    });

    // Search input
    document.getElementById('inputSearch').addEventListener('input', (e) => {
        currentSearch = e.target.value.trim();
        renderLeads();
    });

    // Clear All
    document.getElementById('btnClearAll').addEventListener('click', async () => {
        if (!confirm('Are you sure you want to delete all leads?')) return;
        await fetch('/api/leads', { method: 'DELETE' });
        fetchLeads();
        fetchStats();
    });

    // Modal Close
    document.getElementById('btnCloseModal').addEventListener('click', () => {
        document.getElementById('modalBrief').classList.add('hidden');
    });
    document.getElementById('btnCloseModalBottom').addEventListener('click', () => {
        document.getElementById('modalBrief').classList.add('hidden');
    });

    // Settings Modal
    const modalSettings = document.getElementById('modalSettings');
    document.getElementById('btnOpenSettings').addEventListener('click', () => {
        modalSettings.classList.remove('hidden');
    });
    document.getElementById('btnCloseSettings').addEventListener('click', () => {
        modalSettings.classList.add('hidden');
    });
    document.getElementById('btnCancelSettings').addEventListener('click', () => {
        modalSettings.classList.add('hidden');
    });

    // Settings Submit
    document.getElementById('formSettings').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            llm_provider: document.getElementById('settingProvider').value,
            gemini_api_key: document.getElementById('settingGeminiKey').value,
            openai_api_key: document.getElementById('settingOpenAIKey').value,
            groq_api_key: document.getElementById('settingGroqKey').value,
            max_crawl_pages_per_lead: parseInt(document.getElementById('settingMaxPages').value)
        };
        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            modalSettings.classList.add('hidden');
            alert('Settings saved successfully!');
            fetchSettings();
        } catch (err) {
            alert('Failed to save settings: ' + err);
        }
    });
}

// Fetch Settings for Modal Inputs
async function fetchSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        document.getElementById('settingProvider').value = data.llm_provider;
        if (data.has_gemini_key) {
            document.getElementById('settingGeminiKey').placeholder = `Configured (${data.gemini_api_key_masked})`;
        }
        if (data.has_openai_key) {
            document.getElementById('settingOpenAIKey').placeholder = `Configured (${data.openai_api_key_masked})`;
        }
        if (data.has_groq_key) {
            document.getElementById('settingGroqKey').placeholder = `Configured (${data.groq_api_key_masked})`;
        }
        document.getElementById('settingMaxPages').value = data.max_crawl_pages;
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

// Rerun individual lead
async function rerunLead(leadId) {
    try {
        await fetch(`/api/leads/${leadId}/rerun`, { method: 'POST' });
        fetchLeads();
        fetchStats();
    } catch (e) {
        alert('Failed to rerun lead: ' + e);
    }
}

// Delete individual lead
async function deleteLeadItem(leadId) {
    if (!confirm('Delete this lead?')) return;
    try {
        await fetch(`/api/leads/${leadId}`, { method: 'DELETE' });
        fetchLeads();
        fetchStats();
    } catch (e) {
        alert('Failed to delete lead: ' + e);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeJsString(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n');
}
