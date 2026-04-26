# AI-MedPay — Intelligent Health Insurance Platform

An AI-powered health insurance platform built with Flask, PostgreSQL, LightGBM, FAISS, and Llama 2. The system compares insurance plans, detects medical bill fraud using OCR, and provides hospital-aware pre-authorization estimates through a RAG-powered chatbot.

---

## Application Screenshots

### Home Page

![Home Page](assets/Home_page.png)

The landing page presents a live AI recommendation card alongside platform statistics: 500+ indexed insurance plans, 95% model accuracy, and an average user saving of Rs. 25,000.

---

### Get a Quote — User Input Form

![Get Quote](assets/Get_Quote.png)

A four-step guided form collects user demographics (age, income, dependents, region, city, occupation type, plan type) and pre-existing conditions. A live profile panel on the right displays recommendation confidence in real time — reaching 95% as fields are completed.

---

### Insurance Quote Results

![Quote Results](assets/Final_output.png)

The output page ranks matching insurance plans using the LightGBM model. Each card shows premium, deductible, network hospital count, rank, and a plain-language explanation of why the plan was recommended (e.g., "Excellent value: Rs. 191 coverage per Rs. 1 premium").

---

## Overview

AI-MedPay addresses three pain points in the Indian health insurance market: opaque plan comparison, unchecked medical bill overcharges, and inaccessible pre-authorization processes. All three are handled within a single platform backed by machine learning and retrieval-augmented generation.

---

## Key Features

### 1. Smart Plan Comparison
- LightGBM ranking model trained with LambdaRank objective and 1,000 decision trees
- 18 engineered features covering age, income, family size, location, pre-existing conditions, and plan type
- Scores and ranks 204+ plans; outputs ranked list with human-readable explanation per plan
- 99.85% NDCG score on validation data

### 2. Bill Buster — Medical Bill Fraud Detector
- Accepts PDF, JPG, PNG, and HEIC bill uploads
- OCR pipeline: preprocessing (denoise, grayscale) → Tesseract extraction → NLP line-item parsing
- Detects duplicate charges and cost inflation against market rates (571% overcharges flagged in testing)
- Reports potential savings per bill (Rs. 189,760 average recovery in test cases)
- Real-time anomaly flagging with confidence scores per line item

### 3. Pre-Authorization RAG System
- Hospital-aware cost estimation for five medical procedures
- Knowledge base built from real hospital data: Apollo, Fortis, AIIMS with cost multipliers
- Interactive frontend with hospital selection dropdown and estimated coverage breakdown

### 4. AI Chatbot (RAG + Llama 2)
- Sentence-transformer embeddings indexed with FAISS vector search
- Llama 2 7B Chat (quantized, Q4) for deterministic response generation
- Floating widget accessible across all pages with no PII stored per session

### 5. User Dashboard
- Google OAuth2 authentication
- Saved plan comparison, claim history, and hospital network finder

---

## System Architecture

```
User Input (Demographics + Conditions)
        │
        ▼
LightGBM Ranker (18 features, LambdaRank)
        │
        ▼
Ranked Plan List (NDCG 99.85%)
        │
        ▼
Explanation Generator → Frontend Card Render

Bill Upload (PDF/JPG/PNG/HEIC)
        │
        ▼
OCR Pipeline (Tesseract + Preprocessing)
        │
        ▼
Anomaly Detection (Duplicate + Inflation Check)
        │
        ▼
Savings Report

User Query (Chatbot)
        │
        ▼
Sentence-Transformer Embeddings
        │
        ▼
FAISS Retrieval → Llama 2 7B → Response
```

---

## Technology Stack

### Backend
- Python 3.12, Flask (blueprint architecture)
- PostgreSQL + SQLAlchemy ORM
- LightGBM, FAISS, sentence-transformers
- Llama-cpp-python (local LLM inference)
- Tesseract OCR, pdf2image, pillow-heif

### Frontend
- HTML5, CSS3, Vanilla JavaScript
- Tailwind CSS with glassmorphism design system
- Custom RAG chatbot widget with drag-and-drop file upload
- Live profile confidence panel (real-time form feedback)

---

## Project Structure

```
AI-Medpay/
│
├── backend/
│   ├── app/
│   │   ├── api/routes/              # REST API endpoints
│   │   ├── services/procedure_rag.py
│   │   ├── frontend_routes/bill_buster.py
│   │   └── utils/bill_analyzer.py
│   ├── data/
│   │   ├── hospitals_real.csv       # 30 real hospitals with cost multipliers
│   │   └── procedure_knowledge.json # 5 procedures knowledge base
│   └── models/plan_ranker.pkl
│
├── frontend/
│   └── templates/
│
├── chat_index/faiss.index
├── models/llm/ggml-model-q4_0.gguf
├── scripts/index_docs.py
│
└── assets/
    ├── Home_page.png
    ├── Get_Quote.png
    └── Final_output.png
```

---

## REST API Endpoints

| Feature | Endpoint | Method |
|---|---|---|
| Plan recommendations | `/api/recommendations` | GET / POST |
| Submit quote | `/api/quote/submit` | POST |
| Bill fraud analysis | `/api/bill/analyze` | POST |
| OCR parsing | `/api/bill/parse` | POST |
| Bill scan result | `/bill-buster/scan-result/<job_id>` | GET |
| Pre-auth estimate | `/pre-auth-estimate` | POST |
| Hospital selection | `/bill-buster/pre-auth` | GET |
| Chat query | `/api/chat/query` | POST |
| List plans | `/api/platforms` | GET |

---

## Setup Instructions

```bash
git clone https://github.com/Varadpendkar/AI-Medpay.git
cd AI-Medpay

# Activate virtual environment
source AImedenv/bin/activate

# Install dependencies
pip install -r requirements_chatbot.txt

# Set environment variables
export PYTHONPATH=/path/to/project/backend
export LLAMA_MODEL_PATH=models/llm/ggml-model-q4_0.gguf

# Run DB migrations
alembic upgrade head

# Build FAISS knowledge index
python scripts/index_docs.py

# Start application
cd backend && python -m app.main
```

Application runs at: `http://127.0.0.1:5001`

---

## Performance Benchmarks

| Component | Latency |
|---|---|
| LightGBM plan ranking | < 20ms |
| FAISS vector retrieval | < 50ms |
| Hospital cost lookup | < 100ms |
| Pre-auth RAG query | 2 – 4 seconds |
| Bill OCR processing | 5 – 15 seconds |

---

## Security

- Google OAuth2 for user authentication
- SQL injection protection via SQLAlchemy ORM
- File validation: MIME type checking and size limits enforced on upload
- No personally identifiable information stored in chatbot sessions

---

## Testing

- 36 pytest test files covering unit, integration, and functional tests
- End-to-end API workflow validation
- Bill fraud detection functional test: 66.7% anomaly flagging rate
- Model accuracy verified: 99.85% NDCG on held-out validation set

---

## Future Enhancements

- Transformer-based plan recommender using BERT embeddings
- Multilingual chatbot support: Hindi and regional Indian languages
- Real-time claim tracking via insurance provider API integration
- Mobile application: React Native
- Production deployment: Nginx + Gunicorn + Redis caching

---

## License

This project is open-source. No explicit license file is included. Contact the author before using in production or commercial contexts.

---

## Author

**Varad Pendkar**
Full-Stack Developer & AI/ML Engineer
varadpendkar@gmail.com
[GitHub](https://github.com/Varadpendkar) | [LinkedIn](https://linkedin.com/in/varad-pendkar-0b4974253)
