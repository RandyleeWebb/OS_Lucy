
from typing import List, Dict, Any, Optional, Callable, Union
import json
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

from ..config import config
from ..database.graph_manager import GraphManager
from ..models.graph_entities import Task, Agent, GraphNode, NodeType, EdgeType

logger = logging.getLogger(__name__)

class StepType(Enum):
    """Types of reasoning steps in ART"""
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    OBSERVATION = "observation"
    SYNTHESIS = "synthesis"

@dataclass
class ReasoningStep:
    """Single reasoning step in ART"""
    id: str
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    result: Optional[Any] = None
    confidence: float = 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class Tool:
    """Base class for ART tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        """Execute the tool with given arguments"""
        raise NotImplementedError

class GraphQueryTool(Tool):
    """Tool for querying the graph database"""
    
    def __init__(self, graph_manager: GraphManager):
        super().__init__(
            name="graph_query",
            description="Query the GraphRAG knowledge graph for information"
        )
        self.graph_manager = graph_manager
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        """Execute graph query"""
        query = args.get("query", "")
        node_type = args.get("node_type")
        access_level = args.get("access_level", 0)
        max_depth = args.get("max_depth", 3)
        
        try:
            results = self.graph_manager.semantic_graph_traversal(
                query=query,
                access_level=access_level,
                max_depth=max_depth
            )
            return {"results": results, "count": len(results)}
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": str(e), "results": [], "count": 0}

class VectorSearchTool(Tool):
    """Tool for vector similarity search"""
    
    def __init__(self, graph_manager: GraphManager):
        super().__init__(
            name="vector_search",
            description="Search for similar content using vector embeddings"
        )
        self.graph_manager = graph_manager
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        """Execute vector search"""
        query = args.get("query", "")
        node_type = args.get("node_type")
        access_level = args.get("access_level", 0)
        limit = args.get("limit", 10)
        
        try:
            from ..embeddings.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            query_vector = embedding_service.encode_text(query)
            
            results = self.graph_manager.vector_search(
                query_vector=query_vector,
                node_type=node_type,
                access_level=access_level,
                limit=limit
            )
            return {"results": results, "count": len(results)}
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {"error": str(e), "results": [], "count": 0}

class EntityExtractionTool(Tool):
    """Tool for extracting entities from text"""
    
    def __init__(self):
        super().__init__(
            name="extract_entities",
            description="Extract entities (people, concepts, tasks) from text"
        )
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        """Extract entities from text"""
        text = args.get("text", "")
        
        try:
            from ..processing.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            entities = processor.extract_entities(text)
            return {"entities": entities, "text_length": len(text)}
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {"error": str(e), "entities": {}}

class InsightSynthesisTool(Tool):
    """Tool for synthesizing insights from multiple sources"""
    
    def __init__(self, graph_manager: GraphManager):
        super().__init__(
            name="synthesize_insights",
            description="Synthesize new insights from existing knowledge"
        )
        self.graph_manager = graph_manager
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        """Synthesize insights"""
        sources = args.get("sources", [])
        query = args.get("query", "")
        
        try:
            # This would typically use an LLM to synthesize insights
            # For now, we'll simulate with a simple combination
            insights = []
            
            for source in sources:
                insight = {
                    "source": source,
                    "insight": f"Derived insight from {source}",
                    "confidence": 0.7,
                    "timestamp": datetime.utcnow().isoformat()
                }
                insights.append(insight)
            
            return {"insights": insights, "synthesis_query": query}
        except Exception as e:
            logger.error(f"Insight synthesis failed: {e}")
            return {"error": str(e), "insights": []}

class ARTEngine:
    """Automatic Reasoning and Tool-use Engine"""
    
    def __init__(self, graph_manager: GraphManager):
        self.graph_manager = graph_manager
        self.tools: Dict[str, Tool] = {}
        self.task_library: List[Dict] = []
        self.reasoning_history: List[List[ReasoningStep]] = []
        self.max_reasoning_steps = config.max_reasoning_steps
        self.tool_timeout = config.tool_timeout_seconds
        
        # Initialize default tools
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize default ART tools"""
        self.register_tool(GraphQueryTool(self.graph_manager))
        self.register_tool(VectorSearchTool(self.graph_manager))
        self.register_tool(EntityExtractionTool())
        self.register_tool(InsightSynthesisTool(self.graph_manager))
    
    def register_tool(self, tool: Tool):
        """Register a new tool with the ART engine"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def add_task_to_library(self, task_definition: Dict):
        """Add a task definition to the task library"""
        self.task_library.append(task_definition)
        logger.info(f"Added task to library: {task_definition.get('name', 'unnamed')}")
    
    async def execute_task(self, task: Task, query: str, access_level: int = 0) -> List[ReasoningStep]:
        """Execute a task using ART methodology"""
        logger.info(f"Executing task: {task.name}")
        
        reasoning_steps = []
        current_context = {"query": query, "task": task.name, "access_level": access_level}
        
        # Step 1: Task decomposition
        decomposition_steps = await self._decompose_task(task, query, current_context)
        reasoning_steps.extend(decomposition_steps)
        
        # Step 2: Select demonstrations from task library
        demonstrations = self._select_demonstrations(task, query)
        
        # Step 3: Execute reasoning steps with tool use
        execution_steps = await self._execute_with_tools(task, query, demonstrations, current_context)
        reasoning_steps.extend(execution_steps)
        
        # Step 4: Synthesize final result
        synthesis_step = await self._synthesize_result(reasoning_steps, current_context)
        reasoning_steps.append(synthesis_step)
        
        # Store reasoning history
        self.reasoning_history.append(reasoning_steps)
        
        return reasoning_steps
    
    async def _decompose_task(self, task: Task, query: str, context: Dict) -> List[ReasoningStep]:
        """Decompose complex task into sub-tasks"""
        steps = []
        
        # Initial reasoning about the task
        initial_reasoning = ReasoningStep(
            id=str(uuid.uuid4()),
            step_type=StepType.REASONING,
            content=f"Analyzing task: {task.name}. Query: {query}. Breaking down into manageable steps.",
            confidence=0.9
        )
        steps.append(initial_reasoning)
        
        # Identify required tools based on task metadata
        required_capabilities = task.metadata.get("required_capabilities", [])
        
        for capability in required_capabilities:
            tool_selection = ReasoningStep(
                id=str(uuid.uuid4()),
                step_type=StepType.REASONING,
                content=f"Capability '{capability}' required. Selecting appropriate tools.",
                confidence=0.8
            )
            steps.append(tool_selection)
        
        return steps
    
    def _select_demonstrations(self, task: Task, query: str) -> List[Dict]:
        """Select relevant demonstrations from task library"""
        demonstrations = []
        
        # Simple similarity-based selection (in practice, would be more sophisticated)
        for lib_task in self.task_library:
            if self._task_similarity(task, lib_task) > 0.7:
                demonstrations.append(lib_task)
        
        return demonstrations[:3]  # Limit to top 3 demonstrations
    
    def _task_similarity(self, task1: Task, task2: Dict) -> float:
        """Compute similarity between task and library task"""
        # Simple keyword-based similarity
        task1_words = set(task1.name.lower().split() + task1.description.lower().split())
        task2_words = set(task2.get("name", "").lower().split() + task2.get("description", "").lower().split())
        
        intersection = len(task1_words.intersection(task2_words))
        union = len(task1_words.union(task2_words))
        
        return intersection / union if union > 0 else 0.0
    
    async def _execute_with_tools(self, 
                                 task: Task, 
                                 query: str, 
                                 demonstrations: List[Dict], 
                                 context: Dict) -> List[ReasoningStep]:
        """Execute reasoning steps with interleaved tool use"""
        steps = []
        
        # Plan execution based on demonstrations
        execution_plan = self._create_execution_plan(task, demonstrations)
        
        for plan_step in execution_plan:
            if plan_step["type"] == "tool_use":
                # Execute tool
                tool_name = plan_step["tool"]
                tool_args = plan_step["args"].copy()
                tool_args.update(context)
                
                tool_step = ReasoningStep(
                    id=str(uuid.uuid4()),
                    step_type=StepType.TOOL_USE,
                    content=f"Using tool '{tool_name}' with args: {tool_args}",
                    tool_name=tool_name,
                    tool_args=tool_args
                )
                steps.append(tool_step)
                
                # Execute tool with timeout
                try:
                    result = await asyncio.wait_for(
                        self.tools[tool_name].execute(tool_args),
                        timeout=self.tool_timeout
                    )
                    
                    observation_step = ReasoningStep(
                        id=str(uuid.uuid4()),
                        step_type=StepType.OBSERVATION,
                        content=f"Tool '{tool_name}' returned result: {json.dumps(result, default=str)[:200]}...",
                        result=result,
                        confidence=0.9
                    )
                    steps.append(observation_step)
                    
                except asyncio.TimeoutError:
                    error_step = ReasoningStep(
                        id=str(uuid.uuid4()),
                        step_type=StepType.OBSERVATION,
                        content=f"Tool '{tool_name}' timed out after {self.tool_timeout} seconds",
                        result={"error": "timeout"},
                        confidence=0.1
                    )
                    steps.append(error_step)
                
                except Exception as e:
                    error_step = ReasoningStep(
                        id=str(uuid.uuid4()),
                        step_type=StepType.OBSERVATION,
                        content=f"Tool '{tool_name}' failed: {str(e)}",
                        result={"error": str(e)},
                        confidence=0.1
                    )
                    steps.append(error_step)
            
            elif plan_step["type"] == "reasoning":
                # Add reasoning step
                reasoning_step = ReasoningStep(
                    id=str(uuid.uuid4()),
                    step_type=StepType.REASONING,
                    content=plan_step["content"],
                    confidence=plan_step.get("confidence", 0.8)
                )
                steps.append(reasoning_step)
        
        return steps
    
    def _create_execution_plan(self, task: Task, demonstrations: List[Dict]) -> List[Dict]:
        """Create execution plan based on task and demonstrations"""
        plan = []
        
        # Default plan for general queries
        if "search" in task.name.lower() or "find" in task.description.lower():
            plan.extend([
                {"type": "reasoning", "content": "Need to search for relevant information", "confidence": 0.9},
                {"type": "tool_use", "tool": "vector_search", "args": {"query": "", "limit": 10}},
                {"type": "tool_use", "tool": "graph_query", "args": {"query": "", "max_depth": 2}},
                {"type": "reasoning", "content": "Analyzing search results to find relevant information", "confidence": 0.8}
            ])
        
        elif "analyze" in task.name.lower():
            plan.extend([
                {"type": "reasoning", "content": "Need to analyze text and extract entities", "confidence": 0.9},
                {"type": "tool_use", "tool": "extract_entities", "args": {"text": ""}},
                {"type": "reasoning", "content": "Synthesizing insights from extracted entities", "confidence": 0.8},
                {"type": "tool_use", "tool": "synthesize_insights", "args": {"sources": []}}
            ])
        
        else:
            # Generic plan
            plan.extend([
                {"type": "reasoning", "content": "Breaking down the task into manageable steps", "confidence": 0.8},
                {"type": "tool_use", "tool": "graph_query", "args": {"query": ""}},
                {"type": "reasoning", "content": "Processing results and preparing response", "confidence": 0.8}
            ])
        
        return plan
    
    async def _synthesize_result(self, reasoning_steps: List[ReasoningStep], context: Dict) -> ReasoningStep:
        """Synthesize final result from all reasoning steps"""
        # Collect all observations
        observations = [step.result for step in reasoning_steps if step.step_type == StepType.OBSERVATION and step.result]
        
        synthesis_content = f"Completed task '{context['task']}' for query '{context['query']}'. "
        synthesis_content += f"Executed {len(reasoning_steps)} reasoning steps with {len(observations)} successful observations. "
        
        if observations:
            synthesis_content += "Key findings: " + "; ".join([str(obs)[:100] for obs in observations[:3]])
        
        return ReasoningStep(
            id=str(uuid.uuid4()),
            step_type=StepType.SYNTHESIS,
            content=synthesis_content,
            confidence=0.8
        )
    
    def get_reasoning_history(self, task_id: str = None) -> List[List[ReasoningStep]]:
        """Get reasoning history, optionally filtered by task"""
        if task_id:
            return [history for history in self.reasoning_history 
                   if any(step.content.startswith(f"Completed task '{task_id}'") for step in history)]
        return self.reasoning_history
    
    def export_reasoning_trace(self, reasoning_steps: List[ReasoningStep]) -> Dict:
        """Export reasoning steps as a structured trace"""
        return {
            "task_execution": {
                "steps": [
                    {
                        "id": step.id,
                        "type": step.step_type.value,
                        "content": step.content,
                        "tool_name": step.tool_name,
                        "tool_args": step.tool_args,
                        "result": step.result,
                        "confidence": step.confidence,
                        "timestamp": step.timestamp.isoformat()
                    }
                    for step in reasoning_steps
                ],
                "total_steps": len(reasoning_steps),
                "execution_time": (
                    reasoning_steps[-1].timestamp - reasoning_steps[0].timestamp
                ).total_seconds() if reasoning_steps else 0,
                "success_rate": len([s for s in reasoning_steps if s.confidence > 0.5]) / len(reasoning_steps) if reasoning_steps else 0
            }
        }
