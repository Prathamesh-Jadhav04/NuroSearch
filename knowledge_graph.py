"""
NuroSearch Knowledge Graph Integration
Extracts entity-relationship triples from documents and stores in Neo4j.
Used for multi-hop reasoning in GraphRAG queries.
"""

import os
import re
import json
import requests

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "nurosearch")

class KnowledgeGraph:
    
    def __init__(self):
        self.available = False
        self.driver = None
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Test connection with a short timeout
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.available = True
            print(f"[Neo4j] Connected to {NEO4J_URI}")
        except Exception as e:
            self.available = False
            self.driver = None
            print(f"[Neo4j] Unavailable. Dry-run mode active. Reason: {e}")
            
    def extract_triples(self, text: str, title: str) -> list[dict]:
        """
        Use local LLM to extract (subject, relation, object) triples from text.
        Returns list of {"subject": ..., "relation": ..., "object": ...}
        """
        # Get Ollama URL
        host = os.environ.get('OLLAMA_HOST', '127.0.0.1')
        port = os.environ.get('OLLAMA_PORT', '11434')
        env_url = os.environ.get('OLLAMA_BASE_URL')
        if env_url:
            url = f"{env_url.rstrip('/')}/api/generate"
        else:
            url = f"http://{host}:{port}/api/generate"

        prompt = f"""Extract all factual relationships from this text as JSON triples.
        
Text: {text[:1000]}

Return ONLY a JSON array like:
[
  {{"subject": "Tim Cook", "relation": "CEO_OF", "object": "Apple"}},
  {{"subject": "Apple", "relation": "FOUNDED_IN", "object": "1976"}}
]

Rules:
- Subject and Object must be specific entities (people, companies, places, dates)
- Relation must be a verb phrase in UPPERCASE_SNAKE_CASE
- Return only the JSON array, no other text"""
        
        try:
            response = requests.post(url, json={
                "model": "qwen2.5:0.5b",
                "prompt": prompt,
                "stream": False
            }, timeout=30)
            
            raw = response.json().get('response', '[]')
            # Extract JSON array from response
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    return []
        except Exception as e:
            print(f"[GraphRAG] Failed to call LLM for triple extraction: {e}")
            
        return []
    
    def store_triples(self, triples: list[dict], source_doc: str):
        """Store triples as Neo4j nodes and edges."""
        if not self.available or not self.driver:
            print("[Neo4j] Dry-run: Skip storing triples.")
            return
            
        try:
            with self.driver.session() as session:
                for triple in triples:
                    subject = triple.get('subject')
                    obj = triple.get('object')
                    if not subject or not obj:
                        continue  # Skip incomplete triples
                    # Sanitize relation to fit UPPERCASE_SNAKE_CASE
                    relation_type = re.sub(r'[^a-zA-Z0-9_]', '_', triple.get('relation', 'RELATED_TO')).upper()
                    if not relation_type:
                        relation_type = 'RELATED_TO'
                        
                    session.run(f"""
                        MERGE (s:Entity {{name: $subject}})
                        MERGE (o:Entity {{name: $object}})
                        MERGE (s)-[r:{relation_type} {{source: $source}}]->(o)
                    """, 
                    subject=subject,
                    object=obj,
                    source=source_doc
                    )
            print(f"[Neo4j] Stored {len(triples)} triples for doc: {source_doc}")
        except Exception as e:
            print(f"[Neo4j] Failed to store triples: {e}")
    
    def graph_search(self, start_entity: str, hops: int = 2) -> list[dict]:
        """
        Traverse from start_entity up to N hops, return all connected facts.
        Used to enrich RAG context with relational information.
        """
        if not self.available or not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                result = session.run(f"""
                    MATCH path = (start:Entity {{name: $name}})-[*1..{hops}]-(connected)
                    RETURN start.name, 
                           [r in relationships(path) | type(r)] AS relations,
                           [n in nodes(path) | n.name] AS entities
                    LIMIT 20
                """, name=start_entity)
                
                paths = []
                for record in result:
                    entities = record['entities']
                    relations = record['relations']
                    path_str = entities[0]
                    for i, rel in enumerate(relations):
                        path_str += f" --[{rel}]--> {entities[i+1]}"
                    paths.append({"path": path_str, "entities": entities})
                
                return paths
        except Exception as e:
            print(f"[Neo4j] Search error: {e}")
            return []
    
    def hybrid_rag_context(self, question: str, vector_chunks: list[str]) -> str:
        """
        Combine vector chunks with graph paths for richer LLM context.
        1. Extract key entities from question using capitalized words
        2. Traverse graph from those entities
        3. Append graph paths to vector context
        """
        # Simple entity extraction: capitalized words in question (ignoring start of sentence if it's common)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', question)
        
        graph_facts = []
        if self.available:
            for entity in entities[:3]:  # Limit to 3 entities
                paths = self.graph_search(entity, hops=2)
                graph_facts.extend([p['path'] for p in paths[:5]])
        
        # Build combined context
        vector_context = "\n\n".join(vector_chunks)
        graph_context = "\n".join(graph_facts) if graph_facts else "No graph facts found."
        
        return f"""DOCUMENT CONTEXT:
{vector_context}

KNOWLEDGE GRAPH FACTS:
{graph_context}"""
