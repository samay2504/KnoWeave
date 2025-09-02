"""
Embeddings utilities with fallback implementations
"""
import hashlib
from typing import List, Optional, Protocol
from dataclasses import dataclass

# Import numpy with fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Fallback numpy-like operations
    class MockNumpy:
        @staticmethod
        def array(data, dtype=float):
            return data
        
        @staticmethod
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))
        
        @staticmethod
        def linalg_norm(vector):
            return (sum(x * x for x in vector)) ** 0.5
    
    np = MockNumpy()


@dataclass
class EmbeddingResult:
    """Result from embedding generation"""
    embeddings: List[List[float]]
    dimension: int
    model_name: str


class EmbeddingsProvider(Protocol):
    """Protocol for embeddings providers"""
    
    def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for texts"""
        ...


class HashEmbeddingsProvider:
    """Hash-based embeddings provider (fallback)"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.model_name = "hash-fallback"
    
    def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate hash-based embeddings"""
        embeddings = []
        
        for text in texts:
            # Use hash for deterministic "embeddings"
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Convert hex to numbers and normalize
            numbers = [int(text_hash[i:i+2], 16) for i in range(0, min(len(text_hash), self.dimension//4*2), 2)]
            
            # Pad or truncate to desired dimension
            while len(numbers) < self.dimension:
                numbers.extend(numbers[:self.dimension-len(numbers)])
            numbers = numbers[:self.dimension]
            
            # Normalize to unit vector
            if NUMPY_AVAILABLE:
                vector = np.array(numbers, dtype=float)
                vector = vector / np.linalg.norm(vector)
                embeddings.append(vector.tolist())
            else:
                # Manual normalization without numpy
                norm = (sum(x * x for x in numbers)) ** 0.5
                if norm > 0:
                    normalized = [x / norm for x in numbers]
                else:
                    normalized = numbers
                embeddings.append(normalized)
        
        return EmbeddingResult(
            embeddings=embeddings,
            dimension=self.dimension,
            model_name=self.model_name
        )


def get_embeddings(texts, dimension=768):
    """
    Generate basic embeddings using hash-based approach (fallback)
    """
    provider = HashEmbeddingsProvider(dimension)
    result = provider.embed(texts)
    return result.embeddings


def cosine_similarity_score(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    if NUMPY_AVAILABLE:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
    else:
        # Manual calculation without numpy
        dot_product = sum(x * y for x, y in zip(embedding1, embedding2))
        norm1 = (sum(x * x for x in embedding1)) ** 0.5
        norm2 = (sum(x * x for x in embedding2)) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def create_embeddings_provider(model_name: Optional[str] = None) -> EmbeddingsProvider:
    """Create an embeddings provider"""
    # Try to use sentence-transformers if available
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        
        class SentenceTransformerProvider:
            def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
                self.model = SentenceTransformer(model_name)
                self.model_name = model_name
                self.dimension = self.model.get_sentence_embedding_dimension()
            
            def embed(self, texts: List[str]) -> EmbeddingResult:
                embeddings = self.model.encode(texts).tolist()
                return EmbeddingResult(
                    embeddings=embeddings,
                    dimension=self.dimension,
                    model_name=self.model_name
                )
        
        return SentenceTransformerProvider(model_name or 'all-MiniLM-L6-v2')
        
    except ImportError:
        # Fall back to hash-based embeddings
        return HashEmbeddingsProvider()

# Try to use sentence-transformers if available
try:
    from sentence_transformers import SentenceTransformer
    
    _model = None
    
    def get_embeddings_st(texts):
        global _model
        if _model is None:
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        return _model.encode(texts).tolist()
    
    # Use sentence-transformers if available
    get_embeddings = get_embeddings_st
    
except ImportError:
    # Keep the fallback implementation
    pass
