# backend/app/chat_local.py
"""
Local LLM RAG Chatbot Blueprint
Uses llama-cpp-python for inference, FAISS for retrieval, sentence-transformers for embeddings.
"""
import os
import json
import time
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

# Lazy import for llama_cpp to allow running without model initially
_llama_cpp = None

CHAT_BP = Blueprint("chat_local", __name__, url_prefix="/api/chat")

# Config (paths configurable via environment)
PROJECT_ROOT = Path(__file__).parent.parent.parent
BASE_DIR = Path(os.environ.get("PROJECT_BASE", str(PROJECT_ROOT)))
MODEL_PATH = Path(os.environ.get("LLAMA_MODEL_PATH", str(BASE_DIR / "models" / "llm" / "ggml-model-q4_0.gguf")))
INDEX_DIR = BASE_DIR / "chat_index"
DOCS_JSON = INDEX_DIR / "docs.json"
INDEX_FILE = INDEX_DIR / "faiss.index"
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
TOP_K_DEFAULT = 5
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "512"))
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.0"))

# System prompt - strict RAG behavior with citations
SYSTEM_PROMPT_TEXT = """You are the AI-MedPay Health Insurance Assistant. You must ONLY use the content found in the section titled "RETRIEVED DOCUMENTS" that follows. Never invent facts or assert anything that is not directly supported by the retrieved documents. If asked something not present in the retrieved documents, respond exactly:

"I don't know this from the provided sources. Would you like me to search more documents or connect you with a human agent?"

Answer format rules:
1. Provide a BRIEF direct answer first (1–3 sentences).
2. Then provide a "Details" section with supporting evidence: up to 3 short quoted snippets (<= 200 characters each) from the retrieved documents with exact bracketed citations like [source:ID].
3. Always include a "Sources" list at the end with each source id and its URL (if known) and the retrieval score.
4. Ask a clarifying question if the user's query is ambiguous or lacks required details.
5. If the user's request involves Personal Identifiable Information (PII) or disallowed content, refuse politely: "I cannot assist with that request. If you'd like, I can help with general guidance that doesn't require sharing private information."
6. For health insurance questions, prioritize accuracy and compliance. Never provide medical advice—only insurance plan information.
7. Keep tone professional, concise, and helpful. Avoid marketing language.

CRITICAL: Cite sources inline whenever you assert a fact: [source:ID]. Do not hallucinate.

Example responses:
Q: "What are pre-existing conditions?"
A: "Pre-existing conditions (PEDs) are medical conditions you had before purchasing health insurance. [source:kb-ped] Most insurance plans have a waiting period of 2-4 years before covering PEDs. [source:kb-ped]

Details:
• Waiting periods vary: "Standard PED waiting period is 24-48 months" [source:kb-ped]
• Disclosure required: "You must disclose all pre-existing conditions during application" [source:kb-ped]
• Coverage starts after waiting period ends

Would you like to know about specific conditions or waiting period details?"

Q: "How do I file a claim?"
A: "You can file claims through two methods: cashless (at network hospitals) or reimbursement (any hospital). [source:kb-claims]

Details:
• Cashless: "Present your health card at network hospital for pre-authorization" [source:kb-claims]
• Reimbursement: "Submit bills within 15-30 days of discharge with claim form" [source:kb-claims]
• Documents needed: Discharge summary, bills, prescriptions, diagnostic reports

Which method would you like detailed guidance on?"

Q: "hi"
A: "Hello! 👋 I'm your AI-MedPay insurance assistant. I can help you with:

• Health insurance basics & terminology
• Filing claims (cashless/reimbursement)
• Pre-existing condition coverage
• Network hospitals & cashless facilities
• Plan comparisons & recommendations
• Premium calculations & tax benefits

What would you like to know about health insurance today?"
"""

# Greeting patterns for quick detection
GREETING_PATTERNS = [
    'hi', 'hello', 'hey', 'hola', 'namaste', 'good morning', 'good afternoon',
    'good evening', 'greetings', 'howdy', 'sup', 'yo', 'hii', 'helllo'
]

