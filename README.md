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

### **1. Smart Plan Comparison**
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
