# AI-MedPay — Intelligent Health Insurance Platform
### *AI-powered plan comparison, bill analysis & insurance assistance*

---

## 🚀 Overview
AI-MedPay is a full-stack health insurance intelligence platform built with **Flask, PostgreSQL, LightGBM, FAISS, and Llama 2**.  
It compares insurance plans, analyzes medical bills using OCR, and provides an AI-powered chatbot for real-time insurance assistance.

This project demonstrates:

- Full-stack engineering  
- Machine learning deployment  
- OCR + NLP pipelines  
- RAG-based chatbot systems  
- API design & system architecture  

---

## ⭐ Key Features

### **1. Smart Plan Comparison**Optimizing tool selection...# AI-MedPay — Intelligent Health Insurance Platform
### *AI-powered plan comparison, bill fraud detection & pre-authorization RAG system*

---

## 🚀 Overview
AI-MedPay is a full-stack health insurance intelligence platform built with **Flask, PostgreSQL, LightGBM, FAISS, and Llama 2**.  
It compares insurance plans, detects medical bill fraud using OCR, and provides hospital-aware pre-authorization estimates with RAG-powered assistance.

This project demonstrates:

- Full-stack engineering with Flask blueprints
- Machine learning deployment (99.85% NDCG score)
- OCR + anomaly detection pipelines
- RAG-based chatbot with hospital integration
- REST API design & microservice architecture

---

## ⭐ Key Features

### **1. Smart Plan Comparison**
- LightGBM ranking model with 18-feature engineering
- Scores 204 plans across premium, coverage, deductible, and network features
- Personalized recommendations with explanation text

### **2. Bill Buster — Medical Bill Fraud Detector**
- OCR-powered bill extraction (PDF/JPG/PNG/HEIC)
- Detects duplicate charges, inflated costs (571% overcharges caught)
- Calculates potential savings (₹189,760 average recovery)
- Real-time anomaly flagging with confidence scores

### **3. Pre-Authorization RAG System**
- Hospital-aware cost estimation for 5 medical procedures
- Real hospital data (Apollo, Fortis, AIIMS with cost multipliers)
- Procedure knowledge base with hospital-specific variations
- Interactive frontend with hospital selection dropdown

### **4. AI Chatbot (RAG + Llama 2)**
- Sentence-transformer embeddings with FAISS vector search
- Llama 2 7B Chat (quantized) for deterministic responses
- Document indexing with 8 knowledge base entries
- Floating widget across all pages

### **5. User Dashboard**
- Google OAuth2 authentication
- Saved plans with comparison features
- Hospital finder with network validation
- Interactive 3D elements and glassmorphism UI

---

## 🧠 AI & ML Components

### **LightGBM Plan Ranker**
- 18 engineered features (age, income, family size, location)
- LambdaRank objective with 1000 decision trees
- 99.85% NDCG score on validation data

### **Pre-Auth RAG Architecture**
```
User Query → Hospital Selection → Procedure RAG → Cost Estimation → Recommendations
```

### **Bill Fraud Detection Pipeline**
1. OCR text extraction (Tesseract)
2. Line item parsing and categorization
3. Duplicate detection (fuzzy matching)
4. Cost inflation analysis vs market rates
5. Savings calculation with conservative estimates

---

## 🛠️ Technology Stack

### **Backend**
- Python 3.12 with Flask blueprint architecture
- PostgreSQL + SQLAlchemy ORM
- LightGBM, FAISS, sentence-transformers
- Llama-cpp-python for local LLM inference
- Tesseract OCR, pdf2image, pillow-heif

### **Frontend**
- HTML5, CSS3, Vanilla JavaScript
- Tailwind CSS with responsive design
- Custom chatbot widget with drag-drop file uploads
- Interactive hospital selection and cost visualization

---

## 📦 Project Structure (Simplified)
```
backend/
├── app/
│   ├── api/routes/
│   ├── services/procedure_rag.py
│   ├── frontend_routes/bill_buster.py
│   └── utils/bill_analyzer.py
├── data/
│   ├── hospitals_real.csv (30 hospitals)
│   └── procedure_knowledge.json (5 procedures)
├── models/plan_ranker.pkl
frontend/templates/bill_buster_preauth_working.html
chat_index/faiss.index
```

---

## 🔌 Core REST API Endpoints

| Feature | Endpoint | Method |
|--------|----------|--------|
| Plan recommendations | `/api/recommendations` | GET/POST |
| Bill fraud analysis | `/api/bill/analyze` | POST |
| OCR parsing | `/api/bill/parse` | POST |
| Pre-auth estimate | `/pre-auth-estimate` | POST |
| Hospital selection | `/bill-buster/pre-auth` | GET |
| Chat query | `/api/chat/query` | POST |
| Platform list | `/api/platforms` | GET |

---

## ⚙️ Setup Instructions

```bash
git clone https://github.com/Varadpendkar/AI-Medpay.git
cd AI-Medpay

# Activate environment
source AImedenv/bin/activate

# Install dependencies
pip install -r requirements_chatbot.txt

# Set environment variables
export PYTHONPATH=/path/to/project/backend
export LLAMA_MODEL_PATH=models/llm/ggml-model-q4_0.gguf

# Initialize knowledge base
python scripts/index_docs.py

# Start application
cd backend && python -m app.main
```
**App URL:** http://127.0.0.1:5001

