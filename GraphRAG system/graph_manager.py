
from typing import List, Optional, Dict, Any, Union
from neo4j import GraphDatabase, Driver
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import logging
from datetime import datetime

from ..config import config
from ..models.graph_entities import GraphNode, GraphEdge, NodeType, EdgeType

logger = logging.getLogger(__name__)

class GraphManager:
    """Core Graph Database Manager for HyperGraphRAG v5"""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or config.neo4j_uri
        self.user = user or config.neo4j_user
        self.password = password or config.neo4j_password
        self.driver: Optional[Driver] = None
        self.embedding_model = None
        
    def connect(self) -> bool:
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def initialize_schema(self) -> bool:
        """Create the complete GraphRAG schema with constraints and indexes"""
        if not self.driver:
            raise ConnectionError("Database not connected")
        
        constraints_queries = [
            # Node constraints
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:PERSON) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (a:AGENT) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:DOCUMENT) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:CHUNK) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:CONCEPT) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:TASK) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT insight_id IF NOT EXISTS FOR (i:INSIGHT) REQUIRE i.id IS UNIQUE",
            
            # Access level constraint for security
            "CREATE CONSTRAINT node_access_level IF NOT EXISTS FOR (n) REQUIRE n.access_level IS NOT NULL"
        ]
        
        index_queries = [
            # Vector indexes for semantic search
            "CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS " +
            "FOR (c:CHUNK) ON (c.embedding) " +
            "OPTIONS {indexConfig: {dimension: 768, similarityFunction: 'cosine'}}",
            
            "CREATE VECTOR INDEX concept_embedding IF NOT EXISTS " +
            "FOR (c:CONCEPT) ON (c.embedding) " +
            "OPTIONS {indexConfig: {dimension: 768, similarityFunction: 'cosine'}}",
            
            "CREATE VECTOR INDEX person_embedding IF NOT EXISTS " +
            "FOR (p:PERSON) ON (p.embedding) " +
            "OPTIONS {indexConfig: {dimension: 768, similarityFunction: 'cosine'}}",
            
            # Full-text search indexes
            "CREATE FULLTEXT INDEX entity_name_index IF NOT EXISTS " +
            "FOR (n) ON EACH [n.name, n.content]",
            
            "CREATE FULLTEXT INDEX content_search_index IF NOT EXISTS " +
            "FOR (n:CHUNK, n:DOCUMENT, n:INSIGHT) ON EACH [n.content, n.insight_text]",
            
            # Performance indexes
            "CREATE INDEX node_type_index IF NOT EXISTS FOR (n) ON (n.type)",
            "CREATE INDEX node_access_level_index IF NOT EXISTS FOR (n) ON (n.access_level)",
            "CREATE INDEX created_at_index IF NOT EXISTS FOR (n) ON (n.created_at)",
            "CREATE INDEX updated_at_index IF NOT EXISTS FOR (n) ON (n.updated_at)",
            
            # Edge indexes
            "CREATE INDEX edge_type_index IF NOT EXISTS FOR ()-[r]-() ON (r.type)",
            "CREATE INDEX edge_weight_index IF NOT EXISTS FOR ()-[r]-() ON (r.weight)"
        ]
        
        try:
            with self.driver.session() as session:
                for query in constraints_queries + index_queries:
                    session.run(query)
            logger.info("Schema initialization completed successfully")
            return True
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            return False
    
    def create_node(self, node: GraphNode) -> bool:
        """Create a new node in the graph"""
        if not self.driver:
            raise ConnectionError("Database not connected")
        
        cypher_query = """
        CREATE (n:$label)
        SET n.id = $id,
            n.type = $type,
            n.name = $name,
            n.embedding = $embedding,
            n.created_at = $created_at,
            n.updated_at = $updated_at,
            n.tags = $tags,
            n.confidence = $confidence,
            n.source = $source,
            n.access_level = $access_level,
            n.version = $version,
            n.metadata = $metadata
        RETURN n
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    cypher_query,
                    label=node.type.value,
                    id=str(node.id),
                    type=node.type.value,
                    name=node.name,
                    embedding=node.embedding,
                    created_at=node.created_at.isoformat(),
                    updated_at=node.updated_at.isoformat(),
                    tags=node.tags,
                    confidence=node.confidence,
                    source=node.source,
                    access_level=node.access_level,
                    version=node.version,
                    metadata=json.dumps(node.metadata)
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            return False
    
    def create_edge(self, edge: GraphEdge) -> bool:
        """Create a new edge (relationship) in the graph"""
        if not self.driver:
            raise ConnectionError("Database not connected")
        
        cypher_query = """
        MATCH (a), (b)
        WHERE a.id = $source_id AND b.id = $target_id
        CREATE (a)-[r:$edge_type]->(b)
        SET r.id = $edge_id,
            r.weight = $weight,
            r.confidence = $confidence,
            r.created_at = $created_at,
            r.metadata = $metadata
        RETURN r
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    cypher_query,
                    source_id=str(edge.source_id),
                    target_id=str(edge.target_id),
                    edge_type=edge.type.value,
                    edge_id=str(edge.id),
                    weight=edge.weight,
                    confidence=edge.confidence,
                    created_at=edge.created_at.isoformat(),
                    metadata=json.dumps(edge.metadata)
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to create edge: {e}")
            return False
    
    def vector_search(self, 
                     query_vector: List[float], 
                     node_type: Optional[NodeType] = None,
                     access_level: int = 0,
                     limit: int = 10) -> List[Dict]:
        """Perform vector similarity search"""
        if not self.driver:
            raise ConnectionError("Database not connected")
        
        base_query = """
        CALL db.index.vector.queryNodes($index_name, $limit, $query_vector)
        YIELD node, score
        WHERE node.access_level <= $access_level
        """
        
        if node_type:
            base_query += " AND node.type = $node_type"
        
        base_query += " RETURN node, score ORDER BY score DESC"
        
        index_name = f"{node_type.value.lower()}_embedding" if node_type else "chunk_embedding"
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    base_query,
                    index_name=index_name,
                    limit=limit,
                    query_vector=query_vector,
                    access_level=access_level,
                    node_type=node_type.value if node_type else None
                )
                return [{"node": record["node"], "score": record["score"]} 
                       for record in result]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def semantic_graph_traversal(self, 
                               query: str, 
                               access_level: int = 0,
                               max_depth: int = 3) -> List[Dict]:
        """Perform semantic graph traversal for complex queries"""
        if not self.embedding_model:
            self.embedding_model = SentenceTransformer(config.embedding_model)
        
        # Generate query embedding
        query_vector = self.embedding_model.encode(query).tolist()
        
        # First find relevant chunks via vector search
        relevant_chunks = self.vector_search(
            query_vector, 
            NodeType.CHUNK, 
            access_level, 
            limit=5
        )
        
        if not relevant_chunks:
            return []
        
        # Traverse graph from relevant chunks
        traversal_query = """
        UNWIND $chunk_ids AS chunk_id
        MATCH (chunk:CHUNK {id: chunk_id})
        CALL apoc.path.expandConfig(chunk, {
            relationshipFilter: "CONTAINS|REFERENCES|SIMILAR_TO|SUPPORTS",
            maxDepth: $max_depth,
            bfs: true,
            filterStartNode: false,
            filterEndNode: false,
            uniqueness: "NODE_GLOBAL"
        })
        YIELD path
        RETURN path, length(path) as depth
        ORDER BY depth ASC
        LIMIT 100
        """
        
        chunk_ids = [chunk["node"]["id"] for chunk in relevant_chunks]
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    traversal_query,
                    chunk_ids=chunk_ids,
                    max_depth=max_depth
                )
                return [{"path": record["path"], "depth": record["depth"]} 
                       for record in result]
        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Database connection closed")
