#!/usr/bin/env python3
"""
Document Indexer for RAG Chatbot
Crawls specified URLs or local files and indexes them into FAISS via Flask API.
"""
import requests
import bs4
import os
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from time import sleep
import sys

# Configuration
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5001")
INDEX_ENDPOINT = f"{API_BASE}/api/chat/index"

# URLs to crawl (customize for your site)
SEED_URLS = [
    "http://127.0.0.1:5001/",
    "http://127.0.0.1:5001/about",
    "http://127.0.0.1:5001/get-quote",
    "http://127.0.0.1:5001/bill-buster",
    # Add more URLs from your site
]

# Local documents to index (optional)
LOCAL_DOCS = [
    # Path(__file__).parent.parent / "README.md",
    # Path(__file__).parent.parent / "docs" / "faq.md",
]

# Chunking parameters
CHUNK_SIZE = 800  # tokens (words)
OVERLAP = 100  # overlap between chunks
MAX_PAGE_CHARS = 10000  # max chars to extract per page


def fetch_text(url):
    """Fetch and extract clean text from URL"""
    try:
        print(f"📥 Fetching: {url}")
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Failed: {url} - {e}")
        return None
    
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    
    # Remove scripts, styles, nav, footer, header
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()
    
    # Extract text
    text = soup.get_text(separator="\n")
    
    # Normalize whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    
    # Trim to max chars
    text = text[:MAX_PAGE_CHARS]
    
    print(f"✅ Extracted {len(text)} chars from {url}")
    return text


