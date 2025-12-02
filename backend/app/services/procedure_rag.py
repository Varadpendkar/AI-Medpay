#!/usr/bin/env python3
"""
Procedure-specific RAG service for pre-authorization cost estimation.
Different from chatbot RAG - focuses on structured procedure data retrieval.
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ProcedureRAG:
    """RAG system specifically for medical procedure cost estimation."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.procedures = []
        self.embeddings = None
        self.index = None
        self.procedure_texts = []
        
        # Load and index procedure data
        self._load_procedures()
        self._create_embeddings()
        self._build_index()
    
    def _load_procedures(self):
        """Load procedure knowledge from JSON file."""
        procedure_file = self.data_dir / "procedure_knowledge.json"
        
        if not procedure_file.exists():
            logger.error(f"Procedure knowledge file not found: {procedure_file}")
            return
            
        with open(procedure_file, 'r') as f:
            self.procedures = json.load(f)
            
        logger.info(f"Loaded {len(self.procedures)} procedure records")
    
    def _create_procedure_text(self, procedure: Dict) -> str:
        """Convert procedure dict to searchable text."""
        return f"""
        Procedure: {procedure['procedure']}
        Category: {procedure['category']}
        Cost Range: ₹{procedure['typical_cost_range']}
        Insurance Coverage: {procedure['insurance_coverage']}
        Duration: {procedure['duration']}
        Exclusions: {procedure['common_exclusions']}
        Complications: {procedure['complications']}
        Network Requirements: {procedure['network_preference']}
        """
    
    def _create_embeddings(self):
        """Create embeddings for all procedures."""
        self.procedure_texts = [
            self._create_procedure_text(proc) for proc in self.procedures
        ]
        
        if not self.procedure_texts:
            logger.warning("No procedure texts to embed")
            return
            
        self.embeddings = self.model.encode(self.procedure_texts)
        logger.info(f"Created embeddings: {self.embeddings.shape}")
    
    def _build_index(self):
        """Build FAISS index for fast similarity search."""
        if self.embeddings is None or len(self.embeddings) == 0:
            logger.warning("No embeddings available for indexing")
            return
            
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)
        
        logger.info(f"Built FAISS index with {self.index.ntotal} procedures")
    
    def search_procedure(self, query: str, hospital_chain: str = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant procedures based on query with optional hospital context.
        
        Args:
            query: Search query (e.g., "heart surgery cost estimation")
            hospital_chain: Optional hospital chain (apollo, fortis, max, etc.)
            top_k: Number of top results to return
            
        Returns:
            List of relevant procedure information with similarity scores
        """
        if not self.index or not self.procedures:
            return []
        
        # Enhance query with hospital context if provided
        enhanced_query = query
        if hospital_chain:
            hospital_context = self._get_hospital_context(hospital_chain)
            enhanced_query = f"{query} {hospital_context}"
            
        # Encode query
        query_embedding = self.model.encode([enhanced_query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.procedures):
                result = self.procedures[idx].copy()
                result['similarity_score'] = float(score)
                
                # Add hospital-specific adjustments
                if hospital_chain:
                    result = self._apply_hospital_adjustments(result, hospital_chain)
                
                results.append(result)
        
        return results
    
    def _get_hospital_context(self, hospital_chain: str) -> str:
        """Get hospital-specific context for enhanced search."""
        hospital_contexts = {
            'apollo': 'premium multi-specialty hospital high-end facilities',
            'fortis': 'corporate hospital chain quality healthcare',
            'max': 'super speciality hospital advanced medical care',
            'manipal': 'healthcare network comprehensive services',
            'narayana': 'affordable quality healthcare value-based care',
            'aster': 'international standards medical excellence',
            'aiims': 'government hospital subsidized rates medical college',
            'pgimer': 'government medical institute research hospital',
            'medanta': 'multi-specialty hospital advanced technology',
            'kokilaben': 'premium hospital luxury healthcare services'
        }
        return hospital_contexts.get(hospital_chain.lower(), '')
    
    def _apply_hospital_adjustments(self, procedure_data: Dict, hospital_chain: str) -> Dict:
        """Apply hospital-specific cost and coverage adjustments."""
        # Hospital tier pricing multipliers
        hospital_multipliers = {
            'apollo': 1.3,      # Premium pricing
            'fortis': 1.25,     # Premium pricing
            'max': 1.2,         # High-end pricing
            'medanta': 1.35,    # Premium pricing
            'kokilaben': 1.4,   # Luxury pricing
            'manipal': 1.1,     # Moderate pricing
            'aster': 1.15,      # Moderate-premium pricing
            'narayana': 0.9,    # Value pricing
            'aiims': 0.3,       # Government subsidized
            'pgimer': 0.35,     # Government subsidized
        }
        
        multiplier = hospital_multipliers.get(hospital_chain.lower(), 1.0)
        
        # Adjust cost range
        cost_range = procedure_data.get('typical_cost_range', '100000-300000')
        if '-' in cost_range:
            low, high = cost_range.split('-')
            low_adjusted = int(int(low) * multiplier)
            high_adjusted = int(int(high) * multiplier)
            procedure_data['hospital_adjusted_cost'] = f"{low_adjusted}-{high_adjusted}"
        
        # Add hospital-specific notes
        hospital_notes = {
            'apollo': 'Premium facilities, international standards, higher out-of-pocket',
            'fortis': 'Corporate hospital with good insurance network coverage',
            'max': 'Super-specialty care with comprehensive insurance acceptance',
            'medanta': 'Advanced medical technology, premium pricing',
            'kokilaben': 'Luxury healthcare services, highest cost tier',
            'narayana': 'Value-based healthcare, cost-effective option',
            'aiims': 'Government hospital, heavily subsidized, long waiting times',
            'pgimer': 'Government medical institute, very low cost, limited private rooms'
        }
        
        procedure_data['hospital_notes'] = hospital_notes.get(hospital_chain.lower(), '')
        procedure_data['hospital_chain'] = hospital_chain.lower()
        
        return procedure_data
    
    def get_procedure_context(self, procedure_name: str) -> Dict[str, Any]:
        """
        Get specific context for a given procedure name.
        
        Args:
            procedure_name: Name of the procedure
            
        Returns:
            Procedure context with cost estimates and coverage info
        """
        # Direct match first
        for proc in self.procedures:
            if proc['procedure'].lower() == procedure_name.lower():
                return proc
        
        # Fuzzy search if no direct match
        results = self.search_procedure(procedure_name, top_k=1)
        return results[0] if results else {}
    
    def estimate_costs(self, procedure_name: str, user_profile: Dict = None) -> Dict[str, Any]:
        """
        Generate cost estimates based on procedure and user profile.
        
        Args:
            procedure_name: Name of the medical procedure
            user_profile: User information (age, location, etc.)
            
        Returns:
            Cost estimation with contextual information
        """
        context = self.get_procedure_context(procedure_name)
        
        if not context:
            return {
                'error': 'Procedure not found in knowledge base',
                'procedure': procedure_name
            }
        
        # Parse cost range
        cost_range = context.get('typical_cost_range', '100000-200000')
        try:
            min_cost, max_cost = map(int, cost_range.split('-'))
        except:
            min_cost, max_cost = 100000, 200000
        
        # Generate estimates based on context
        base_cost = (min_cost + max_cost) // 2
        
        # Adjust for user profile if provided
        if user_profile:
            age = user_profile.get('age', 35)
            if age > 60:
                base_cost = int(base_cost * 1.2)  # Higher cost for seniors
            elif age < 25:
                base_cost = int(base_cost * 0.9)  # Lower cost for young adults
        
        return {
            'procedure': procedure_name,
            'context': context,
            'estimated_cost': base_cost,
            'cost_range': {
                'min': min_cost,
                'max': max_cost
            },
            'coverage_info': context.get('insurance_coverage', 'Coverage varies'),
            'recommendations': self._generate_recommendations(context)
        }
    
    def _generate_recommendations(self, context: Dict) -> List[str]:
        """Generate contextual recommendations based on procedure."""
        recommendations = []
        
        category = context.get('category', '')
        duration = context.get('duration', '')
        network_pref = context.get('network_preference', '')
        
        if 'day-care' in duration.lower():
            recommendations.append("Consider day-care packages for lower costs")
        
        if 'cardiac' in category.lower():
            recommendations.append("Ensure hospital has cardiac ICU facilities")
            
        if 'specialty' in network_pref.lower():
            recommendations.append("Choose plans with specialist hospital networks")
            
        recommendations.append("Pre-authorization is strongly recommended")
        
        return recommendations


def create_procedure_rag(project_root: Path) -> ProcedureRAG:
    """Factory function to create ProcedureRAG instance."""
    data_dir = project_root / "data"
    return ProcedureRAG(data_dir)


if __name__ == "__main__":
    # Test the RAG system
    project_root = Path(__file__).parent.parent.parent
    rag = create_procedure_rag(project_root)
    
    # Test queries
    test_queries = [
        "heart surgery",
        "appendectomy cost",
        "knee replacement surgery",
        "cataract operation"
    ]
    
    for query in test_queries:
        print(f"\n=== Testing: {query} ===")
        results = rag.search_procedure(query, top_k=2)
        for result in results:
            print(f"Procedure: {result['procedure']}")
            print(f"Score: {result['similarity_score']:.3f}")
            print(f"Cost: ₹{result['typical_cost_range']}")
            print()