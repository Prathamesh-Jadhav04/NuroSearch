import heapq
import math

class KDNode:
    def __init__(self, item):
        self.item = item
        self.left = None
        self.right = None

class KDTree:
    def __init__(self, dims):
        self.root = None
        self.dims = dims

    def insert(self, v):
        self.root = self._ins(self.root, v, 0)

    def _ins(self, n, v, d):
        if n is None:
            return KDNode(v)
        ax = d % self.dims
        if v["emb"][ax] < n.item["emb"][ax]:
            n.left = self._ins(n.left, v, d + 1)
        else:
            n.right = self._ins(n.right, v, d + 1)
        return n

    def _knn(self, n, q, k, d, dist, heap):
        if n is None:
            return
        dn = dist(q, n.item["emb"])
        if len(heap) < k:
            heapq.heappush(heap, (-dn, n.item["id"]))
        elif dn < -heap[0][0]:
            heapq.heapreplace(heap, (-dn, n.item["id"]))
        ax = d % self.dims
        diff = q[ax] - n.item["emb"][ax]
        closer = n.left if diff < 0 else n.right
        farther = n.right if diff < 0 else n.left
        self._knn(closer, q, k, d + 1, dist, heap)
        if len(heap) < k or abs(diff) < -heap[0][0]:
            self._knn(farther, q, k, d + 1, dist, heap)

    def knn(self, q, k, dist):
        heap = []
        self._knn(self.root, q, k, 0, dist, heap)
        return sorted([(-neg_d, id_) for neg_d, id_ in heap])

def cosine_distance(a, b):
    import numpy as np
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        dot = np.dot(a, b)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            return 1.0
        return float(1.0 - dot / (na * nb))
    if len(a) > 64:
        a_np = np.asarray(a, dtype=np.float32)
        b_np = np.asarray(b, dtype=np.float32)
        dot = np.dot(a_np, b_np)
        na = np.linalg.norm(a_np)
        nb = np.linalg.norm(b_np)
        if na < 1e-9 or nb < 1e-9:
            return 1.0
        return float(1.0 - dot / (na * nb))
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a)
    nb = sum(x * x for x in b)
    if na < 1e-9 or nb < 1e-9:
        return 1.0
    return 1.0 - dot / (math.sqrt(na) * math.sqrt(nb))

class KDTreeIndex:
    def __init__(self, dim):
        self.dim = dim
        self.kd_tree = KDTree(dims=dim)
        
    def insert(self, id, vector):
        item = {"id": id, "emb": vector}
        self.kd_tree.insert(item)
        
    def search(self, query, k):
        results = self.kd_tree.knn(query, k, dist=cosine_distance)
        return [item_id for dist, item_id in results]
