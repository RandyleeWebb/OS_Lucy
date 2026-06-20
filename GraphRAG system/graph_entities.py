
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class NodeType(str, Enum):
    """Universal node types for GraphRAG"""
    PERSON = "PERSON"
    AGENT = "AGENT"
    DOCUMENT = "DOCUMENT"
    CHUNK = "CHUNK"
    CONCEPT = "CONCEPT"
    TASK = "TASK"
    GOAL = "GOAL"
    TOOL = "TOOL"
    CODE_FILE = "CODE_FILE"
    MEMORY_EPISODE = "MEMORY_EPISODE"
    OBSERVATION = "OBSERVATION"
    INSIGHT = "INSIGHT"
    PLAN = "PLAN"
    COMMAND = "COMMAND"
    SYSTEM_STATE = "SYSTEM_STATE"

class EdgeType(str, Enum):
    """Universal relationship types"""
    KNOWS = "KNOWS"
    CREATED_BY = "CREATED_BY"
    REFERENCES = "REFERENCES"
    CONTAINS = "CONTAINS"
    INSTANCE_OF = "INSTANCE_OF"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"
    USES_TOOL = "USES_TOOL"
    IMPLEMENTS = "IMPLEMENTS"
    SIMILAR_TO = "SIMILAR_TO"
    CAUSED = "CAUSED"
    CONTRADICTS = "CONTRADICTS"
    SUPPORTS = "SUPPORTS"
    EXECUTED = "EXECUTED"
    TRIGGERS = "TRIGGERS"

class GraphNode(BaseModel):
    """Universal Graph Node with all required properties"""
    id: UUID = Field(default_factory=uuid4)
    type: NodeType
    name: str
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: Optional[str] = None
    access_level: int = Field(default=0, ge=0, le=5)
    version: int = Field(default=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    """Universal Graph Edge with all required properties"""
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    type: EdgeType
    weight: float = Field(default=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Document(GraphNode):
    """Document node with additional properties"""
    type: NodeType = NodeType.DOCUMENT
    content: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None

class Chunk(GraphNode):
    """Text chunk node with additional properties"""
    type: NodeType = NodeType.CHUNK
    content: str
    document_id: UUID
    chunk_index: int
    start_char: int
    end_char: int

class Person(GraphNode):
    """Person node with additional properties"""
    type: NodeType = NodeType.PERSON
    email: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None

class Agent(GraphNode):
    """AI Agent node with additional properties"""
    type: NodeType = NodeType.AGENT
    capabilities: List[str] = Field(default_factory=list)
    model_name: Optional[str] = None
    status: str = Field(default="active")

class Concept(GraphNode):
    """Concept/Entity node with additional properties"""
    type: NodeType = NodeType.CONCEPT
    category: Optional[str] = None
    definition: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)

class Task(GraphNode):
    """Task node with additional properties"""
    type: NodeType = NodeType.TASK
    description: str
    status: str = Field(default="pending")
    priority: int = Field(default=1, ge=1, le=5)
    completed_at: Optional[datetime] = None

class Insight(GraphNode):
    """Insight node with additional properties"""
    type: NodeType = NodeType.INSIGHT
    insight_text: str
    confidence_score: float
    supporting_evidence: List[UUID] = Field(default_factory=list)