SMALL_TALK_PATTERNS = [
    'how are you', 'how r u', 'how are u', 'how do you do', 'what\'s up',
    'whats up', 'wassup', 'how\'s it going', 'hows it going', 'how are things'
]

# Globals for lazy loading
_embed_model = None
_faiss_index = None
_docs = []
_dim = None
_llm = None


def get_embed_model():
    """Lazy load sentence transformer model"""
    global _embed_model, _dim
    if _embed_model is None:
        current_app.logger.info(f"🔄 Loading embedding model: {EMBED_MODEL_NAME}")
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        _dim = _embed_model.get_sentence_embedding_dimension()
        current_app.logger.info(f"✅ Embedding model loaded (dim={_dim})")
    return _embed_model


def get_llm():
    """Lazy load LLM model"""
    global _llm, _llama_cpp
    if _llm is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(
                f"❌ LLM model not found at {MODEL_PATH}\n"
                f"Please download a quantized GGUF model and place it at:\n"
                f"  {MODEL_PATH}\n"
                f"Recommended: llama-2-7b-chat.Q4_0.gguf or vicuna-7b-v1.5.Q4_K_M.gguf\n"
                f"Download from: https://huggingface.co/TheBloke"
            )
        
        # Import llama_cpp only when needed
        if _llama_cpp is None:
            try:
                import llama_cpp
                _llama_cpp = llama_cpp
            except ImportError:
                raise RuntimeError(
                    "llama-cpp-python not installed. Run:\n"
                    "  pip install llama-cpp-python\n"
                    "For Apple Silicon with Metal support:\n"
                    "  CMAKE_ARGS='-DLLAMA_METAL=on' pip install llama-cpp-python"
                )
        
        current_app.logger.info(f"🔄 Loading LLM from: {MODEL_PATH}")
        current_app.logger.info(f"   Size: {MODEL_PATH.stat().st_size / (1024**3):.2f} GB")
        
        # Initialize llama.cpp with optimal settings for Apple Silicon or CPU
        _llm = _llama_cpp.Llama(
            model_path=str(MODEL_PATH),
            n_ctx=2048,  # Context window
            n_batch=512,  # Batch size for prompt processing
            n_threads=4,  # CPU threads (adjust based on your machine)
            n_gpu_layers=0,  # Set to 0 for CPU-only; increase for GPU
            verbose=False
        )
        current_app.logger.info("✅ LLM loaded successfully")
    return _llm


def ensure_index():
    """Load or create FAISS index"""
    global _faiss_index, _docs, _dim
    get_embed_model()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    if DOCS_JSON.exists() and INDEX_FILE.exists():
        current_app.logger.info(f"📂 Loading existing index from {INDEX_DIR}")
        with open(DOCS_JSON, "r", encoding="utf-8") as f:
            _docs = json.load(f)
        _faiss_index = faiss.read_index(str(INDEX_FILE))
        current_app.logger.info(f"✅ Loaded {len(_docs)} documents, index size: {_faiss_index.ntotal}")
    else:
        current_app.logger.info("📝 Creating new FAISS index")
        _docs = []
        _faiss_index = faiss.IndexFlatIP(_dim)  # Inner product on normalized vectors = cosine similarity


def save_index():
    """Persist FAISS index and document metadata"""
    global _faiss_index, _docs
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(DOCS_JSON, "w", encoding="utf-8") as f:
        json.dump(_docs, f, ensure_ascii=False, indent=2)
    
    faiss.write_index(_faiss_index, str(INDEX_FILE))


