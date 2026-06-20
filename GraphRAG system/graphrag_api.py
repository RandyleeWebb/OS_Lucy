
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json

from ..config import config
from ..database.graph_manager import GraphManager
from ..models.graph_entities import (
    GraphNode, GraphEdge, Document, Chunk, Person, Concept, Task, Insight,
    NodeType, EdgeType
)
from ..processing.document_processor import DocumentProcessor
from ..art.art_engine import ARTEngine
from ..security.access_control import AccessController, Permission
from ..embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="HyperGraphRAG v5 API",
    description="Advanced GraphRAG system with ART and zero-trust security",
    version="5.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
access_controller = AccessController()

# Global instances
graph_manager = GraphManager()
art_engine = ARTEngine(graph_manager)
doc_processor = DocumentProcessor()
embedding_service = EmbeddingService()

# Pydantic models for API
class DocumentUpload(BaseModel):
    name: str
    content: str
    mime_type: Optional[str] = "text/plain"
    tags: List[str] = Field(default_factory=list)
    access_level: int = Field(default=0, ge=0, le=5)

class QueryRequest(BaseModel):
    query: str
    node_type: Optional[NodeType] = None
    access_level: int = Field(default=0, ge=0, le=5)
    max_depth: int = Field(default=3, ge=1, le=5)
    limit: int = Field(default=10, ge=1, le=100)

class NodeCreate(BaseModel):
    type: NodeType
    name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    access_level: int = Field(default=0, ge=0, le=5)

class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    type: EdgeType
    weight: float = Field(default=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TaskExecution(BaseModel):
    task_name: str
    task_description: str
    query: str
    access_level: int = Field(default=0, ge=0, le=5)

# Dependency for authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = access_controller.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the GraphRAG system"""
    logger.info("Starting HyperGraphRAG v5 API...")
    
    # Connect to database
    if not graph_manager.connect():
        logger.error("Failed to connect to database")
        return
    
    # Initialize schema
    if not graph_manager.initialize_schema():
        logger.error("Failed to initialize database schema")
        return
    
    logger.info("HyperGraphRAG v5 API ready")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "5.0.0",
        "database": "connected" if graph_manager.driver else "disconnected"
    }

