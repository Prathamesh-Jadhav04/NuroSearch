import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Pre-mock sentence_transformers before import
with patch('sentence_transformers.CrossEncoder') as MockCrossEncoder:
    from reranker import CrossEncoderReranker

def test_reranker_basic():
    with patch('reranker.CrossEncoder') as MockCrossEncoder:
        mock_instance = MockCrossEncoder.return_value
        # Mock predict to return 0.1 for first candidate, 0.9 for second
        mock_instance.predict.return_value = [0.1, 0.9]
        
        reranker = CrossEncoderReranker()
        
        candidates = [
            {"doc_id": 1, "text": "Photosynthesis is bad"},
            {"doc_id": 2, "text": "The powerhouse of the cell is mitochondria"}
        ]
        
        results = reranker.rerank("What is mitochondria?", candidates, top_k=1)
        assert len(results) == 1
        assert results[0][1]["doc_id"] == 2
        assert results[0][0] == 0.9
