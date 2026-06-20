
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import logging
from pathlib import Path
import json

from ..config import config

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Advanced Embedding Service for GraphRAG"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.embedding_model
        self.dimension = config.embedding_dimension
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Loaded embedding model: {self.model_name} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            # Fallback to a smaller model
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2', device=self.device)
                logger.info("Fallback to all-MiniLM-L6-v2 model")
            except Exception as fallback_error:
                logger.error(f"Fallback model failed: {fallback_error}")
                raise
    
    def encode_text(self, text: str, normalize: bool = True) -> List[float]:
        """Encode single text to embedding vector"""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return [0.0] * self.dimension
    
    def encode_batch(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """Encode multiple texts to embedding vectors"""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                show_progress_bar=True,
                batch_size=32
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to encode batch: {e}")
            return [[0.0] * self.dimension] * len(texts)
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        try:
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            # Handle zero vectors
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(emb1, emb2) / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def find_similar_texts(self, 
                          query_embedding: List[float], 
                          candidate_embeddings: List[List[float]], 
                          threshold: float = 0.7) -> List[int]:
        """Find indices of similar texts based on embedding similarity"""
        try:
            similarities = []
            for i, candidate_emb in enumerate(candidate_embeddings):
                sim = self.compute_similarity(query_embedding, candidate_emb)
                if sim >= threshold:
                    similarities.append((i, sim))
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [idx for idx, _ in similarities]
        except Exception as e:
            logger.error(f"Failed to find similar texts: {e}")
            return []
    
    def chunk_embeddings(self, chunks: List[str], chunk_size: int = 32) -> List[List[float]]:
        """Generate embeddings for text chunks in batches"""
        all_embeddings = []
        
        for i in range(0, len(chunks), chunk_size):
            batch = chunks[i:i + chunk_size]
            batch_embeddings = self.encode_batch(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def semantic_search(self, 
                       query: str, 
                       corpus: List[str], 
                       top_k: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search on text corpus"""
        try:
            # Encode query
            query_embedding = self.encode_text(query)
            
            # Encode corpus (if not already embedded)
            corpus_embeddings = self.encode_batch(corpus)
            
            # Compute similarities
            similarities = []
            for i, (text, embedding) in enumerate(zip(corpus, corpus_embeddings)):
                sim = self.compute_similarity(query_embedding, embedding)
                similarities.append({
                    "index": i,
                    "text": text,
                    "similarity": sim
                })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:top_k]
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def save_embeddings(self, embeddings: List[List[float]], filepath: str):
        """Save embeddings to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(embeddings, f)
            logger.info(f"Saved {len(embeddings)} embeddings to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
    
    def load_embeddings(self, filepath: str) -> List[List[float]]:
        """Load embeddings from file"""
        try:
            with open(filepath, 'r') as f:
                embeddings = json.load(f)
            logger.info(f"Loaded {len(embeddings)} embeddings from {filepath}")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return []