---

## 🔐 Security & Performance Highlights

### **Security**
- Google OAuth2 integration
- SQL injection protection via SQLAlchemy ORM
- File validation with MIME type checking
- No PII storage in chatbot conversations

### **Performance**
- LightGBM inference: <20ms
- FAISS vector search: <50ms  
- Bill OCR processing: 5-15 seconds
- Pre-auth RAG queries: 2-4 seconds
- Hospital cost lookup: <100ms

---

## 🧪 Testing Coverage
- **Unit tests:** pytest framework with 36 test files
- **Integration tests:** End-to-end API workflow validation
- **Functional tests:** Bill fraud detection (66.7% anomaly flagging)
- **Performance tests:** 99.85% NDCG model accuracy verified
- **Manual tests:** Complete user workflow validation

---

## 🧭 Future Enhancements
- Transformer-based plan recommender with BERT embeddings
- Multilingual chatbot support (Hindi + Regional languages)
- Real-time claim tracking with insurance API integration
- Mobile app development (React Native)
- Production deployment with Nginx + Gunicorn + Redis caching

---

## 👤 Author
**Varad Pendkar**  
Full-Stack Developer & AI/ML Engineer  
📧 varadpendkar@gmail.com  
🔗 [GitHub](https://github.com/Varadpendkar) | [LinkedIn](https://linkedin.com/in/varadpendkar)
- LightGBM ranking model  
- Scores plans across premium, coverage, deductible, and network features  
- Personalized recommendations based on user profile  

### **2. Bill Buster — Medical Bill Analyzer**
- OCR-powered bill extraction (PDF/JPG/PNG/HEIC)  
- Extracts totals, dates, hospital name, line items  
- Suggests cheaper network hospitals  
- Coverage eligibility overview  

### **3. AI Chatbot (RAG + Llama 2)**
- Sentence-transformer embeddings  
- FAISS vector search  
- Llama 2 7B Chat (quantized) for deterministic responses  
- Works across all pages via floating widget  

### **4. Pre-Authorization Workflow**
- Document uploads  
- Hospital verification  
- Estimated treatment cost  
- Coverage validation  
- Status tracking  

### **5. User Dashboard**
- Saved plans  
- Claim history  
- Hospital finder  
- Quick actions & chatbot integration  

---

## 🧠 AI & ML Components

### **LightGBM Plan Ranker**
- 18 engineered features  
- Scores and ranks health plans  
- Outputs normalized relevance scores  

### **RAG Chatbot Architecture**
User Query → Embeddings → FAISS Retrieval → Llama 2 → Final Answer

yaml
Copy code

### **Bill Scanner Pipeline**
1. Preprocessing (denoise, grayscale)  
2. OCR (Tesseract)  
3. NLP parsing  
4. Hospital matching  
5. Savings estimation  

---

## 🛠️ Technology Stack

### **Backend**
- Python 3.12  
- Flask  
- PostgreSQL + SQLAlchemy  
- LightGBM, FAISS, sentence-transformers  
- Llama-cpp-python  
- Tesseract OCR, pdf2image, pillow-heif  

### **Frontend**
- HTML5, CSS3, Vanilla JS  
- Custom chatbot widget  
- Responsive glassmorphism UI  

---

## 📦 Project Structure (Simplified)
backend/
app/
api/
core/
chat_local.py
frontend_routes/
models/
migrations/
models/
llm/
recommender/
chat_index/
scripts/
uploads/

yaml
Copy code

---

## 🔌 Core API Endpoints

| Feature | Endpoint | Method |
|--------|----------|--------|
| Submit quote | `/api/quote/submit` | POST |
| Upload bill | `/bill-buster/upload-bill` | POST |
| Bill result | `/bill-buster/scan-result/<job_id>` | GET |
| Chat query | `/api/chat/query` | POST |
| List health plans | `/api/platforms` | GET |
| Submit pre-auth request | `/bill-buster/pre-auth` | POST |

---

## ⚙️ Setup Instructions

```bash
git clone <repo>
cd project

# Activate environment
source AImedenv/bin/activate

# Install dependencies
pip install -r requirement.txt

# Set environment variables
export PYTHONPATH=backend
export LLAMA_MODEL_PATH=models/llm/ggml-model-q4_0.gguf

# Run DB migrations & build index
alembic upgrade head
python scripts/index_docs.py

# Start app
bash start_server.sh
App URL: http://127.0.0.1:5001

🔐 Security Highlights
Chatbot does not store PII

File validation: MIME + size limits

SQL injection protection via ORM

Planned: API rate limiting

📈 Performance Snapshot
LLM inference: 2–4 seconds

FAISS retrieval: <50ms

Bill processing: 5–15 seconds

Plan ranking: <20ms

🧭 Future Enhancements
Transformer-based plan recommender

Multilingual chatbot (Hindi + Regional)

Real-time claim tracking

Mobile app (React Native)

Production deployment with Nginx + Gunicorn + Redis

👤 Author
Varad Pendkar
Full-Stack Developer & AI/ML Engineer
📧 varadpendkar@gmail.com