# Document endpoints
@app.post("/documents/upload")
async def upload_document(
    document: DocumentUpload,
    current_user: Dict = Depends(get_current_user)
):
    """Upload and process a new document"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Create document node
        doc_node = Document(
            name=document.name,
            content=document.content,
            mime_type=document.mime_type,
            size_bytes=len(document.content.encode()),
            tags=document.tags,
            access_level=document.access_level,
            source=current_user.get("user_id")
        )
        
        # Process document (chunking + entity extraction)
        chunks, entities = doc_processor.process_document(doc_node)
        
        # Store in graph
        success = graph_manager.create_node(doc_node)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store document")
        
        # Store chunks
        for chunk in chunks:
            graph_manager.create_node(chunk)
            # Create edge between document and chunk
            from ..models.graph_entities import GraphEdge
            edge = GraphEdge(
                source_id=doc_node.id,
                target_id=chunk.id,
                type=EdgeType.CONTAINS
            )
            graph_manager.create_edge(edge)
        
        # Store entities
        for entity in entities:
            graph_manager.create_node(entity)
            # Create edge between chunk and entity
            edge = GraphEdge(
                source_id=chunks[0].id,  # Link to first chunk
                target_id=entity.id,
                type=EdgeType.REFERENCES
            )
            graph_manager.create_edge(edge)
        
        # Audit access
        access_controller.audit_access(
            current_user.get("user_id"),
            "upload_document",
            str(doc_node.id),
            True
        )
        
        return {
            "document_id": str(doc_node.id),
            "chunks_created": len(chunks),
            "entities_extracted": len(entities),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get document by ID"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Query document from graph
        # This is a simplified implementation
        # In practice, you'd query the graph database
        
        return {"document_id": document_id, "status": "retrieved"}
        
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoints
@app.post("/search/semantic")
async def semantic_search(
    request: QueryRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Perform semantic search across the knowledge graph"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Perform semantic graph traversal
        results = graph_manager.semantic_graph_traversal(
            query=request.query,
            access_level=min(user_access_level, request.access_level),
            max_depth=request.max_depth
        )
        
        # Filter results based on access level
        filtered_results = []
        for result in results:
            # Extract nodes from path and filter
            # This is simplified - in practice, you'd filter each node
            filtered_results.append(result)
        
        return {
            "query": request.query,
            "results": filtered_results,
            "count": len(filtered_results)
        }
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/vector")
async def vector_search(
    request: QueryRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Perform vector similarity search"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Generate query embedding
        query_vector = embedding_service.encode_text(request.query)
        
        # Perform vector search
        results = graph_manager.vector_search(
            query_vector=query_vector,
            node_type=request.node_type,
            access_level=min(user_access_level, request.access_level),
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Node management endpoints
@app.post("/nodes")
async def create_node(
    node_data: NodeCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new graph node"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Check permissions
        if not access_controller.can_access_node(user_access_level, 
            GraphNode(type=node_data.type, name=node_data.name, access_level=node_data.access_level), 
            Permission.WRITE):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Create node based on type
        node = GraphNode(
            type=node_data.type,
            name=node_data.name,
            metadata=node_data.metadata,
            tags=node_data.tags,
            access_level=node_data.access_level,
            source=current_user.get("user_id")
        )
        
        # Generate embedding
        embedding = embedding_service.encode_text(node.name)
        node.embedding = embedding
        
        success = graph_manager.create_node(node)
        
        if success:
            return {"node_id": str(node.id), "status": "created"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create node")
            
    except Exception as e:
        logger.error(f"Node creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/edges")
async def create_edge(
    edge_data: EdgeCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new graph edge"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Create edge
        from uuid import UUID
        edge = GraphEdge(
            source_id=UUID(edge_data.source_id),
            target_id=UUID(edge_data.target_id),
            type=edge_data.type,
            weight=edge_data.weight,
            metadata=edge_data.metadata
        )
        
        success = graph_manager.create_edge(edge)
        
        if success:
            return {"edge_id": str(edge.id), "status": "created"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create edge")
            
    except Exception as e:
        logger.error(f"Edge creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ART endpoints
@app.post("/art/execute")
async def execute_art_task(
    task_request: TaskExecution,
    current_user: Dict = Depends(get_current_user)
):
    """Execute a task using ART methodology"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # Create task node
        task = Task(
            name=task_request.task_name,
            description=task_request.task_description,
            metadata={"required_capabilities": ["search", "analyze"]},
            access_level=task_request.access_level,
            source=current_user.get("user_id")
        )
        
        # Execute task using ART
        reasoning_steps = await art_engine.execute_task(
            task=task,
            query=task_request.query,
            access_level=min(user_access_level, task_request.access_level)
        )
        
        # Export reasoning trace
        trace = art_engine.export_reasoning_trace(reasoning_steps)
        
        return {
            "task_id": str(task.id),
            "status": "completed",
            "reasoning_trace": trace,
            "steps_executed": len(reasoning_steps)
        }
        
    except Exception as e:
        logger.error(f"ART task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/art/history")
async def get_art_history(
    task_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Get ART reasoning history"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        history = art_engine.get_reasoning_history(task_id)
        
        # Filter based on access level
        filtered_history = []
        for reasoning_steps in history:
            # Check if user can access this reasoning trace
            # This is simplified - in practice, you'd check each step
            filtered_history.append(reasoning_steps)
        
        return {
            "history": filtered_history,
            "count": len(filtered_history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get ART history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Authentication endpoints
@app.post("/auth/login")
async def login(username: str, password: str, access_level: int = 1):
    """Authenticate user and return access token"""
    try:
        # In practice, you'd validate against user database
        # This is a simplified implementation
        
        if username and password:
            # Create access token
            token_data = {
                "username": username,
                "access_level": access_level,
                "user_id": username  # Simplified
            }
            
            access_token = access_controller.create_access_token(token_data)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "access_level": access_level
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/auth/verify")
async def verify_token(current_user: Dict = Depends(get_current_user)):
    """Verify token and return user info"""
    return {
        "username": current_user.get("username"),
        "access_level": current_user.get("access_level"),
        "user_id": current_user.get("user_id")
    }

# Statistics endpoints
@app.get("/stats/overview")
async def get_system_stats(current_user: Dict = Depends(get_current_user)):
    """Get system overview statistics"""
    try:
        user_access_level = current_user.get("access_level", 0)
        
        # In practice, you'd query the graph database for real stats
        stats = {
            "total_nodes": 0,
            "total_edges": 0,
            "node_types": {},
            "edge_types": {},
            "access_distribution": {},
            "recent_activity": []
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
