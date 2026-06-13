import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import BM25

def test_bm25_basic():
    bm = BM25()
    corpus = [
        "the quick brown fox",
        "jumped over the lazy dog",
        "the dog barked at the mailman"
    ]
    bm.index(corpus)
    res = bm.search("dog", top_k=2)
    assert len(res) <= 2
    docs_with_dog = [idx for score, idx in res]
    assert 1 in docs_with_dog
    assert 2 in docs_with_dog
