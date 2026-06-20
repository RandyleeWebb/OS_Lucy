
"""Setup script for HyperGraphRAG v5 Demo"""

import asyncio
import logging
from typing import List, Dict, Any

from src.config import config
from src.database.graph_manager import GraphManager
from src.models.graph_entities import Document, NodeType
from src.processing.document_processor import DocumentProcessor
from src.art.art_engine import ARTEngine
from src.security.access_control import AccessController
from demo.demo_data import DEMO_DOCUMENTS, ART_TASK_LIBRARY, DEMO_USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_demo():
    """Setup the complete GraphRAG demo environment"""
    logger.info("Setting up HyperGraphRAG v5 Demo...")
    
    # Initialize components
    graph_manager = GraphManager()
    art_engine = ARTEngine(graph_manager)
    access_controller = AccessController()
    
    # Connect to database
    if not graph_manager.connect():
        logger.error("Failed to connect to database")
        return False
    
    # Initialize schema
    if not graph_manager.initialize_schema():
        logger.error("Failed to initialize schema")
        return False
    
    logger.info("Database connected and schema initialized")
    
    # Setup documents
    await setup_documents(graph_manager)
    
    # Setup ART task library
    setup_art_tasks(art_engine)
    
    # Setup demo users
    setup_demo_users(access_controller)
    
    logger.info("Demo setup completed successfully!")
    return True

async def setup_documents(graph_manager: GraphManager):
    """Process and store demo documents"""
    logger.info("Processing demo documents...")
    
    doc_processor = DocumentProcessor()
    
    for i, doc_data in enumerate(DEMO_DOCUMENTS):
        logger.info(f"Processing document {i+1}: {doc_data['name']}")
        
        # Create document node
        document = Document(
            name=doc_data["name"],
            content=doc_data["content"],
            tags=doc_data["tags"],
            access_level=doc_data["access_level"],
            source="demo_setup"
        )
        
        # Process document (chunking + entity extraction)
        chunks, entities = doc_processor.process_document(document)
        
        # Store document
        success = graph_manager.create_node(document)
        if not success:
            logger.error(f"Failed to store document: {doc_data['name']}")
            continue
        
        # Store chunks
        for chunk in chunks:
            graph_manager.create_node(chunk)
        
        # Store entities
        for entity in entities:
            graph_manager.create_node(entity)
        
        logger.info(f"  - Created {len(chunks)} chunks")
        logger.info(f"  - Extracted {len(entities)} entities")
    
    logger.info("All demo documents processed and stored")

def setup_art_tasks(art_engine: ARTEngine):
    """Setup ART task library with demo tasks"""
    logger.info("Setting up ART task library...")
    
    for task_def in ART_TASK_LIBRARY:
        art_engine.add_task_to_library(task_def)
        logger.info(f"  - Added task: {task_def['name']}")
    
    logger.info("ART task library setup completed")

def setup_demo_users(access_controller: AccessController):
    """Setup demo users with hashed passwords"""
    logger.info("Setting up demo users...")
    
    demo_users_with_hash = []
    
    for user in DEMO_USERS:
        hashed_password = access_controller.hash_password(user["password"])
        
        demo_user = {
            "username": user["username"],
            "password_hash": hashed_password,
            "access_level": user["access_level"],
            "role": user["role"]
        }
        
        demo_users_with_hash.append(demo_user)
        logger.info(f"  - Created user: {user['username']} (level {user['access_level']})")
    
    # In a real implementation, you'd store these in a database
    # For demo purposes, we'll just log them
    logger.info("Demo users created (passwords hashed)")
    logger.info("Demo login credentials:")
    
    for user in DEMO_USERS:
        logger.info(f"  Username: {user['username']}, Password: {user['password']}, Level: {user['access_level']}")

async def run_demo_queries(graph_manager: GraphManager):
    """Run demo queries to test the system"""
    logger.info("Running demo queries...")
    
    from demo.demo_data import DEMO_QUERIES
    from src.embeddings.embedding_service import EmbeddingService
    
    embedding_service = EmbeddingService()
    
    for i, query_data in enumerate(DEMO_QUERIES):
        logger.info(f"Query {i+1}: {query_data['query']}")
        
        try:
            # Generate query embedding
            query_vector = embedding_service.encode_text(query_data['query'])
            
            # Perform vector search
            results = graph_manager.vector_search(
                query_vector=query_vector,
                access_level=query_data.get('required_access_level', 0),
                limit=5
            )
            
            logger.info(f"  - Found {len(results)} results")
            for j, result in enumerate(results[:3]):
                logger.info(f"    {j+1}. Score: {result['score']:.3f}")
            
        except Exception as e:
            logger.error(f"  - Query failed: {e}")

def print_demo_info():
    """Print demo information and next steps"""
    print("\
" + "="*60)
    print("HYPERGRAPHRAG v5 DEMO SETUP COMPLETED")
    print("="*60)
    print("\
\ud83d\ude80 System Components:")
    print("  \u2705 Neo4j Graph Database with Vector Search")
    print("  \u2705 Semantic Embeddings (nomic-embed-text)")
    print("  \u2705 Document Processing & Entity Extraction")
    print("  \u2705 ART (Automatic Reasoning and Tool-use) Engine")
    print("  \u2705 Zero-Trust Security with Access Control")
    print("  \u2705 REST API with FastAPI")
    
    print("\
\ud83d\udcda Demo Documents Loaded:")
    for doc in DEMO_DOCUMENTS:
        level_str = f"(Level {doc['access_level']})"
        print(f"  - {doc['name']} {level_str}")
    
    print("\
\ud83d\udc65 Demo Users:")
    for user in DEMO_USERS:
        level_names = ["Public", "User", "Advanced", "Developer", "Admin", "AI Agent"]
        level_name = level_names[user['access_level']]
        print(f"  - {user['username']}: {user['password']} ({level_name})")
    
    print("\
\ud83d\udd27 To start the API server:")
    print("  cd /workspace")
    print("  python -m uvicorn src.api.graphrag_api:app --reload --host 0.0.0.0 --port 8000")
    
    print("\
\ud83d\udcd6 API Documentation:")
    print("  http://localhost:8000/docs")
    
    print("\
\ud83e\uddea Example API Usage:")
    print("  # Login as public user:")
    print("  curl -X POST 'http://localhost:8000/auth/login' \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"username\": \"public_user\", \"password\": \"public123\"}'")
    
    print("\
  # Semantic search:")
    print("  curl -X POST 'http://localhost:8000/search/semantic' \\")
    print("    -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"query\": \"What is GraphRAG?\"}'")
    
    print("\
  # Upload document:")
    print("  curl -X POST 'http://localhost:8000/documents/upload' \\")
    print("    -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"name\": \"My Document\", \"content\": \"Your content here\"}'")
    
    print("\
\ud83c\udfaf Demo Scenarios:")
    from demo.demo_data import DEMO_SCENARIOS
    for name, scenario in DEMO_SCENARIOS.items():
        print(f"  - {name}: {scenario['description']}")
    
    print("\
" + "="*60)
    print("\ud83c\udf89 Ready to explore HyperGraphRAG v5!")
    print("="*60)

if __name__ == "__main__":
    async def main():
        success = await setup_demo()
        if success:
            print_demo_info()
        else:
            print("Demo setup failed!")
    
    asyncio.run(main())
