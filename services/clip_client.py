"""
CLIP Client Service

Provides semantic embeddings for text and images using CLIP model.
Uses lazy initialization to load the model only once per process.

Features:
- Text-to-embedding conversion
- Image-to-embedding conversion (optional)
- In-memory caching for text embeddings
- Graceful fallback if CLIP unavailable
"""

import os
import hashlib
from typing import Optional, Union, List
import numpy as np

# Global variables for lazy initialization
_clip_model = None
_clip_available = None
_embedding_cache = {}
_cache_max_size = 1000  # Limit cache to prevent memory bloat


def is_clip_available() -> bool:
    """
    Check if CLIP model is available and can be loaded.
    
    Returns:
        bool: True if CLIP can be initialized, False otherwise
    """
    global _clip_available
    
    if _clip_available is not None:
        return _clip_available
    
    try:
        # Try importing dependencies
        import torch
        from sentence_transformers import SentenceTransformer
        
        # Check if model can be loaded
        _init_clip_model()
        _clip_available = True
        print("✅ CLIP model available and initialized")
        return True
        
    except ImportError as e:
        print(f"⚠️ CLIP dependencies not installed: {e}")
        print("   → Install with: pip install torch sentence-transformers")
        _clip_available = False
        return False
        
    except Exception as e:
        print(f"⚠️ CLIP model initialization failed: {e}")
        _clip_available = False
        return False


def _init_clip_model():
    """
    Initialize CLIP model (lazy loading).
    Uses sentence-transformers with CLIP model for simplicity.
    
    Model: clip-ViT-B-32 (balanced performance/quality)
    - Fast inference
    - Good multilingual support
    - ~600MB model size
    """
    global _clip_model
    
    if _clip_model is not None:
        return _clip_model
    
    try:
        from sentence_transformers import SentenceTransformer
        
        print("🔄 Loading CLIP model (this may take a minute on first run)...")
        
        # Use CLIP model via sentence-transformers
        # clip-ViT-B-32: Good balance of speed and quality
        _clip_model = SentenceTransformer('clip-ViT-B-32')
        
        print("✅ CLIP model loaded successfully")
        print(f"   → Model: clip-ViT-B-32")
        print(f"   → Embedding dimension: {_clip_model.get_sentence_embedding_dimension()}")
        
        return _clip_model
        
    except Exception as e:
        print(f"❌ Failed to load CLIP model: {e}")
        raise


def get_text_embedding(text: str, use_cache: bool = True) -> Optional[np.ndarray]:
    """
    Get CLIP embedding for text.
    
    Args:
        text: Text to encode (slide title, content, etc.)
        use_cache: Whether to use cached embeddings (default: True)
    
    Returns:
        numpy array of shape (embedding_dim,) or None if CLIP unavailable
    
    Example:
        >>> emb = get_text_embedding("Market analysis and revenue growth")
        >>> emb.shape
        (512,)  # For clip-ViT-B-32
    """
    if not text or not text.strip():
        return None
    
    # Check if CLIP is available
    if not is_clip_available():
        return None
    
    # Normalize text
    text = text.strip()
    
    # Check cache first
    if use_cache:
        cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
        if cache_key in _embedding_cache:
            return _embedding_cache[cache_key]
    
    try:
        # Get embedding from CLIP model
        embedding = _clip_model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        
        # Cache the result
        if use_cache:
            # Limit cache size to prevent memory issues
            if len(_embedding_cache) >= _cache_max_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(_embedding_cache))
                del _embedding_cache[oldest_key]
            
            _embedding_cache[cache_key] = embedding
        
        return embedding
        
    except Exception as e:
        print(f"⚠️ Error getting text embedding: {e}")
        return None


def get_image_embedding(image_url: str) -> Optional[np.ndarray]:
    """
    Get CLIP embedding for image (optional feature).
    
    Downloads image from URL and encodes it.
    Note: This is more resource-intensive than text embeddings.
    
    Args:
        image_url: URL of the image to encode
    
    Returns:
        numpy array of shape (embedding_dim,) or None if failed
    """
    if not is_clip_available():
        return None
    
    try:
        import requests
        from PIL import Image
        from io import BytesIO
        
        # Download image
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            return None
        
        # Open image
        image = Image.open(BytesIO(response.content))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Get embedding
        embedding = _clip_model.encode(
            image,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        return embedding
        
    except Exception as e:
        print(f"⚠️ Error getting image embedding: {e}")
        return None


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.
    
    Since embeddings are L2-normalized, cosine similarity = dot product.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
    
    Returns:
        float: Similarity score in range [0, 1] (higher = more similar)
    """
    try:
        # Embeddings are already normalized, so dot product = cosine similarity
        similarity = float(np.dot(embedding1, embedding2))
        
        # Clamp to [0, 1] range (sometimes numerical errors can give values slightly outside)
        similarity = max(0.0, min(1.0, similarity))
        
        return similarity
        
    except Exception as e:
        print(f"⚠️ Error computing similarity: {e}")
        return 0.0


def clear_cache():
    """Clear the embedding cache (useful for testing or memory management)."""
    global _embedding_cache
    _embedding_cache.clear()
    print("🧹 CLIP embedding cache cleared")


def get_cache_stats() -> dict:
    """
    Get statistics about the embedding cache.
    
    Returns:
        dict with keys: 'size', 'max_size', 'hit_rate'
    """
    return {
        'size': len(_embedding_cache),
        'max_size': _cache_max_size,
        'items': list(_embedding_cache.keys())[:10]  # First 10 keys for debugging
    }


# Pre-check on module import
if __name__ != "__main__":
    # Silently check availability on import (don't print if just importing)
    try:
        is_clip_available()
    except:
        pass