def classify_query(query):
    """
    Classify user query into categories for better routing
    Returns: dict with 'type' and 'confidence'
    """
    query_lower = query.lower().strip()
    
    # Check for greetings
    if query_lower in GREETING_PATTERNS:
        return {"type": "greeting", "confidence": 1.0}
    
    # Check for small talk
    for pattern in SMALL_TALK_PATTERNS:
        if pattern in query_lower:
            return {"type": "small_talk", "confidence": 0.9}
    
    # Check if it's too short (likely not a real question)
    if len(query.split()) <= 2 and '?' not in query:
        return {"type": "unclear", "confidence": 0.7}
    
    # Check for question indicators
    question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'should', 'is', 'are', 'do', 'does']
    if any(query_lower.startswith(qw) for qw in question_words) or '?' in query:
        return {"type": "question", "confidence": 0.95}
    
    # Check for specific intents
    if any(word in query_lower for word in ['claim', 'file', 'submit', 'reimbursement']):
        return {"type": "question", "confidence": 0.9, "intent": "claims"}
    
    if any(word in query_lower for word in ['plan', 'compare', 'recommend', 'best', 'choose']):
        return {"type": "question", "confidence": 0.9, "intent": "plans"}
    
    if any(word in query_lower for word in ['hospital', 'network', 'cashless', 'doctor']):
        return {"type": "question", "confidence": 0.9, "intent": "hospitals"}
    
    if any(word in query_lower for word in ['pre-existing', 'ped', 'condition', 'disease', 'diabetes', 'hypertension']):
        return {"type": "question", "confidence": 0.9, "intent": "coverage"}
    
    # Default to question
    return {"type": "question", "confidence": 0.5}


def get_greeting_response():
    """Return friendly greeting without needing RAG"""
    return {
        "answer": """Hello! 👋 I'm your AI-MedPay insurance assistant. I can help you with:

• **Health insurance basics** - Understanding coverage, premiums, deductibles
• **Filing claims** - Cashless vs reimbursement procedures
• **Pre-existing conditions** - Coverage rules and waiting periods
• **Network hospitals** - Finding cashless treatment facilities
• **Plan comparisons** - Choosing the right insurance for your needs
• **Premium & tax benefits** - Section 80D deductions and savings

What would you like to know about health insurance today?""",
        "sources": [],
        "requires_retrieval": False,
        "query_type": "greeting"
    }


def get_small_talk_response(query):
    """Handle small talk queries"""
    responses = {
        "how are you": "I'm doing great, thank you for asking! I'm here to help with your health insurance questions. What would you like to know?",
        "how r u": "I'm doing well! Ready to help with any health insurance questions you have. What can I assist you with?",
        "what's up": "Not much! Just here to help you with health insurance questions. What would you like to know?",
    }
    
    query_lower = query.lower().strip()
    for pattern, response in responses.items():
        if pattern in query_lower:
            return {
                "answer": response,
                "sources": [],
                "requires_retrieval": False,
                "query_type": "small_talk"
            }
    
    # Default small talk response
    return {
        "answer": "I'm here and ready to help! I specialize in health insurance questions. What would you like to know?",
        "sources": [],
        "requires_retrieval": False,
        "query_type": "small_talk"
    }


def get_suggested_questions(page_context=None, intent=None):
    """Return suggested questions based on context"""
    
    # Page-specific suggestions
    if page_context == "bill-buster":
        return [
            "How can I reduce my medical bill?",
            "What are common billing errors?",
            "How do I negotiate hospital charges?",
            "What is the claim process?"
        ]
    elif page_context == "get-quote":
        return [
            "What factors affect my premium?",
            "How do I choose the right sum insured?",
            "What are pre-existing conditions?",
            "Should I choose a deductible?"
        ]
    elif page_context == "dashboard":
        return [
            "How do I file a claim?",
            "Where are my network hospitals?",
            "What is covered in my plan?",
            "How do I renew my policy?"
        ]
    
    # Intent-based suggestions
    if intent == "claims":
        return [
            "How do I file a cashless claim?",
            "What documents are needed for reimbursement?",
            "How long does claim settlement take?",
            "What if my claim is rejected?"
        ]
    elif intent == "plans":
        return [
            "What's the difference between plans?",
            "How do I compare insurance plans?",
            "Which plan is best for families?",
            "What coverage do I need?"
        ]
    elif intent == "hospitals":
        return [
            "How do I find network hospitals?",
            "What is cashless treatment?",
            "Can I go to any hospital?",
            "What is pre-authorization?"
        ]
    
    # Default suggestions
    return [
        "What are pre-existing conditions?",
        "How do I file a claim?",
        "What is a network hospital?",
        "How do I compare plans?"
    ]


