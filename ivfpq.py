import numpy as np
from sklearn.cluster import MiniBatchKMeans

class IVFPQIndex:
    """
    Inverted File Index + Product Quantization.
    Compresses 768D float vectors into M byte codes using sub-vector clustering.
    
    Architecture:
      - IVF: K-Means partitions dataset into C clusters (coarse quantization)
      - PQ:  Each vector split into M sub-vectors, each sub-vector compressed to 1 byte
      - Search: Only probe nearest N_PROBE clusters, use lookup table for fast distance
    """
    
    def __init__(self, dim=768, M=8, C=256, n_probe=8, metric="cosine"):
        """
        Args:
            dim:     Vector dimensionality (768 for nomic-embed-text)
            M:       Number of sub-vector segments (dim must be divisible by M)
            C:       Number of IVF clusters (coarse quantizers)
            n_probe: How many IVF clusters to search at query time
            metric:  Distance metric to use (for compatibility)
        """
        self.dim = dim
        self.M = M                        # Number of PQ sub-spaces
        self.sub_dim = dim // M           # Dimension per sub-space (768//8 = 96)
        assert dim % M == 0, f"IVF-PQ: dim ({dim}) must be divisible by M ({M}), got remainder {dim % M}"
        self.C = C                        # Number of IVF centroids
        self.n_probe = n_probe
        self.metric = metric
        self.K = 256                      # Codebook size per sub-space (fits in 1 byte)
        
        self.ivf_quantizer = None         # Coarse K-Means (C centroids)
        self.pq_codebooks = None          # Shape: [M, K, sub_dim] — PQ codebooks
        self.inverted_lists = {}          # cluster_id -> list of (doc_id, pq_code)
        self.id_map = {}                  # index position -> original doc_id
        self.raw_store = {}               # doc_id -> raw vector (list of floats)
        self.is_trained = False
    
    def train(self, vectors):
        """
        Train IVF coarse quantizer and PQ codebooks on a set of vectors.
        Supports:
          - np.ndarray of shape [N, dim]
          - list of list of floats
          - list of dicts: [{"id": ..., "emb": [...]}] or [{"emb": [...]}]
        """
        parsed_vectors = []
        if isinstance(vectors, np.ndarray):
            parsed_vectors = vectors.tolist()
        elif isinstance(vectors, list):
            for v in vectors:
                if isinstance(v, dict):
                    emb = v.get("emb") or v.get("embedding")
                    if emb:
                        parsed_vectors.append(list(emb))
                elif isinstance(v, (list, tuple)):
                    # Check if it is a (doc_id, vector) tuple or just a vector
                    if len(v) == 2 and isinstance(v[0], (int, str)) and isinstance(v[1], (list, tuple, np.ndarray)):
                        parsed_vectors.append(list(v[1]))
                    else:
                        parsed_vectors.append(list(v))
                else:
                    parsed_vectors.append(v)
        else:
            parsed_vectors = vectors
            
        vectors = np.array(parsed_vectors, dtype=np.float32)
        N = len(vectors)
        if N < 2:
            # Fallback if too few vectors to train: just set trained but use brute force
            print(f"[IVF-PQ] Not enough vectors to train ({N}), skipping clustering.")
            self.is_trained = True
            return
            
        # Dynamically adjust C and K to prevent KMeans from failing if samples < clusters
        original_C = self.C
        if N < self.C:
            self.C = max(2, N)
            print(f"[IVF-PQ] Dynamically reducing C from {original_C} to {self.C} due to small dataset")
            
        original_K = self.K
        if N < self.K:
            self.K = max(2, N)
            print(f"[IVF-PQ] Dynamically reducing K from {original_K} to {self.K} due to small dataset")
            
        # --- Stage 1: Train IVF coarse quantizer ---
        print(f"[IVF-PQ] Training IVF with {self.C} clusters on {N} vectors...")
        self.ivf_quantizer = MiniBatchKMeans(n_clusters=self.C, random_state=42, batch_size=min(512, N))
        self.ivf_quantizer.fit(vectors)
        
        # --- Stage 2: Train PQ codebooks ---
        # Compute IVF residuals
        assignments = self.ivf_quantizer.predict(vectors)
        residuals = vectors - self.ivf_quantizer.cluster_centers_[assignments]
        
        print(f"[IVF-PQ] Training PQ codebooks: {self.M} sub-spaces × {self.K} codes...")
        self.pq_codebooks = np.zeros((self.M, self.K, self.sub_dim), dtype=np.float32)
        
        for m in range(self.M):
            sub_vecs = residuals[:, m * self.sub_dim : (m + 1) * self.sub_dim]
            kmeans = MiniBatchKMeans(n_clusters=self.K, random_state=42, batch_size=min(512, N))
            kmeans.fit(sub_vecs)
            self.pq_codebooks[m] = kmeans.cluster_centers_
        
        self.is_trained = True
        print("[IVF-PQ] Training complete. Encoding stored vectors...")
        
        # Encode all raw vectors currently in raw_store
        self.inverted_lists = {}
        for doc_id, raw_v in self.raw_store.items():
            ivf_id, pq_code = self.encode(np.array(raw_v, dtype=np.float32))
            if ivf_id not in self.inverted_lists:
                self.inverted_lists[ivf_id] = []
            self.inverted_lists[ivf_id].append((doc_id, pq_code))
            
    def encode(self, vector: np.ndarray) -> tuple[int, np.ndarray]:
        """
        Compress a single vector into M bytes using trained PQ codebooks.
        Returns: tuple of (ivf_id, pq_code)
        """
        assert self.is_trained, "Call train() before encode()"
        vector = np.array(vector, dtype=np.float32)
        
        # Fallback if quantizer wasn't trained (e.g. N < 2)
        if self.ivf_quantizer is None:
            return 0, np.zeros(self.M, dtype=np.uint8)
            
        # IVF assignment
        ivf_id = self.ivf_quantizer.predict(vector.reshape(1, -1))[0]
        residual = vector - self.ivf_quantizer.cluster_centers_[ivf_id]
        
        # PQ encode
        code = np.zeros(self.M, dtype=np.uint8)
        for m in range(self.M):
            sub_vec = residual[m * self.sub_dim : (m + 1) * self.sub_dim]
            diffs = self.pq_codebooks[m] - sub_vec         # [K, sub_dim]
            distances = np.sum(diffs ** 2, axis=1)          # [K]
            code[m] = np.argmin(distances)
        
        return int(ivf_id), code
    
    def add(self, doc_id: int, vector):
        """Add a single vector to the index. Stores raw vector and encodes if trained."""
        if isinstance(vector, np.ndarray):
            vector_np = vector.astype(np.float32)
            vector_list = vector.tolist()
        else:
            vector_np = np.array(vector, dtype=np.float32)
            vector_list = list(vector)
            
        self.raw_store[doc_id] = vector_list
        
        if self.is_trained:
            ivf_id, pq_code = self.encode(vector_np)
            if ivf_id not in self.inverted_lists:
                self.inverted_lists[ivf_id] = []
            self.inverted_lists[ivf_id].append((doc_id, pq_code))
            
    def remove(self, doc_id: int):
        """Remove a vector from the index by its ID."""
        if doc_id in self.raw_store:
            del self.raw_store[doc_id]
        
        for ivf_id, lists in list(self.inverted_lists.items()):
            new_list = [(d_id, code) for d_id, code in lists if d_id != doc_id]
            self.inverted_lists[ivf_id] = new_list
            
    def search(self, query_vector: np.ndarray, k: int = 5) -> list:
        """
        Search using ADC (Asymmetric Distance Computation).
        Returns: list of (approximate_distance, doc_id) sorted by distance
        """
        query = np.array(query_vector, dtype=np.float32)
        
        # If not trained or no clusters, fallback to brute force search on raw_store
        if not self.is_trained or self.ivf_quantizer is None or not self.inverted_lists:
            # Brute force search using cosine distance
            candidates = []
            for doc_id, v in self.raw_store.items():
                v_np = np.array(v, dtype=np.float32)
                dot = np.dot(query, v_np)
                norm_q = np.linalg.norm(query)
                norm_v = np.linalg.norm(v_np)
                if norm_q > 1e-9 and norm_v > 1e-9:
                    dist = 1.0 - dot / (norm_q * norm_v)
                else:
                    dist = 1.0
                candidates.append((dist, doc_id))
            candidates.sort(key=lambda x: x[0])
            return candidates[:k]
            
        # Find nearest IVF clusters to probe
        dists_to_centroids = np.sum(
            (self.ivf_quantizer.cluster_centers_ - query) ** 2, axis=1
        )
        probe_clusters = np.argsort(dists_to_centroids)[:min(self.n_probe, self.C)]
        
        # Build lookup table
        lookup_table = np.zeros((self.M, self.K), dtype=np.float32)
        for m in range(self.M):
            q_sub = query[m * self.sub_dim : (m + 1) * self.sub_dim]
            diffs = self.pq_codebooks[m] - q_sub            # [K, sub_dim]
            lookup_table[m] = np.sum(diffs ** 2, axis=1)
        
        # Score candidates in probed clusters
        candidates = []
        for cluster_id in probe_clusters:
            for doc_id, pq_code in self.inverted_lists.get(cluster_id, []):
                approx_dist = 0.0
                for m in range(self.M):
                    approx_dist += lookup_table[m, pq_code[m]]
                candidates.append((approx_dist, doc_id))
        
        candidates.sort(key=lambda x: x[0])
        return candidates[:k]
    
    def memory_bytes(self) -> int:
        """Calculate total memory used by the compressed index."""
        total = 0
        for lists in self.inverted_lists.values():
            total += len(lists) * self.M  # M bytes per encoded vector
        return total
        
    def raw_memory_bytes(self) -> int:
        """Calculate memory used by raw float vectors."""
        return len(self.raw_store) * self.dim * 4  # 4 bytes per float
