
"""Demo data and scenarios for HyperGraphRAG v5"""

from datetime import datetime
from uuid import uuid4

# Sample documents for demonstration
DEMO_DOCUMENTS = [
    {
        "name": "AI Research Paper - GraphRAG Systems",
        "content": """
        GraphRAG: Combining Knowledge Graphs with Retrieval-Augmented Generation
        
        Abstract:
        This paper presents GraphRAG, a novel approach that combines knowledge graphs with 
        retrieval-augmented generation to improve the accuracy and relevance of language model outputs.
        
        Introduction:
        Traditional RAG systems rely on vector similarity search alone, which can miss important 
        contextual relationships. By integrating knowledge graphs, we can capture structured 
        relationships between entities and enable more sophisticated reasoning.
        
        Methodology:
        Our approach involves three main components: (1) Entity extraction and relationship 
        identification, (2) Knowledge graph construction, and (3) Graph-enhanced retrieval 
        combined with LLM generation. We use Neo4j for graph storage and nomic-embed-text 
        for semantic embeddings.
        
        Results:
        Experiments show that GraphRAG improves factual accuracy by 23% compared to vanilla RAG 
        systems, particularly on complex reasoning tasks that require understanding entity relationships.
        
        Conclusion:
        GraphRAG represents a significant advancement in retrieval-augmented generation, 
        enabling more accurate and contextually aware AI responses.
        """,
        "tags": ["AI", "GraphRAG", "Research", "Neo4j"],
        "access_level": 0
    },
    {
        "name": "Technical Guide - Neo4j Vector Search",
        "content": """
        Neo4j Vector Search Implementation Guide
        
        Overview:
        Neo4j 5.24+ introduces native vector search capabilities that enable semantic similarity 
        search directly within the graph database. This eliminates the need for separate vector stores.
        
        Setup:
        1. Install Neo4j 5.24 or later
        2. Enable the vector plugin in neo4j.conf
        3. Create vector indexes using Cypher
        
        Example Vector Index Creation:
        CREATE VECTOR INDEX chunk_embedding 
        FOR (c:Chunk) ON (c.embedding) 
        OPTIONS {indexConfig: {dimension: 768, similarityFunction: 'cosine'}}
        
        Querying:
        Use db.index.vector.queryNodes() for similarity search:
        
        CALL db.index.vector.queryNodes('chunk_embedding', 10, query_vector)
        YIELD node, score
        RETURN node.content, score
        
        Best Practices:
        - Use 768-dimensional embeddings for good balance of quality and performance
        - Normalize embeddings before storing
        - Combine vector search with graph traversal for optimal results
        - Implement proper access control using node properties
        """,
        "tags": ["Neo4j", "Vector Search", "Technical", "Database"],
        "access_level": 1
    },
    {
        "name": "Security Architecture - Zero Trust GraphRAG",
        "content": """
        Zero Trust Security Model for GraphRAG Systems
        
        Overview:
        Implementing zero-trust architecture in GraphRAG systems requires multi-layered security 
        controls at the node, edge, and query levels. Each component must verify access independently.
        
        Access Levels (0-5):
        Level 0: Public access - Basic entities and concepts
        Level 1: User access - Personal data and documents
        Level 2: Advanced user - Code files and development resources
        Level 3: Developer - System internals and debugging tools
        Level 4: Admin - User management and system configuration
        Level 5: AI Agent - Full system access with monitoring
        
        Implementation:
        1. Node-level access control using access_level property
        2. Mandatory Access Control (MAC) for cross-level access
        3. JWT-based authentication with role-based permissions
        4. Audit logging for all access attempts
        5. Encryption for sensitive data at rest
        
        Query Filtering:
        All queries must be filtered by user access level:
        MATCH (n) WHERE n.access_level <= $user_level RETURN n
        
        This ensures users can only access data within their clearance level.
        """,
        "tags": ["Security", "Zero Trust", "Architecture", "Access Control"],
        "access_level": 3
    }
]

# Sample queries for testing
DEMO_QUERIES = [
    {
        "query": "What is GraphRAG and how does it improve AI accuracy?",
        "description": "Basic query about GraphRAG concept",
        "expected_results": ["AI Research Paper", "technical concepts"]
    },
    {
        "query": "How do I implement vector search in Neo4j?",
        "description": "Technical implementation query",
        "expected_results": ["Neo4j Vector Search", "setup instructions"]
    },
    {
        "query": "What security measures are implemented in this system?",
        "description": "Security and access control query",
        "expected_results": ["Zero Trust model", "access levels"],
        "required_access_level": 2
    },
    {
        "query": "Who developed the GraphRAG methodology and what were their key findings?",
        "description": "Complex query requiring entity relationship traversal",
        "expected_results": ["Research paper authors", "23% improvement metric"]
    }
]

# Sample ART task definitions
ART_TASK_LIBRARY = [
    {
        "name": "semantic_search",
        "description": "Perform semantic search across knowledge graph",
        "required_capabilities": ["vector_search", "graph_traversal"],
        "demonstration": """
        1. Generate query embedding
        2. Perform vector similarity search
        3. Traverse related nodes
        4. Synthesize results
        """
    },
    {
        "name": "entity_analysis",
        "description": "Analyze entities and their relationships",
        "required_capabilities": ["entity_extraction", "relationship_mapping"],
        "demonstration": """
        1. Extract entities from text
        2. Map entity relationships
        3. Identify key patterns
        4. Generate insights
        """
    },
    {
        "name": "knowledge_synthesis",
        "description": "Synthesize new knowledge from existing information",
        "required_capabilities": ["pattern_recognition", "insight_generation"],
        "demonstration": """
        1. Identify related concepts
        2. Find common patterns
        3. Generate new insights
        4. Create knowledge connections
        """
    }
]

# Sample users for demo
DEMO_USERS = [
    {
        "username": "public_user",
        "password": "public123",
        "access_level": 0,
        "role": "public"
    },
    {
        "username": "john_developer",
        "password": "dev123",
        "access_level": 2,
        "role": "advanced_user"
    },
    {
        "username": "admin",
        "password": "admin123",
        "access_level": 4,
        "role": "admin"
    },
    {
        "username": "lucy_agent",
        "password": "ai123",
        "access_level": 5,
        "role": "ai_agent"
    }
]

# Demo scenarios
DEMO_SCENARIOS = {
    "basic_research": {
        "description": "Basic user searching for AI research",
        "user": "public_user",
        "query": "GraphRAG research findings",
        "expected_behavior": "Access to public research papers only"
    },
    "technical_implementation": {
        "description": "Developer looking for implementation guides",
        "user": "john_developer",
        "query": "Neo4j vector search setup",
        "expected_behavior": "Access to technical documentation and code examples"
    },
    "security_admin": {
        "description": "Admin checking security architecture",
        "user": "admin",
        "query": "System security measures and access control",
        "expected_behavior": "Full access to security documentation and system internals"
    },
    "ai_reasoning": {
        "description": "AI agent performing complex analysis",
        "user": "lucy_agent",
        "query": "Analyze the relationship between GraphRAG performance and entity richness",
        "expected_behavior": "Complex reasoning with tool use and insight synthesis"
    }
}