def get_user_profile_context(user_id=None):
    """
    Fetch user profile data to personalize responses
    Returns dict with user's preferences, plans, location, etc.
    """
    if not user_id:
        return None
    
    try:
        # Try to import User model
        from app.models.models import User
        from flask_login import current_user
        
        # Get user from database
        if current_user.is_authenticated:
            user = current_user
            
            profile = {
                "user_id": user.id,
                "name": getattr(user, 'name', None) or getattr(user, 'email', 'User'),
                "email": getattr(user, 'email', None),
                "age": getattr(user, 'age', None),
                "state": getattr(user, 'state', None),
                "city": getattr(user, 'city', None),
                # Add more fields as available in your User model
            }
            
            current_app.logger.info(f"📊 User profile loaded: {profile['name']}")
            return profile
    except Exception as e:
        current_app.logger.warning(f"⚠️ Could not load user profile: {e}")
    
    return None
    current_app.logger.info(f"💾 Saved index with {len(_docs)} documents to {INDEX_DIR}")


@CHAT_BP.route("/index", methods=["POST"])
def index_route():
    """
    POST /api/chat/index
    Body: { "docs": [{"id":"...", "text":"...", "meta":{...}}, ...] }
    
    Indexes documents for RAG retrieval.
    """
    try:
        payload = request.get_json(force=True)
        docs = payload.get("docs") or []
        
        if not docs:
            return jsonify({"error": "no docs provided"}), 400
        
        current_app.logger.info(f"📥 Indexing {len(docs)} documents...")
        
        ensure_index()
        model = get_embed_model()
        
        # Extract texts and generate embeddings
        texts = [d["text"] for d in docs]
        current_app.logger.info(f"🔄 Generating embeddings for {len(texts)} chunks...")
        
        embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        
        # Add to FAISS and store metadata
        for i, d in enumerate(docs):
            _docs.append(d)
        
        _faiss_index.add(embs)
        save_index()
        
        return jsonify({
            "status": "success",
            "added": len(docs),
            "total": len(_docs),
            "index_size": _faiss_index.ntotal
        })
    
    except Exception as e:
        current_app.logger.exception("❌ Indexing failed")
        return jsonify({"error": "indexing failed", "detail": str(e)}), 500


def retrieve(query, top_k=TOP_K_DEFAULT, page_context=None, intent=None):
    """
    Retrieve top-k most relevant document chunks for query
    Supports filtering by page_context and intent for better results
    """
    ensure_index()
    
    if len(_docs) == 0:
        current_app.logger.warning("⚠️  No documents in index")
        return []
    
    model = get_embed_model()
    q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    
    # Search FAISS index (retrieve more candidates for filtering)
    search_k = min(top_k * 3, len(_docs))  # Get 3x candidates for filtering
    D, I = _faiss_index.search(q_emb, search_k)
    
    candidates = []
    for score, idx in zip(D[0].tolist(), I[0].tolist()):
        if idx < 0 or idx >= len(_docs):
            continue
        candidates.append({
            "score": float(score),
            "doc": _docs[idx],
            "idx": idx
        })
    
    # Apply page context and intent filtering
    if page_context or intent:
        filtered = []
        for cand in candidates:
            doc_meta = cand["doc"].get("meta", {})
            doc_url = cand["doc"].get("url", "")
            
            # Boost score if document matches page context
            boost = 0.0
            if page_context:
                if page_context in doc_url or page_context in str(doc_meta.get("page_type", "")):
                    boost += 0.15  # 15% boost for page match
            
            # Boost score if document matches intent
            if intent:
                doc_topics = doc_meta.get("topics", [])
                doc_keywords = doc_meta.get("keywords", [])
                if intent in doc_topics or intent in doc_keywords:
                    boost += 0.1  # 10% boost for intent match
            
            # Apply boost
            cand["score"] = cand["score"] + boost
            filtered.append(cand)
        
        # Re-sort by boosted scores
        filtered.sort(key=lambda x: x["score"], reverse=True)
        candidates = filtered
    
    # Return top-k after filtering
    return candidates[:top_k]