def read_local_file(filepath):
    """Read text from local file"""
    try:
        print(f"📂 Reading: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        
        text = text[:MAX_PAGE_CHARS]
        print(f"✅ Read {len(text)} chars from {filepath}")
        return text
    except Exception as e:
        print(f"❌ Failed to read {filepath}: {e}")
        return None


def make_chunks(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """Split text into overlapping chunks"""
    tokens = text.split()
    chunks = []
    i = 0
    
    while i < len(tokens):
        chunk_tokens = tokens[i:i+chunk_size]
        chunk_text = " ".join(chunk_tokens)
        chunks.append(chunk_text)
        i += chunk_size - overlap
    
    return chunks


def index_documents(docs):
    """Send documents to Flask index endpoint"""
    if not docs:
        print("⚠️  No documents to index")
        return
    
    print(f"\n📤 Sending {len(docs)} chunks to {INDEX_ENDPOINT}...")
    
    try:
        resp = requests.post(
            INDEX_ENDPOINT,
            json={"docs": docs},
            timeout=120
        )
        resp.raise_for_status()
        
        result = resp.json()
        print(f"✅ Index response: {json.dumps(result, indent=2)}")
        print(f"   Added: {result.get('added', 0)} chunks")
        print(f"   Total: {result.get('total', 0)} chunks in index")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Index request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        sys.exit(1)


def crawl_urls(urls):
    """Crawl URLs and extract text chunks"""
    docs = []
    
    for url in urls:
        text = fetch_text(url)
        if not text:
            continue
        
        chunks = make_chunks(text)
        print(f"   Created {len(chunks)} chunks from {url}")
        
        for idx, chunk in enumerate(chunks):
            docs.append({
                "id": f"{url}#chunk{idx}",
                "text": chunk,
                "meta": {
                    "url": url,
                    "chunk": idx,
                    "source_type": "web"
                }
            })
        
        sleep(0.5)  # Be polite
    
    return docs


def index_local_files(filepaths):
    """Index local text files"""
    docs = []
    
    for filepath in filepaths:
        text = read_local_file(filepath)
        if not text:
            continue
        
        chunks = make_chunks(text)
        print(f"   Created {len(chunks)} chunks from {filepath}")
        
        for idx, chunk in enumerate(chunks):
            docs.append({
                "id": f"file://{filepath}#chunk{idx}",
                "text": chunk,
                "meta": {
                    "filepath": str(filepath),
                    "chunk": idx,
                    "source_type": "file"
                }
            })
    
    return docs


def index_health_insurance_kb():
    """Index comprehensive health insurance knowledge base"""
    kb_docs = [
        # Basics (existing)
        {
            "id": "kb://health-insurance-basics",
            "text": """Health insurance is a contract that requires an insurer to pay some or all of a person's healthcare costs in exchange for a premium. Health insurance plans in India typically cover hospitalization expenses, pre and post-hospitalization costs, daycare procedures, and ambulance charges. Key components include: Premium (amount paid to insurer), Sum Insured (maximum coverage amount), Deductible (amount you pay before insurance kicks in), Co-payment (percentage you pay for each claim), Network Hospitals (cashless treatment facilities), and Waiting Period (time before certain conditions are covered).""",
            "meta": {"category": "basics", "topics": ["coverage"], "keywords": ["premium", "sum insured", "deductible"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # Claims (existing + enhanced)
        {
            "id": "kb://claim-process",
            "text": """To file a health insurance claim: 1) Cashless Claim - Contact insurer's helpline before hospitalization, get pre-authorization from network hospital, insurer settles directly with hospital. 2) Reimbursement Claim - Pay hospital bills yourself, collect all bills/prescriptions/discharge summary, submit claim form with documents within claim intimation period (usually 7-30 days), insurer reviews and reimburses approved amount. Required documents: Claim form, Hospital bills, Discharge summary, Prescriptions, Diagnostic reports, Pre-authorization form (for cashless). Claim settlement usually takes 7-15 days for reimbursement.""",
            "meta": {"category": "claims", "topics": ["claims"], "keywords": ["cashless", "reimbursement", "settlement"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        {
            "id": "kb://claim-rejection-reasons",
            "text": """Common reasons for claim rejection: 1) Non-disclosure of pre-existing conditions, 2) Treatment during waiting period, 3) Incomplete documentation, 4) Treatment not covered under policy, 5) Lapsed policy due to non-payment, 6) Claims for excluded items (cosmetic surgery, dental), 7) Treatment at non-network hospital without intimation. How to avoid: Always disclose medical history truthfully, read policy exclusions carefully, maintain all original bills and documents, inform insurer within 24-48 hours of hospitalization.""",
            "meta": {"category": "claims", "topics": ["claims"], "keywords": ["rejection", "denial", "reasons"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # Pre-existing conditions (existing + enhanced)
        {
            "id": "kb://pre-existing-conditions",
            "text": """Pre-existing conditions (PED) are illnesses or medical conditions that exist before buying health insurance. Most insurers impose a waiting period of 2-4 years before covering pre-existing conditions. During waiting period, any treatment related to pre-existing condition is not covered. Some insurers offer plans with reduced waiting periods (1 year) at higher premiums. Common pre-existing conditions: Diabetes, Hypertension, Heart disease, Asthma, Thyroid disorders, Arthritis, High cholesterol. Always disclose pre-existing conditions truthfully during application to avoid claim rejection. Some insurers offer immediate cover for PED at higher premiums.""",
            "meta": {"category": "coverage", "topics": ["coverage"], "keywords": ["ped", "pre-existing", "waiting period", "diabetes", "hypertension"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # Network hospitals (existing)
        {
            "id": "kb://network-hospitals",
            "text": """Network hospitals are medical facilities that have tie-ups with insurance companies for cashless treatment. Benefits: No upfront payment required, Direct billing between hospital and insurer, Faster claim settlement, Reduced paperwork. To use network hospital: Check insurer's hospital list online or app, Inform hospital about your insurance at admission, Provide insurance card and policy details, Hospital contacts insurer for pre-authorization. For non-network hospitals, you must pay and file reimbursement claim. Major network hospital chains in India: Apollo, Fortis, Max Healthcare, Manipal, KIMS, Narayana Health.""",
            "meta": {"category": "hospitals", "topics": ["hospitals"], "keywords": ["network", "cashless", "apollo", "fortis"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # Exclusions (existing)
        {
            "id": "kb://exclusions",
            "text": """Common health insurance exclusions (not covered): Cosmetic surgery, Dental treatment (unless due to accident), Alternative therapies (Ayurveda, Homeopathy unless specified), Self-inflicted injuries, War/nuclear risks, Pre-existing diseases during waiting period, Experimental treatments, Congenital diseases (unless covered), Infertility treatment, Pregnancy complications (unless maternity rider added), Obesity treatment, Vitamin supplements. Always read policy exclusions carefully before buying.""",
            "meta": {"category": "exclusions", "topics": ["coverage"], "keywords": ["exclusions", "not covered", "cosmetic", "dental"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Premium calculation
        {
            "id": "kb://premium-factors",
            "text": """Health insurance premium is calculated based on: 1) Age - Higher age means higher premium (increases by 10-15% every 5 years), 2) Sum Insured - Higher coverage = higher premium, 3) Medical history - Pre-existing conditions increase premium, 4) Lifestyle - Smoking, drinking habits affect premium, 5) BMI - Obesity may increase premium, 6) Family size - Family floater plans cost less than individual plans for each member, 7) City of residence - Metro cities have higher premiums, 8) Add-ons/Riders - Maternity, critical illness riders increase premium. Ways to reduce premium: Choose higher deductible, opt for lower room rent, avoid unnecessary riders, maintain healthy lifestyle, pay annually instead of monthly.""",
            "meta": {"category": "basics", "topics": ["plans"], "keywords": ["premium", "cost", "factors", "age"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Room rent limits
        {
            "id": "kb://room-rent-limits",
            "text": """Room rent limit is the maximum amount insurer will pay for hospital room per day. Types: 1) Fixed limit (e.g., ₹5000/day), 2) Percentage of sum insured (e.g., 1% of SI), 3) No limit (recommended). Impact: If actual room rent exceeds limit, ALL treatment costs are proportionately reduced (Proportionate Deduction clause). Example: If policy allows ₹5000/day but you choose ₹10,000 room (2x limit), insurer pays only 50% of total bill. Recommendation: Choose plans with no room rent limits or high limits to avoid out-of-pocket expenses.""",
            "meta": {"category": "coverage", "topics": ["coverage", "plans"], "keywords": ["room rent", "limit", "proportionate"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Co-payment
        {
            "id": "kb://copayment",
            "text": """Co-payment is the percentage of claim amount you must pay from your pocket. Example: 20% co-pay on ₹1,00,000 claim means you pay ₹20,000, insurer pays ₹80,000. Common in: Senior citizen plans (10-30% co-pay), Plans with lower premiums, OPD claims. Benefits of co-payment: Reduces premium by 15-30%, Prevents misuse of insurance, Encourages cost-conscious decisions. Who should choose: Those with good financial cushion, Younger individuals with lower claim probability. Who should avoid: Senior citizens, Those with chronic conditions, Families with frequent hospitalization needs.""",
            "meta": {"category": "basics", "topics": ["coverage", "plans"], "keywords": ["copay", "co-payment", "percentage"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Tax benefits
        {
            "id": "kb://tax-benefits-80d",
            "text": """Health insurance premiums are tax deductible under Section 80D of Income Tax Act. Deduction limits (FY 2024-25): For self/spouse/children - ₹25,000 (below 60 years), ₹50,000 (above 60 years). For parents - Additional ₹25,000 (below 60), ₹50,000 (above 60). Maximum deduction: ₹1,00,000 (if you and parents both above 60). Eligible expenses: Premium paid, Preventive health checkup (₹5000), Medical expenses for senior citizens (if no insurance). Payment mode: Only online/cheque (not cash). Claim process: Provide premium receipt while filing ITR, Declare in Form 16 or during e-filing.""",
            "meta": {"category": "basics", "topics": ["plans"], "keywords": ["tax", "80d", "deduction", "itr"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Maternity coverage
        {
            "id": "kb://maternity-coverage",
            "text": """Maternity coverage includes pre-natal, delivery, and post-natal expenses. Key points: 1) Waiting period: Usually 2-4 years (some offer 9 months at higher premium), 2) Coverage: Normal delivery, C-section, pre/post natal checkups, newborn baby expenses (first 90 days), 3) Sub-limit: ₹50,000 to ₹1,00,000 depending on plan, 4) Number of deliveries: Usually 2 deliveries covered per policy lifetime. Exclusions: Abortion (unless medically necessary), Surrogacy, IVF treatment (unless specified). Best for: Couples planning pregnancy within 2-4 years, Should be added before conception for coverage.""",
            "meta": {"category": "coverage", "topics": ["coverage"], "keywords": ["maternity", "pregnancy", "delivery", "newborn"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Critical illness
        {
            "id": "kb://critical-illness",
            "text": """Critical Illness rider provides lump-sum payout on diagnosis of specified critical illnesses. Covered illnesses (typically 15-25): Cancer, Heart attack, Stroke, Kidney failure, Major organ transplant, Paralysis, Blindness, Coronary artery bypass surgery, Multiple sclerosis, Parkinson's disease. Benefits: Lump-sum payment (₹5-50 lakhs), No hospitalization required, Can be used for any purpose (treatment, lost income, lifestyle changes), Separate from base policy sum insured. Waiting period: 90 days (30 days for accidents). Best for: High-risk professions, Family history of critical illness, Those seeking additional financial protection.""",
            "meta": {"category": "coverage", "topics": ["coverage"], "keywords": ["critical illness", "rider", "cancer", "heart attack"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Day care procedures
        {
            "id": "kb://daycare-procedures",
            "text": """Day care procedures are treatments that don't require 24-hour hospitalization due to medical advancements. Common day care procedures covered: Cataract surgery, Dialysis, Chemotherapy, Lithotripsy (kidney stone removal), Tonsillectomy, Piles treatment, Hernia repair, Arthroscopy, Dental surgery (accident-related), Varicose vein treatment. Coverage: Most modern policies cover 150+ day care procedures, No hospitalization requirement (can be discharged same day), Full coverage including surgeon fees, OT charges, medicines. Important: Check policy wording for list of covered day care procedures.""",
            "meta": {"category": "coverage", "topics": ["coverage"], "keywords": ["daycare", "outpatient", "cataract", "dialysis"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: OPD coverage
        {
            "id": "kb://opd-coverage",
            "text": """OPD (Outpatient Department) coverage includes medical expenses without hospitalization. Covered: Doctor consultation fees, Diagnostic tests, Medicines, Physiotherapy, Dental checkups, Eye checkups. Not typically included in base health plans - available as add-on/rider. OPD sub-limits: Usually ₹5,000 to ₹25,000 per year, Per consultation limits (₹500-1000). Co-payment: 20-30% common in OPD claims. Best for: Families with children, Elderly with frequent doctor visits, Those with chronic conditions requiring regular checkups. Alternative: Some insurers offer wellness benefits (free health checkups) instead of full OPD.""",
            "meta": {"category": "coverage", "topics": ["coverage"], "keywords": ["opd", "outpatient", "consultation", "checkup"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: Portability
        {
            "id": "kb://portability",
            "text": """Health insurance portability allows switching from one insurer to another without losing benefits. Benefits: Keep accumulated waiting period credits, No fresh medical tests, Preserve no-claim bonus, Get better coverage/features. Process: Apply to new insurer 45 days before renewal, New insurer requests records from old insurer, Approval within 15 days, Seamless transfer on renewal date. Important: Cannot port during claim processing, Portability doesn't mean automatic approval (new insurer can reject), Sum insured can be increased during porting (but may require medical tests).""",
            "meta": {"category": "basics", "topics": ["plans"], "keywords": ["portability", "switch", "transfer"], "source_type": "kb", "page_type": "knowledge_base"}
        },
        
        # NEW: No Claim Bonus
        {
            "id": "kb://no-claim-bonus",
            "text": """No Claim Bonus (NCB) is a reward for not filing claims. How it works: For each claim-free year, sum insured increases by 5-50% (without premium increase), OR premium decreases by 10-20%. Types: Cumulative bonus (increases every year), Super NCB (bonus continues even after claim, with reset). Maximum: Usually 100-200% of original sum insured. Lost if: You file a claim, Policy lapses. Protection: Some insurers offer NCB protection rider (preserve bonus even after 1-2 claims). Best practice: Use insurance only for large expenses, pay small bills yourself to preserve NCB.""",
            "meta": {"category": "basics", "topics": ["plans"], "keywords": ["ncb", "bonus", "claim-free"], "source_type": "kb", "page_type": "knowledge_base"}
        }
    ]
    
    return kb_docs


def main():
    """Main indexing workflow"""
    print("=" * 60)
    print("🚀 AI-MedPay Document Indexer for RAG Chatbot")
    print("=" * 60)
    
    all_docs = []
    
    # 1. Crawl URLs
    if SEED_URLS:
        print(f"\n📡 Crawling {len(SEED_URLS)} URLs...")
        url_docs = crawl_urls(SEED_URLS)
        all_docs.extend(url_docs)
        print(f"✅ Extracted {len(url_docs)} chunks from URLs")
    
    # 2. Index local files
    if LOCAL_DOCS:
        print(f"\n📂 Indexing {len(LOCAL_DOCS)} local files...")
        file_docs = index_local_files(LOCAL_DOCS)
        all_docs.extend(file_docs)
        print(f"✅ Extracted {len(file_docs)} chunks from files")
    
    # 3. Add knowledge base
    print("\n📚 Adding health insurance knowledge base...")
    kb_docs = index_health_insurance_kb()
    all_docs.extend(kb_docs)
    print(f"✅ Added {len(kb_docs)} KB articles")
    
    # 4. Send to index
    if not all_docs:
        print("\n⚠️  No documents found to index!")
        print("Please configure SEED_URLS or LOCAL_DOCS")
        sys.exit(1)
    
    print(f"\n📊 Total documents to index: {len(all_docs)}")
    index_documents(all_docs)
    
    print("\n" + "=" * 60)
    print("✅ Indexing complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Test query: curl -X POST http://127.0.0.1:5001/api/chat/query \\")
    print("                   -H 'Content-Type: application/json' \\")
    print("                   -d '{\"query\":\"What are pre-existing conditions?\"}'")
    print("  2. Check status: curl http://127.0.0.1:5001/api/chat/status")
    print("  3. View frontend: http://127.0.0.1:5001/chatbot")


if __name__ == "__main__":
    main()
