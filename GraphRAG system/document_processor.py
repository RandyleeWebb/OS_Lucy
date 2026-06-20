
from typing import List, Dict, Any, Optional, Tuple
import re
import spacy
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag
from nltk.tree import Tree
import logging
from pathlib import Path
import uuid
from datetime import datetime

from ..config import config
from ..models.graph_entities import (
    Document, Chunk, Person, Concept, Task, GraphNode, NodeType
)
from ..embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Advanced Document Processing for GraphRAG"""
    
    def __init__(self):
        self.nlp = None
        self.embedding_service = EmbeddingService()
        self._load_nlp_models()
    
    def _load_nlp_models(self):
        """Load NLP models for entity extraction"""
        try:
            # Load spaCy model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model")
            
            # Download NLTK data if needed
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
            
            try:
                nltk.data.find('taggers/averaged_perceptron_tagger')
            except LookupError:
                nltk.download('averaged_perceptron_tagger')
            
            try:
                nltk.data.find('chunkers/maxent_ne_chunker')
            except LookupError:
                nltk.download('maxent_ne_chunker')
            
            try:
                nltk.data.find('corpora/words')
            except LookupError:
                nltk.download('words')
                
            logger.info("Loaded NLTK models")
        except Exception as e:
            logger.error(f"Failed to load NLP models: {e}")
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """Intelligent document chunking with overlap"""
        if not document.content:
            return []
        
        content = document.content
        chunks = []
        
        # Try sentence-based chunking first
        sentences = sent_tokenize(content)
        
        current_chunk = ""
        current_length = 0
        chunk_index = 0
        start_char = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_length + sentence_length > config.chunk_size and current_chunk:
                # Create chunk
                chunk = Chunk(
                    content=current_chunk.strip(),
                    document_id=document.id,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=start_char + current_length,
                    name=f"Chunk {chunk_index} of {document.name}",
                    source=str(document.id)
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + sentence + " "
                current_length = len(current_chunk)
                start_char += current_length - sentence_length
                chunk_index += 1
            else:
                current_chunk += sentence + " "
                current_length += sentence_length + 1
        
        # Add final chunk
        if current_chunk.strip():
            chunk = Chunk(
                content=current_chunk.strip(),
                document_id=document.id,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=start_char + current_length,
                name=f"Chunk {chunk_index} of {document.name}",
                source=str(document.id)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str, max_overlap: int = None) -> str:
        """Get overlapping text for chunk continuity"""
        if max_overlap is None:
            max_overlap = config.chunk_overlap
        
        words = text.split()
        if len(words) <= max_overlap:
            return text
        
        # Take last max_overlap words
        overlap_words = words[-max_overlap:]
        return " ".join(overlap_words) + " "
    
    def extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """Extract entities using multiple NLP approaches"""
        entities = {
            "persons": [],
            "organizations": [],
            "concepts": [],
            "locations": [],
            "tasks": []
        }
        
        # Method 1: spaCy NER
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                entity_data = {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 0.8  # spaCy doesn't provide confidence by default
                }
                
                if ent.label_ == "PERSON":
                    entities["persons"].append(entity_data)
                elif ent.label_ == "ORG":
                    entities["organizations"].append(entity_data)
                elif ent.label_ == "GPE":
                    entities["locations"].append(entity_data)
        
        # Method 2: NLTK NER for additional entities
        try:
            tokens = word_tokenize(text)
            pos_tags = pos_tag(tokens)
            tree = ne_chunk(pos_tags)
            
            for subtree in tree:
                if isinstance(subtree, Tree):
                    entity_text = " ".join([token for token, pos in subtree.leaves()])
                    entity_type = subtree.label()
                    
                    entity_data = {
                        "text": entity_text,
                        "label": entity_type,
                        "confidence": 0.7
                    }
                    
                    if entity_type == "PERSON":
                        # Avoid duplicates
                        if not any(e["text"].lower() == entity_text.lower() 
                                 for e in entities["persons"]):
                            entities["persons"].append(entity_data)
                    elif entity_type == "ORGANIZATION":
                        if not any(e["text"].lower() == entity_text.lower() 
                                 for e in entities["organizations"]):
                            entities["organizations"].append(entity_data)
        except Exception as e:
            logger.warning(f"NLTK NER failed: {e}")
        
        # Method 3: Extract concepts and tasks using patterns
        entities["concepts"].extend(self._extract_concepts(text))
        entities["tasks"].extend(self._extract_tasks(text))
        
        return entities
    
    def _extract_concepts(self, text: str) -> List[Dict]:
        """Extract technical concepts using patterns"""
        concepts = []
        
        # Technical concept patterns
        concept_patterns = [
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # CamelCase
            r'\b\w+\s+(?:algorithm|method|technique|approach|framework|model|system)\b',
            r'\b(?:machine learning|artificial intelligence|deep learning|neural network|natural language processing|computer vision)\b',
            r'\b(?:API|SDK|REST|GraphQL|SQL|NoSQL|JSON|XML|HTML|CSS|JavaScript|Python|Java|C\+\+)\b'
        ]
        
        for pattern in concept_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                concept_text = match.group().strip()
                if len(concept_text) > 2:  # Filter short matches
                    concepts.append({
                        "text": concept_text,
                        "confidence": 0.6,
                        "type": "technical"
                    })
        
        return concepts
    
    def _extract_tasks(self, text: str) -> List[Dict]:
        """Extract tasks using linguistic patterns"""
        tasks = []
        
        # Task patterns
        task_patterns = [
            r'\b(?:should|must|need to|have to|will|shall)\s+\w+\s+\w+',
            r'\b(?:implement|develop|create|build|design|analyze|test|deploy|configure)\s+\w+',
            r'\b(?:task|goal|objective|requirement|deliverable):\s*\w+'
        ]
        
        for pattern in task_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                task_text = match.group().strip()
                if len(task_text) > 5:
                    tasks.append({
                        "text": task_text,
                        "confidence": 0.5,
                        "type": "action"
                    })
        
        return tasks
    
    def create_graph_nodes(self, entities: Dict[str, List[Dict]], source_id: str = None) -> List[GraphNode]:
        """Convert extracted entities to graph nodes"""
        nodes = []
        
        # Create Person nodes
        for person_data in entities["persons"]:
            person = Person(
                name=person_data["text"],
                confidence=person_data["confidence"],
                source=source_id,
                metadata={"extraction_method": "spacy_nltk"}
            )
            nodes.append(person)
        
        # Create Concept nodes
        for concept_data in entities["concepts"]:
            concept = Concept(
                name=concept_data["text"],
                category=concept_data.get("type", "general"),
                confidence=concept_data["confidence"],
                source=source_id,
                metadata={"extraction_method": "pattern_matching"}
            )
            nodes.append(concept)
        
        # Create Task nodes
        for task_data in entities["tasks"]:
            task = Task(
                name=f"Task: {task_data['text'][:50]}...",
                description=task_data["text"],
                confidence=task_data["confidence"],
                source=source_id,
                metadata={"extraction_method": "pattern_matching"}
            )
            nodes.append(task)
        
        return nodes
    
    def process_document(self, document: Document) -> Tuple[List[Chunk], List[GraphNode]]:
        """Process document into chunks and entities"""
        logger.info(f"Processing document: {document.name}")
        
        # Step 1: Chunk the document
        chunks = self.chunk_document(document)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 2: Extract entities from each chunk
        all_entities = {"persons": [], "organizations": [], "concepts": [], "locations": [], "tasks": []}
        
        for chunk in chunks:
            entities = self.extract_entities(chunk.content)
            for entity_type in entities:
                all_entities[entity_type].extend(entities[entity_type])
        
        # Step 3: Deduplicate entities
        deduplicated_entities = self._deduplicate_entities(all_entities)
        
        # Step 4: Create graph nodes
        nodes = self.create_graph_nodes(deduplicated_entities, str(document.id))
        logger.info(f"Extracted {len(nodes)} entity nodes")
        
        # Step 5: Generate embeddings for chunks
        chunk_texts = [chunk.content for chunk in chunks]
        chunk_embeddings = self.embedding_service.encode_batch(chunk_texts)
        
        for chunk, embedding in zip(chunks, chunk_embeddings):
            chunk.embedding = embedding
        
        # Step 6: Generate embeddings for entity nodes
        node_texts = [node.name for node in nodes]
        node_embeddings = self.embedding_service.encode_batch(node_texts)
        
        for node, embedding in zip(nodes, node_embeddings):
            node.embedding = embedding
        
        return chunks, nodes
    
    def _deduplicate_entities(self, entities: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Remove duplicate entities based on text similarity"""
        deduplicated = {key: [] for key in entities}
        
        for entity_type, entity_list in entities.items():
            seen_texts = set()
            
            for entity in entity_list:
                text_lower = entity["text"].lower().strip()
                
                # Check for exact duplicates
                if text_lower in seen_texts:
                    continue
                
                # Check for similar entities (fuzzy matching)
                is_duplicate = False
                for seen_text in seen_texts:
                    if self._text_similarity(text_lower, seen_text) > 0.8:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    deduplicated[entity_type].append(entity)
                    seen_texts.add(text_lower)
        
        return deduplicated
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity for deduplication"""
        # Simple Jaccard similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
