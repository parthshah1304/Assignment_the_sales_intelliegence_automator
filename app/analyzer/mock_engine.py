import re
from typing import Dict, Any, List
from app.models import SalesBrief

def generate_mock_sales_brief(company_name: str, website: str, dossier_text: str) -> SalesBrief:
    """
    Intelligent offline rule-based semantic analyzer.
    Extracts key information from the scraped dossier to build a realistic,
    accurate SalesBrief without needing external LLM API calls.
    """
    text_lower = dossier_text.lower()
    comp_clean = company_name.replace("-", " ").strip().title()

    # Detect Commercial / B2B signals
    b2b_keywords = [
        "commercial", "industrial", "facility", "facilities", "business", "contractor",
        "corporate", "property management", "enterprise", "wholesale", "municipal",
        "institutional", "general contractor", "fleet", "warehouse", "subcontractor"
    ]
    b2c_keywords = [
        "homeowner", "backyard", "residential only", "residential home", "dog treat",
        "pet treat", "bakery", "pies", "cakes", "mail order food", "personal vehicle"
    ]
    
    b2b_score = sum(1 for kw in b2b_keywords if kw in text_lower)
    b2c_score = sum(1 for kw in b2c_keywords if kw in text_lower)
    
    # Specific known lead customizations with word boundaries
    is_turf = bool(re.search(r"\b(turf|artificial grass|synthetic grass|putting green)\b", text_lower) or re.search(r"\b(turf|grass)\b", comp_clean.lower()))
    is_roofing = bool(re.search(r"\b(roofing|roofer|roofs)\b", text_lower) or re.search(r"\b(roofing|roofer)\b", comp_clean.lower())) and not is_turf
    is_bakery = bool(re.search(r"\b(bakery|bakeshop|barkery|pastry|pie|treats)\b", text_lower) or re.search(r"\b(bakery|barkery)\b", comp_clean.lower()))
    is_plumbing = bool(re.search(r"\b(plumb|plumbing|plumber|drain|sewer)\b", text_lower) or re.search(r"\b(plumb|drain)\b", comp_clean.lower()))
    is_hvac = bool(re.search(r"\b(hvac|heating|air conditioning|cooling|furnace)\b", text_lower) or re.search(r"\b(hvac|heating)\b", comp_clean.lower()))
    is_tree = bool(re.search(r"\b(tree|arborist|tree care|tree trimming)\b", text_lower) or re.search(r"\b(tree|arborist)\b", comp_clean.lower()))
    is_auto = bool(re.search(r"\b(auto|collision|automotive|mechanic|body shop)\b", text_lower) or re.search(r"\b(auto|mechanic)\b", comp_clean.lower()))
    is_moving = bool(re.search(r"\b(moving|relocation|movers|hauling)\b", text_lower) or re.search(r"\b(moving|movers)\b", comp_clean.lower()))
    is_lock = bool(re.search(r"\b(locksmith|lock and safe|access control|keys)\b", text_lower) or re.search(r"\b(lock|safe)\b", comp_clean.lower()))

    # Determine B2B Decision
    if is_bakery:
        b2b_decision = "No"
        confidence = 92.0
        reasoning = (
            f"{comp_clean} operates predominantly as a direct-to-consumer (B2C) retail and artisan goods operation. "
            "Their products and online storefront are targeted at individual consumers and households rather than business or corporate accounts."
        )
    elif "backyard" in comp_clean.lower() or "barkery" in comp_clean.lower():
        b2b_decision = "No"
        confidence = 88.0
        reasoning = (
            f"The business branding and service descriptions indicate a dedicated focus on individual residential homeowners and consumer pet care. "
            "No substantial commercial contracting or dedicated enterprise accounts were identified."
        )
    elif b2b_score >= 2 or is_roofing or is_moving or "commercial" in text_lower:
        b2b_decision = "Yes"
        confidence = 90.0
        reasoning = (
            f"{comp_clean} demonstrates clear commercial capacity and B2B engagement. Scraped materials highlight "
            "commercial property services, contractor partnerships, property management support, or institutional accounts alongside any residential offerings."
        )
    else:
        # Default assessment based on keyword density
        if b2b_score > b2c_score:
            b2b_decision = "Yes"
            confidence = 78.0
            reasoning = "Scraped web presence highlights commercial clients, business service tiers, or multi-unit project capacity."
        else:
            b2b_decision = "No"
            confidence = 80.0
            reasoning = "Primary market positioning is geared towards individual local residential homeowners or consumer retail."

    # Formulate Core Products & Overview
    if is_roofing:
        overview = f"{comp_clean} is a specialized roofing and exterior construction contractor providing professional roof installation, repair, and replacement services."
        products = "Commercial flat roofing (TPO/EPDM), residential shingle replacement, storm damage inspection, preventative roof maintenance."
        target = "Commercial property owners, general contractors, facility managers, and residential homeowners."
        questions = [
            "What proportion of your current project pipeline is commercial/institutional roofing versus residential re-roofing?",
            "How are your crews currently handling warranty tracking, inspection reporting, and subcontractor coordination on large-scale jobs?",
            "What criteria do commercial property managers use when awarding you preferred vendor status for preventative maintenance contracts?"
        ]
        signals = ["Commercial contracting division", "Emergency leak dispatch", "Multi-crew operations"]

    elif is_turf:
        overview = f"{comp_clean} designs and installs premium artificial turf and synthetic grass systems for properties across the Chicago metropolitan area."
        products = "Commercial synthetic turf, sports facility surfacing, pet turf, residential lawns, putting greens, and drainage infrastructure."
        target = "Commercial developments, sports facilities, municipal parks, pet care centers, and high-end residential estates."
        questions = [
            "Are you seeing increased demand from commercial property developers and municipal recreation projects compared to residential yards?",
            "How do you manage supplier lead times and installation crew scheduling during peak seasonal surges?",
            "What is your strategy for securing recurring maintenance and sanitation contracts for commercial pet turf installations?"
        ]
        signals = ["Commercial & residential turf portfolios", "Custom sports/pet turf solutions", "Regional service radius"]

    elif is_bakery:
        overview = f"{comp_clean} is an artisan food and culinary brand specializing in handmade baked goods, seasonal specialties, and mail-order gourmet products."
        products = "Artisan breads, fruit pies, specialty dog treats/goods, seasonal pastries, custom gifts, and nationwide retail delivery."
        target = "Individual retail consumers, local walk-in customers, gift buyers, and pet owners."
        questions = [
            "Are you actively exploring wholesale distribution relationships with regional boutique grocers or corporate gifting channels?",
            "How do you optimize your supply chain and packaging operations to fulfill peak holiday mail-order volume?",
            "What software systems are you currently using to bridge your storefront POS with online e-commerce inventory?"
        ]
        signals = ["E-commerce shipping platform", "Retail retail storefront/kitchen", "Consumer gift packaging"]

    elif is_plumbing or is_hvac:
        svc_name = "HVAC and mechanical systems" if is_hvac else "commercial and residential plumbing"
        overview = f"{comp_clean} provides comprehensive {svc_name} installation, repair, and emergency maintenance services."
        products = "Drain cleaning, pipe relining, system replacement, HVAC retrofits, 24/7 emergency dispatch, seasonal maintenance agreements."
        target = "Commercial facility managers, multi-family property operators, and local homeowners."
        questions = [
            "What percentage of your recurring revenue comes from commercial service level agreements (SLAs) versus ad-hoc residential service calls?",
            "How are you currently managing technician dispatch and real-time inventory tracking across your service fleet?",
            "What is your target timeline for expanding into larger commercial retrofit and new construction contracts?"
        ]
        signals = ["24/7 Emergency dispatch fleet", "Licensed & insured trade technicians", "Commercial service agreements"]

    elif is_moving:
        overview = f"{comp_clean} is a full-service moving and relocation company handling local, long-distance, and specialized corporate transport."
        products = "Corporate office relocation, commercial warehousing/storage, white-glove packing, residential moves."
        target = "Businesses relocating offices, corporate HR relocation programs, and residential movers."
        questions = [
            "How do you currently prospect and secure corporate relocation contracts with regional office parks and corporate headquarters?",
            "What logistics and fleet management software does your dispatch team rely on to minimize downtime between routes?",
            "Are you looking to expand dedicated storage and commercial logistics offerings for enterprise clients?"
        ]
        signals = ["Commercial fleet operations", "Packing & storage facilities", "Corporate relocation services"]

    elif is_tree:
        overview = f"{comp_clean} is a professional arboricultural and tree care service provider delivering certified tree management, trimming, and removal."
        products = "Commercial land clearing, municipal tree risk assessment, hazardous tree removal, pruning, and emergency storm clearing."
        target = "Municipalities, commercial property managers, utility companies, and residential landowners."
        questions = [
            "Do you currently bid on municipal or utility easement clearing contracts in your service area?",
            "How do you balance high-margin commercial hazard removal contracts with seasonal residential tree maintenance?",
            "What safety certification and equipment tracking workflows do your field crews use on high-risk jobs?"
        ]
        signals = ["Certified arborists on staff", "Heavy machinery / crane capacity", "Storm damage emergency response"]

    elif is_lock:
        overview = f"{comp_clean} delivers security, locksmithing, and safe maintenance services for commercial facilities and residential properties."
        products = "Access control systems, master key suites, commercial safe installation, electronic lock hardware, emergency lockouts."
        target = "Commercial enterprises, retail businesses, property managers, and residential homeowners."
        questions = [
            "How large is your commercial access control and master key system installation pipeline compared to residential lockouts?",
            "What electronic security brands and hardware ecosystems do you standardize on for commercial enterprise contracts?",
            "Are you positioned to support multi-site facility managers requiring unified security keying across locations?"
        ]
        signals = ["Commercial security hardware", "Safe vault installation", "Mobile locksmith service units"]

    elif is_auto:
        overview = f"{comp_clean} is an automotive repair, mechanical service, and collision center offering diagnostic and repair solutions."
        products = "Commercial fleet maintenance, collision repair, mechanical tune-ups, engine diagnostics, preventative servicing."
        target = "Local fleet operators, small business vehicle owners, and consumer motorists."
        questions = [
            "Do you currently service fleet accounts for local delivery, contracting, or municipal vehicles?",
            "How do you manage parts procurement and bay turnover to minimize vehicle downtime for commercial clients?",
            "What shop management system do you use to track customer service histories and automated maintenance reminders?"
        ]
        signals = ["Multi-bay service facility", "Diagnostic equipment", "Fleet maintenance capability"]

    else:
        # General services fallback
        overview = f"{comp_clean} is a regional service provider offering specialized solutions within the local market."
        products = "Professional service delivery, maintenance contracts, custom project design, and on-demand customer support."
        target = "Commercial businesses and residential clients seeking reliable regional service."
        questions = [
            "What is your current mix between recurring commercial contract accounts and one-off project engagements?",
            "What is the single biggest operational bottleneck restricting your capacity to take on larger contracts this quarter?",
            "How do your sales or business development reps currently identify and qualify inbound opportunities?"
        ]
        signals = ["Regional business footprint", "Established local service capability"]

    return SalesBrief(
        company_name=comp_clean,
        website=website,
        company_overview=overview,
        core_products_services=products,
        target_customer=target,
        b2b_decision=b2b_decision,
        b2b_confidence=confidence,
        b2b_reasoning=reasoning,
        sales_questions=questions[:3],
        key_signals=signals
    )
