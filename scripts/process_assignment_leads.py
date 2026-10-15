import os
import sys
import json
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db, create_lead, get_lead
from app.main import process_single_lead_pipeline

SAMPLE_LEADS = [
    "https://www.houstonroofingonline.com",
    "BrightPlay Turf – Artificial Turf & Landscaping, Chicago IL",
    "https://www.springhilllandscaping.com",
    "Joe's Backyard Landscaping – Phoenix AZ",
    "https://www.centraltexasbarkery.com",
    "Sunrise Plumbing & Drain Services – Tampa FL",
    "https://www.denverlockandsafe.com",
    "Green Leaf Lawn Care – Columbus OH",
    "https://www.redtruckbakery.com",
    "Blue Ridge HVAC Services – Roanoke VA",
    "Acme Roofing & Construction – Dallas TX",
    "https://www.bostonplumbing.com",
    "Pacific Northwest Tree Care – Portland OR",
    "Maple Street Auto Repair – Madison WI",
    "https://www.piedmontmoving.com"
]

async def main():
    print(f"Initializing database and processing {len(SAMPLE_LEADS)} assigned leads...")
    init_db()

    results = []
    for idx, lead_input in enumerate(SAMPLE_LEADS, 1):
        print(f"\n[{idx}/{len(SAMPLE_LEADS)}] Processing: {lead_input}")
        lid = create_lead(lead_input)
        await process_single_lead_pipeline(lid, lead_input)
        lead_data = get_lead(lid)
        results.append(lead_data)
        print(f" -> Completed: {lead_data.get('company_name')} | B2B: {lead_data.get('b2b_decision')} ({lead_data.get('b2b_confidence')}%)")

    # Export to data/sample_results.json
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nAll {len(results)} leads processed successfully!")
    print(f"Results saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
