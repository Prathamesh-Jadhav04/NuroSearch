import logging
from sentence_transformers import CrossEncoder
import numpy as np

logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    """
    Two-stage retrieval: 
      Stage 1 (caller): HNSW retrieves top-N candidates (fast, approximate)
      Stage 2 (this):   Cross-encoder re-ranks top-N precisely
    """
    
    def __init__(self, model_name='cross-encoder/ms-marco-MiniLM-L-6-v2', device=None):
        """
        Args:
            model_name (str): HuggingFace model path or name.
            device (str): Device to run the model on (e.g. 'cpu', 'cuda').
        """
        logger.info(f"Initializing CrossEncoderReranker with model: {model_name}")
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def model(self):
        """Lazy load the CrossEncoder model to avoid slow import/loading at startup if not used."""
        if self._model is None:
            print(f"[Reranker] Lazy-loading cross-encoder model: {self.model_name}...")
            self._model = CrossEncoder(self.model_name, max_length=512, device=self.device)
            print("[Reranker] Model loading complete.")
        return self._model

    def rerank(self, query: str, candidates: list, top_k: int = 3) -> list:
        """
        Re-rank candidate chunks by cross-encoder relevance score.
        
        Args:
            query:      The user's question (raw text string)
            candidates: List of dicts, or list of (distance, dict) tuples.
            top_k:      How many to return after re-ranking
            
        Returns:
            List of tuples (score, original_candidate) sorted by score descending.
        """
        if not candidates:
            return []
            
        # Parse inputs: support both list of dicts and list of (distance, dict) tuples
        doc_list = []
        for doc in candidates:
            if isinstance(doc, tuple) and len(doc) == 2:
                # doc is (distance, doc_dict)
                doc_list.append(doc[1])
            elif isinstance(doc, dict):
                doc_list.append(doc)
            else:
                doc_list.append(doc)
        
        # Build (query, document) pairs for cross-encoder
        pairs = []
        for doc in doc_list:
            text = ""
            if isinstance(doc, dict):
                text = doc.get("text") or doc.get("content") or doc.get("title") or ""
            else:
                text = str(doc)
            pairs.append([query, text])
            
        # Score all pairs in one batch (cross-encoder sees both together)
        scores = self.model.predict(pairs)
        
        # Zip scores and original document elements
        ranked = []
        for score, original_doc in zip(scores, candidates):
            ranked.append((float(score), original_doc))
            
        # Sort by score descending (higher = more relevant)
        ranked.sort(key=lambda x: x[0], reverse=True)
        
        return ranked[:top_k]
