#!/usr/bin/env python3
"""
Quick test script for RAG chatbot (without LLM model)
Tests document indexing and retrieval only
"""
import requests
import json

API_BASE = "http://127.0.0.1:5001"

def test_status():
    """Test chatbot status endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Chatbot Status")
    print("="*60)
    
    resp = requests.get(f"{API_BASE}/api/chat/status")
    data = resp.json()
    
    print(f"Status: {data.get('status')}")
    print(f"Documents indexed: {data.get('index', {}).get('total_docs', 0)}")
    print(f"LLM model exists: {data.get('llm', {}).get('model_exists', False)}")
    print(f"Embedding model: {data.get('index', {}).get('embedding_model')}")
    
    return data

def test_indexing():
    """Test document indexing"""
    print("\n" + "="*60)
    print("TEST 2: Document Indexing")
    print("="*60)
    
    test_docs = [
        {
            "id": "test-doc-1",
            "text": "Health insurance covers medical expenses including hospitalization, surgery, and medication costs.",
            "meta": {"category": "test", "source": "manual"}
        },
        {
            "id": "test-doc-2",
            "text": "Pre-existing conditions are medical conditions that exist before you buy health insurance.",
            "meta": {"category": "test", "source": "manual"}
        }
    ]
    
    resp = requests.post(
        f"{API_BASE}/api/chat/index",
        json={"docs": test_docs}
    )
    
    data = resp.json()
    print(f"Added: {data.get('added')} documents")
    print(f"Total indexed: {data.get('total')} documents")
    
    return data

def test_query_without_llm():
    """Test query (will fail gracefully without LLM)"""
    print("\n" + "="*60)
    print("TEST 3: Query (Retrieval Only)")
    print("="*60)
    
    query = "What are pre-existing conditions?"
    print(f"Query: {query}")
    
    try:
        resp = requests.post(
            f"{API_BASE}/api/chat/query",
            json={"query": query, "top_k": 3},
            timeout=30
        )
        
        data = resp.json()
        
        if 'error' in data:
            print(f"\n⚠️  Expected error (LLM not available):")
            print(f"   {data.get('error')}")
            print(f"\n✅ But retrieval worked! Found {len(data.get('sources', []))} sources:")
            for src in data.get('sources', [])[:3]:
                print(f"   - {src['id']} (score: {src['score']:.2f})")
        else:
            print(f"\n✅ Answer: {data.get('answer', '')[:200]}...")
            print(f"\n📚 Sources: {len(data.get('sources', []))} found")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")

def main():
    print("\n🧪 AI-MedPay RAG Chatbot - Quick Test")
    print("="*60)
    print("This tests the chatbot API endpoints")
    print("Note: LLM model is optional for this test")
    print("="*60)
    
    try:
        # Test 1: Status
        test_status()
        
        # Test 2: Indexing
        test_indexing()
        
        # Test 3: Query (retrieval only)
        test_query_without_llm()
        
        print("\n" + "="*60)
        print("✅ TESTS COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("  1. Download LLM model: See CHATBOT_SETUP.md")
        print("  2. Index full docs: python scripts/index_docs.py")
        print("  3. Test widget: Visit http://127.0.0.1:5001/")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Flask server")
        print("Please start the server first:")
        print("  cd backend")
        print("  export PYTHONPATH=/Users/varadpendkar/Documents/project/backend")
        print("  python -m app.main")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