def build_prompt(query, retrieved, context_messages=None, user_profile=None, max_doc_chars=1500):
    """
    Build the final prompt for LLM with:
    - System instruction
    - User profile context (if available)
    - Retrieved document snippets with source IDs
    - Optional conversation context
    - User question
    """
    sys_prompt = os.environ.get("CHAT_SYSTEM_PROMPT", SYSTEM_PROMPT_TEXT)
    
    # User profile context (personalization)
    profile_block = ""
    if user_profile:
        profile_block = "\n\nUSER PROFILE:\n"
        if user_profile.get("name"):
            profile_block += f"Name: {user_profile['name']}\n"
        if user_profile.get("age"):
            profile_block += f"Age: {user_profile['age']}\n"
        if user_profile.get("state"):
            profile_block += f"Location: {user_profile.get('city', '')}, {user_profile['state']}\n"
        profile_block += "(Use this to personalize recommendations)\n"
    
    # Format retrieved documents
    doc_texts = []
    for r in retrieved:
        txt = r["doc"]["text"]
        # Trim long documents
        txt = txt if len(txt) <= max_doc_chars else txt[:max_doc_chars] + " …"
        doc_id = r["doc"].get("id", "unknown")
        score = r["score"]
        meta = r["doc"].get("meta", {})
        
        doc_texts.append(
            f"[source:{doc_id}] (score: {score:.3f})\n{txt}\n(metadata: {json.dumps(meta)})"
        )
    
    # Optional conversation context
    context_block = ""
    if context_messages:
        ctxs = []
        for m in context_messages[-6:]:  # Last 6 messages
            role = m.get("role", "user")
            text = m.get("text", "")
            ctxs.append(f"{role.upper()}: {text}")
        context_block = "\n\nCONVERSATION CONTEXT:\n" + "\n".join(ctxs) + "\n"
    
    # Build final prompt
    docs_block = "RETRIEVED DOCUMENTS:\n" + "\n\n".join(doc_texts) + "\n\n"
    user_block = f"USER QUESTION: {query}\n\n"
    instruction = (
        "INSTRUCTION:\n"
        "- Use ONLY the retrieved documents to answer.\n"
        "- Cite documents inline: [source:ID].\n"
        "- If documents don't answer the question, say: \"I don't know this from the provided sources. Would you like me to search more documents or connect you with a human agent?\"\n"
        "- Provide brief answer first, then details with evidence snippets.\n"
        "- Include Sources list at the end.\n"
        "- If user profile is provided, personalize the answer based on their age/location.\n\n"
    )
    
    prompt = sys_prompt + profile_block + "\n\n" + docs_block + context_block + user_block + instruction + "ANSWER:"
    
    return prompt


def call_llm(prompt, max_tokens=MAX_TOKENS, temperature=TEMPERATURE):
    """Generate response using local LLM via llama-cpp-python"""
    llm = get_llm()
    
    current_app.logger.info(f"🤖 Calling LLM (max_tokens={max_tokens}, temp={temperature})")
    current_app.logger.debug(f"Prompt length: {len(prompt)} chars")
    
    # Generate response
    resp = llm(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.95,
        stop=["USER:", "QUESTION:", "\n\n\n"],  # Stop sequences
        echo=False
    )
    
    # Extract text from response
    if "choices" in resp and len(resp["choices"]) > 0:
        content = resp["choices"][0].get("text") or resp["choices"][0].get("message", {}).get("content", "")
    else:
        content = resp.get("text", "")
    
    return content.strip()


