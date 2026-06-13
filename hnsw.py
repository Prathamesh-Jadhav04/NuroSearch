import math
import random
import heapq

class HNSW:
    def __init__(self, m=16, ef_build=200):
        self.M = m
        self.M0 = 2 * m
        self.ef_build = ef_build
        self.mL = 1.0 / math.log(m)
        self.G = {}
        self.topLayer = -1
        self.entryPt = -1
        self.rng = random.Random(42)

    def _rand_level(self):
        return int(math.floor(-math.log(self.rng.random()) * self.mL))

    def _search_layer(self, q, ep, ef, lyr, dist):
        vis = set()
        cands = []
        found = []  # Max-heap (negative distances) to keep closest ef elements

        d0 = dist(q, self.G[ep]["emb"])
        vis.add(ep)
        heapq.heappush(cands, (d0, ep))
        heapq.heappush(found, (-d0, ep))

        while cands:
            cd, cid = heapq.heappop(cands)
            if cd > -found[0][0]:
                break
            if lyr >= len(self.G[cid]["nbrs"]):
                continue
            for nid in self.G[cid]["nbrs"][lyr]:
                if nid in vis or nid not in self.G:
                    continue
                vis.add(nid)
                nd = dist(q, self.G[nid]["emb"])
                if len(found) < ef or nd < -found[0][0]:
                    heapq.heappush(cands, (nd, nid))
                    heapq.heappush(found, (-nd, nid))
                    if len(found) > ef:
                        heapq.heappop(found)

        return sorted([(-val, nid) for val, nid in found])

    def _select_nbrs(self, cands, max_m):
        return [c[1] for c in cands[:max_m]]

    def insert(self, item, dist_fn):
        id_ = item["id"]
        lvl = self._rand_level()
        self.G[id_] = {**item, "maxLyr": lvl, "nbrs": [[] for _ in range(lvl + 1)]}

        if self.entryPt == -1:
            self.entryPt = id_
            self.topLayer = lvl
            return

        ep = self.entryPt
        for lc in range(self.topLayer, lvl, -1):
            if lc < len(self.G[ep]["nbrs"]) and self.G[ep]["nbrs"][lc]:
                W = self._search_layer(item["emb"], ep, 1, lc, dist_fn)
                if W:
                    ep = W[0][1]

        for lc in range(min(self.topLayer, lvl), -1, -1):
            W = self._search_layer(item["emb"], ep, self.ef_build, lc, dist_fn)
            max_m = self.M0 if lc == 0 else self.M
            sel = self._select_nbrs(W, max_m)
            self.G[id_]["nbrs"][lc] = sel

            for nid in sel:
                if nid not in self.G:
                    continue
                while len(self.G[nid]["nbrs"]) <= lc:
                    self.G[nid]["nbrs"].append([])
                conn = self.G[nid]["nbrs"][lc]
                conn.append(id_)
                if len(conn) > max_m:
                    ds = [(dist_fn(self.G[nid]["emb"], self.G[c]["emb"]), c) for c in conn if c in self.G]
                    ds.sort()
                    self.G[nid]["nbrs"][lc] = [c for _, c in ds[:max_m]]

            if W:
                ep = W[0][1]

        if lvl > self.topLayer:
            self.topLayer = lvl
            self.entryPt = id_

    def knn(self, q, k, ef, dist):
        if self.entryPt == -1:
            return []
        ep = self.entryPt
        for lc in range(self.topLayer, 0, -1):
            if lc < len(self.G[ep]["nbrs"]) and self.G[ep]["nbrs"][lc]:
                W = self._search_layer(q, ep, 1, lc, dist)
                if W:
                    ep = W[0][1]
        W = self._search_layer(q, ep, max(ef, k), 0, dist)
        return W[:k]

def cosine_distance(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a)
    nb = sum(x * x for x in b)
    if na < 1e-9 or nb < 1e-9:
        return 1.0
    return 1.0 - dot / (math.sqrt(na) * math.sqrt(nb))

class HNSWIndex:
    def __init__(self, dim, M=16, ef_build=200):
        self.dim = dim
        self.hnsw = HNSW(m=M, ef_build=ef_build)

    def insert(self, id, vector):
        item = {"id": id, "emb": vector}
        self.hnsw.insert(item, cosine_distance)

    def search(self, query, k):
        results = self.hnsw.knn(query, k, ef=self.hnsw.ef_build, dist=cosine_distance)
        return [item_id for dist, item_id in results]
