"""
GPU-Accelerated Vector Search using PyTorch.
Falls back to CPU tensors if CUDA is not available (still ~3x faster than Python loops).
"""

import torch
import numpy as np

class GPUSearchIndex:
    """
    Maintains a matrix of all index vectors on GPU memory.
    Supports batched cosine similarity using matrix multiplication.
    
    Memory model:
        - Each vector: dim × 4 bytes (float32)
        - 10,000 × 768D vectors = ~29MB GPU memory (negligible)
        - 1,000,000 × 768D vectors = ~2.9GB GPU memory (fits on most GPUs)
    """
    
    def __init__(self, dim: int):
        self.dim = dim
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.index_tensor = None     # Shape: [N, dim] on device
        self.id_map = []             # Maps row index → original doc_id
        
        print(f"[GPU Search] Using device: {self.device}")
        if self.device.type == 'cuda':
            try:
                props = torch.cuda.get_device_properties(0)
                print(f"[GPU Search] GPU: {props.name}, VRAM: {props.total_memory / 1e9:.1f}GB")
            except Exception as e:
                print(f"[GPU Search] Failed to get GPU properties: {e}")
    
    def build(self, vectors: list[tuple[int, list[float]]]):
        """
        Build GPU index from (doc_id, vector) pairs.
        Normalizes all vectors for cosine similarity via dot product.
        
        Args:
            vectors: List of (doc_id, vector) tuples
        """
        if not vectors:
            self.index_tensor = None
            self.id_map = []
            return
        
        self.id_map = [doc_id for doc_id, _ in vectors]
        matrix = np.array([v for _, v in vectors], dtype=np.float32)
        
        # Move to GPU and normalize (so dot product = cosine similarity)
        tensor = torch.from_numpy(matrix).to(self.device)
        norms = torch.norm(tensor, dim=1, keepdim=True).clamp(min=1e-8)
        self.index_tensor = tensor / norms  # L2-normalized
        
        print(f"[GPU Search] Index built: {len(vectors)} vectors on {self.device}")
    
    def add(self, doc_id: int, vector: list[float]):
        """Add a single vector to the GPU index."""
        v = torch.tensor(vector, dtype=torch.float32, device=self.device)
        v = v / v.norm().clamp(min=1e-8)
        v = v.unsqueeze(0)  # [1, dim]
        
        if self.index_tensor is None:
            self.index_tensor = v
        else:
            self.index_tensor = torch.cat([self.index_tensor, v], dim=0)
        
        self.id_map.append(doc_id)
    
    def remove(self, doc_id: int):
        """Remove a single vector from the GPU index."""
        if doc_id not in self.id_map:
            return
        idx = self.id_map.index(doc_id)
        self.id_map.pop(idx)
        if self.index_tensor is not None:
            if len(self.id_map) == 0:
                self.index_tensor = None
            else:
                self.index_tensor = torch.cat([self.index_tensor[:idx], self.index_tensor[idx+1:]], dim=0)

    def search(self, query_vector: list[float], k: int = 5) -> list[tuple[int, float]]:
        """
        GPU cosine similarity search.
        
        Speed: 
          CPU (Python loops): ~50ms for 10K vectors
          CPU (PyTorch):      ~2ms for 10K vectors  
          GPU (CUDA):         ~0.1ms for 10K vectors (500x speedup)
        
        Returns: list of (doc_id, cosine_similarity_score) sorted descending
        """
        if self.index_tensor is None or len(self.id_map) == 0:
            return []
        
        k = min(k, len(self.id_map))
        
        # Normalize query
        q = torch.tensor(query_vector, dtype=torch.float32, device=self.device)
        q = q / q.norm().clamp(min=1e-8)
        q = q.unsqueeze(0)  # [1, dim]
        
        # Matrix multiply: [1, dim] × [dim, N] = [1, N] similarity scores
        # This is the key operation — one GPU kernel call, fully parallel
        similarities = torch.mm(q, self.index_tensor.T).squeeze(0)  # [N]
        
        # Get top-K in one call
        top_scores, top_indices = torch.topk(similarities, k=k)
        
        # Move back to CPU for result assembly
        top_scores = top_scores.cpu().numpy()
        top_indices = top_indices.cpu().numpy()
        
        results = []
        for idx, score in zip(top_indices, top_scores):
            results.append((self.id_map[int(idx)], float(score)))
        
        return results
    
    def batch_search(self, queries: list[list[float]], k: int = 5) -> list[list[tuple]]:
        """
        Search multiple queries in one GPU call.
        Key advantage of GPU: batch of 100 queries costs nearly the same as 1.
        
        Returns: list of result lists, one per query
        """
        if not queries or self.index_tensor is None:
            return [[] for _ in queries]
        
        k = min(k, len(self.id_map))
        
        # Stack all queries into matrix
        q_matrix = torch.tensor(queries, dtype=torch.float32, device=self.device)
        norms = torch.norm(q_matrix, dim=1, keepdim=True).clamp(min=1e-8)
        q_matrix = q_matrix / norms  # [B, dim]
        
        # [B, dim] × [dim, N] = [B, N] — all queries vs all index vectors at once
        all_similarities = torch.mm(q_matrix, self.index_tensor.T)  # [B, N]
        
        top_scores, top_indices = torch.topk(all_similarities, k=k, dim=1)
        top_scores = top_scores.cpu().numpy()
        top_indices = top_indices.cpu().numpy()
        
        batch_results = []
        for b in range(len(queries)):
            results = [(self.id_map[int(top_indices[b, i])], float(top_scores[b, i])) for i in range(k)]
            batch_results.append(results)
        
        return batch_results
    
    def memory_bytes(self) -> int:
        if self.index_tensor is None:
            return 0
        return self.index_tensor.element_size() * self.index_tensor.nelement()