@CHAT_BP.route("/query", methods=["POST"])
def query_route():
    """
    POST /api/chat/query
    Body: {
        "query": "user question",
        "session_id": "optional-session-id",
        "context": [{"role": "user", "text": "..."}, ...],  // optional conversation history
        "top_k": 5  // optional, number of docs to retrieve
    }
    
    Returns: {
        "answer": "LLM generated answer with citations",
        "query": "original query",
        "sources": [{"id": "...", "score": 0.95, "meta": {...}}, ...],
        "latency_s": 1.23,
        "model_info": {"path": "...", "tokens": 512}
    }
    """
    try:
        data = request.get_json(force=True)
        query = data.get("query")
        session_id = data.get("session_id")
        top_k = int(data.get("top_k", TOP_K_DEFAULT))
        context = data.get("context")
        page_context = data.get("page_context")  # NEW: page type (bill-buster, get-quote, etc.)
        user_id = data.get("user_id")  # NEW: user ID for personalization
        
        if not query:
            return jsonify({"error": "missing query"}), 400
        
        current_app.logger.info(f"💬 Query: '{query[:100]}...' | Page: {page_context} | Session: {session_id}")
        
        t0 = time.time()
        
        # PHASE 1 & 2: Query Classification (Greeting/Small Talk Detection)
        query_classification = classify_query(query)
        query_type = query_classification["type"]
        intent = query_classification.get("intent")
        
        current_app.logger.info(f"🏷️  Query type: {query_type}, Intent: {intent}")
        
        # Handle greetings without RAG
        if query_type == "greeting":
            response = get_greeting_response()
            response["latency_s"] = round(time.time() - t0, 3)
            return jsonify(response)
        
        # Handle small talk
        if query_type == "small_talk":
            response = get_small_talk_response(query)
            response["latency_s"] = round(time.time() - t0, 3)
            return jsonify(response)
        
        # Handle unclear queries with suggestions
        if query_type == "unclear":
            suggestions = get_suggested_questions(page_context, intent)
            return jsonify({
                "answer": "I'd be happy to help! Could you please be more specific? Here are some questions I can answer:\n\n" + 
                          "\n".join([f"• {q}" for q in suggestions]),
                "query": query,
                "sources": [],
                "suggestions": suggestions,
                "latency_s": round(time.time() - t0, 3),
                "query_type": "unclear"
            })
        
        # PHASE 3: User Profile Integration (Personalization)
        user_profile = None
        if user_id or session_id:
            user_profile = get_user_profile_context(user_id)
        
        # PHASE 2: Retrieve with page context and intent filtering
        current_app.logger.info(f"🔍 Retrieving top-{top_k} documents (page: {page_context}, intent: {intent})...")
        retrieved = retrieve(query, top_k=top_k, page_context=page_context, intent=intent)
        
        if not retrieved:
            suggestions = get_suggested_questions(page_context, intent)
            return jsonify({
                "answer": "I don't have any documents indexed yet to answer your question. Here are some topics I can help with:\n\n" +
                          "\n".join([f"• {q}" for q in suggestions]),
                "query": query,
                "sources": [],
                "suggestions": suggestions,
                "latency_s": time.time() - t0,
                "warning": "No documents in index"
            })
        
        current_app.logger.info(f"✅ Retrieved {len(retrieved)} documents (scores: {[r['score'] for r in retrieved[:3]]})")
        
        # PHASE 1: Build prompt with user profile context
        prompt = build_prompt(query, retrieved, context_messages=context, user_profile=user_profile)
        
        # Step 3: Call local LLM
        try:
            answer = call_llm(prompt, max_tokens=MAX_TOKENS, temperature=TEMPERATURE)
            
            # PHASE 1: Better fallback if LLM returns empty/too short
            if not answer or len(answer.strip()) < 20:
                current_app.logger.warning("⚠️  LLM returned empty/short response, using fallback")
                raise ValueError("LLM response too short")
                
        except Exception as e:
            current_app.logger.exception("❌ LLM call failed")
            
            # PHASE 1: Improved fallback with suggestions
            suggestions = get_suggested_questions(page_context, intent)
            fallback_answer = (
                f"I found {len(retrieved)} relevant documents but had trouble generating a complete answer. "
                f"Here are the key sources I found:\n\n"
            )
            for i, r in enumerate(retrieved[:3], 1):
                doc_id = r["doc"].get("id", "unknown")
                snippet = r["doc"]["text"][:200] + "..."
                fallback_answer += f"{i}. [source:{doc_id}] {snippet}\n\n"
            
            fallback_answer += "\n\n**Suggested questions:**\n" + "\n".join([f"• {q}" for q in suggestions])
            
            return jsonify({
                "answer": fallback_answer,
                "query": query,
                "sources": [{"id": r["doc"].get("id"), "score": r["score"], "meta": r["doc"].get("meta")} for r in retrieved],
                "suggestions": suggestions,
                "latency_s": time.time() - t0,
                "error": "LLM unavailable, showing retrieval results",
                "detail": str(e)
            })
        
        latency = time.time() - t0
        
        current_app.logger.info(f"✅ Response generated in {latency:.2f}s")
        
        # Return structured response
        response = {
            "answer": answer,
            "query": query,
            "query_type": query_type,
            "intent": intent,
            "sources": [
                {
                    "id": r["doc"].get("id"),
                    "score": r["score"],
                    "meta": r["doc"].get("meta"),
                    "snippet": r["doc"]["text"][:200] + "..." if len(r["doc"]["text"]) > 200 else r["doc"]["text"]
                }
                for r in retrieved
            ],
            "latency_s": round(latency, 3),
            "model_info": {
                "path": str(MODEL_PATH),
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE
            },
            "personalized": user_profile is not None
        }
        
        return jsonify(response)
    
    except Exception as e:
        current_app.logger.exception("❌ Query processing failed")
        return jsonify({
            "error": "query processing failed",
            "detail": str(e)
        }), 500


@CHAT_BP.route("/feedback", methods=["POST"])
def feedback_route():
    """
    POST /api/chat/feedback
    Body: {
        "query": "original query",
        "answer": "LLM answer",
        "rating": 1 or -1,  // thumbs up/down
        "comment": "optional user comment"
    }
    
    Stores user feedback for model improvement.
    """
    try:
        data = request.get_json(force=True)
        query = data.get("query")
        answer = data.get("answer")
        rating = data.get("rating")
        comment = data.get("comment", "")
        
        # Store feedback (you can save to database or file)
        feedback_file = BASE_DIR / "chat_index" / "feedback.jsonl"
        feedback_file.parent.mkdir(parents=True, exist_ok=True)
        
        feedback_entry = {
            "timestamp": time.time(),
            "query": query,
            "answer": answer,
            "rating": rating,
            "comment": comment
        }
        
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")
        
        current_app.logger.info(f"📝 Feedback saved: rating={rating}, query='{query[:50]}...'")
        
        return jsonify({"status": "success", "message": "Thank you for your feedback!"})
    
    except Exception as e:
        current_app.logger.exception("❌ Feedback storage failed")
        return jsonify({"error": "feedback failed", "detail": str(e)}), 500


@CHAT_BP.route("/status", methods=["GET"])
def status_route():
    """
    GET /api/chat/status
    
    Returns chatbot system status and statistics.
    """
    try:
        ensure_index()
        
        model_exists = MODEL_PATH.exists()
        model_size_gb = MODEL_PATH.stat().st_size / (1024**3) if model_exists else 0
        
        return jsonify({
            "status": "operational",
            "index": {
                "total_docs": len(_docs),
                "faiss_size": _faiss_index.ntotal if _faiss_index else 0,
                "embedding_dim": _dim,
                "embedding_model": EMBED_MODEL_NAME
            },
            "llm": {
                "model_path": str(MODEL_PATH),
                "model_exists": model_exists,
                "model_size_gb": round(model_size_gb, 2),
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "loaded": _llm is not None
            },
            "config": {
                "top_k_default": TOP_K_DEFAULT,
                "index_dir": str(INDEX_DIR)
            }
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
