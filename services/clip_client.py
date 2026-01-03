"""
CLIP Client Service - OPTIMIZED FOR SPEED

Provides semantic embeddings for text and images using CLIP model.
Optimizations:
- Native PyTorch CLIP model (ViT-B/32) for speed
- CUDA acceleration when available
- Batch inference for images
- LRU cache for text embeddings
- Pickle-based persistent cache for image embeddings
- torch.no_grad() for inference
"""

import os
import hashlib
import pickle
import json
import time
from functools import lru_cache
from typing import Optional, Union, List, Dict
import numpy as np

# Global variables for lazy initialization
_clip_model = None
_clip_preprocess = None
_device = None
_clip_available = None

# Cache configuration
_image_cache_file = "clip_image_cache.pkl"
_image_embedding_cache: Dict[str, np.ndarray] = {}
CACHE_MAX_ENTRIES = 500  # Limit image cache size


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
        # Try importing PyTorch CLIP dependencies
        print("\n" + "="*70)
        print("🔧 CLIP DIAGNOSTIC - Checking dependencies...")
        print("="*70)
        
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"   → CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   → CUDA version: {torch.version.cuda}")
            print(f"   → GPU device: {torch.cuda.get_device_name(0)}")
        
        import clip
        print("✅ CLIP library imported successfully")
        
        # Check if model can be loaded
        print("\n🔄 Starting CLIP model initialization...")
        _init_clip_model()
        _clip_available = True
        print("\n✅ CLIP model available and ready")
        print("="*70 + "\n")
        return True
        
    except ImportError as e:
        print("\n❌ CLIP DIAGNOSTIC - Import Error")
        print("="*70)
        print(f"Error: {e}")
        print("\nRequired dependencies:")
        print("   → pip install torch torchvision")
        print("   → pip install ftfy regex tqdm")
        print("   → pip install git+https://github.com/openai/CLIP.git")
        print("="*70 + "\n")
        _clip_available = False
        return False
        
    except Exception as e:
        print("\n❌ CLIP DIAGNOSTIC - Initialization Failed")
        print("="*70)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        print("="*70 + "\n")
        _clip_available = False
        return False


def _init_clip_model():
    """
    Initialize CLIP model (lazy loading) with CUDA support.
    Uses native PyTorch CLIP for maximum speed.
    
    Model: ViT-B/32 (balanced performance/quality)
    - Fast inference (~30ms per image on GPU)
    - Good semantic understanding
    - ~350MB model size
    """
    global _clip_model, _clip_preprocess, _device
    
    if _clip_model is not None:
        print("⚡ CLIP model already loaded (using cached instance)")
        return _clip_model
    
    try:
        import torch
        import clip
        
        print("🔄 Loading CLIP model ViT-B/32...")
        print("   (First run may download ~350MB model file)")
        start_time = time.perf_counter()
        
        # Detect device (CUDA if available)
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"   → Target device: {_device.upper()}")
        
        # Load CLIP model
        _clip_model, _clip_preprocess = clip.load("ViT-B/32", device=_device)
        _clip_model.eval()  # Set to evaluation mode (disables dropout, etc.)
        
        load_time = time.perf_counter() - start_time
        
        print(f"\n✅ CLIP model loaded successfully!")
        print(f"   ⏱️  Load time: {load_time:.2f}s")
        print(f"   🧠 Model: ViT-B/32")
        print(f"   💻 Device: {_device.upper()}")
        print(f"   📊 Embedding dimension: 512")
        
        # Load image embedding cache from disk
        print("\n🗄️  Loading image embedding cache...")
        _load_image_cache()
        
        return _clip_model
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: Failed to load CLIP model")
        print(f"   Error: {e}")
        import traceback
        print("\n📋 Full traceback:")
        traceback.print_exc()
        raise


def _load_image_cache():
    """Load image embedding cache from disk (pickle file)."""
    global _image_embedding_cache
    
    try:
        if os.path.exists(_image_cache_file):
            with open(_image_cache_file, 'rb') as f:
                _image_embedding_cache = pickle.load(f)
            print(f"   → Loaded {len(_image_embedding_cache)} cached image embeddings")
    except Exception as e:
        print(f"   ⚠️ Failed to load image cache: {e}")
        _image_embedding_cache = {}


def _save_image_cache():
    """Save image embedding cache to disk (pickle file)."""
    try:
        with open(_image_cache_file, 'wb') as f:
            pickle.dump(_image_embedding_cache, f)
    except Exception as e:
        print(f"⚠️ Failed to save image cache: {e}")


@lru_cache(maxsize=128)
def get_text_embedding(text: str) -> Optional[np.ndarray]:
    """
    Get CLIP embedding for text with LRU caching.
    
    Uses @lru_cache decorator for automatic memory-efficient caching.
    Cache size: 128 entries (most recent queries).
    
    Args:
        text: Text to encode (slide title, content, etc.)
    
    Returns:
        numpy array of shape (512,) or None if CLIP unavailable
    
    Example:
        >>> emb = get_text_embedding("Market analysis and revenue growth")
        >>> emb.shape
        (512,)  # For ViT-B/32
    """
    if not text or not text.strip():
        return None
    
    # Check if CLIP is available
    if not is_clip_available():
        return None
    
    try:
        import torch
        import clip
        
        # Tokenize text
        text_tokens = clip.tokenize([text.strip()]).to(_device)
        
        # Get embedding with no gradient computation
        with torch.no_grad():
            text_features = _clip_model.encode_text(text_tokens)
            # Normalize for cosine similarity
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy
        embedding = text_features.cpu().numpy()[0]
        
        return embedding
        
    except Exception as e:
        print(f"⚠️ Error getting text embedding: {e}")
        return None


def get_image_embedding(image_url: str, use_cache: bool = True) -> Optional[np.ndarray]:
    """
    Get CLIP embedding for image with persistent caching.
    
    Downloads image from URL and encodes it.
    Uses pickle-based cache to avoid re-downloading and re-encoding.
    
    Args:
        image_url: URL of the image to encode
        use_cache: Whether to use cached embeddings (default: True)
    
    Returns:
        numpy array of shape (512,) or None if failed
    """
    if not is_clip_available():
        return None
    
    # Check cache first
    if use_cache and image_url in _image_embedding_cache:
        return _image_embedding_cache[image_url]
    
    try:
        import torch
        import requests
        from PIL import Image
        from io import BytesIO
        
        start_time = time.perf_counter()
        
        # Download image
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            return None
        
        # Open and preprocess image
        image = Image.open(BytesIO(response.content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Preprocess for CLIP
        image_input = _clip_preprocess(image).unsqueeze(0).to(_device)
        
        # Get embedding with no gradient computation
        with torch.no_grad():
            image_features = _clip_model.encode_image(image_input)
            # Normalize for cosine similarity
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy
        embedding = image_features.cpu().numpy()[0]
        
        # Cache the result
        if use_cache:
            _image_embedding_cache[image_url] = embedding
            
            # Limit cache size
            if len(_image_embedding_cache) > CACHE_MAX_ENTRIES:
                # Remove oldest entry
                oldest_url = next(iter(_image_embedding_cache))
                del _image_embedding_cache[oldest_url]
            
            # Save cache periodically (every 10 entries)
            if len(_image_embedding_cache) % 10 == 0:
                _save_image_cache()
        
        elapsed = time.perf_counter() - start_time
        print(f"   ⏱️  Image embedding: {elapsed*1000:.1f}ms")
        
        return embedding
        
    except Exception as e:
        print(f"⚠️ Error getting image embedding: {e}")
        return None


def get_image_embeddings_batch(image_urls: List[str], use_cache: bool = True) -> Dict[str, Optional[np.ndarray]]:
    """
    Get CLIP embeddings for multiple images in batch (OPTIMIZED).
    
    Uses batch processing with torch.stack for maximum speed.
    Falls back to cached embeddings when available.
    
    Args:
        image_urls: List of image URLs to encode
        use_cache: Whether to use cached embeddings (default: True)
    
    Returns:
        Dict mapping URL -> embedding (or None if failed)
    
    Performance:
        - Batch of 6 images: ~150-200ms on GPU, ~500ms on CPU
        - Individual: ~30-50ms per image on GPU, ~100ms on CPU
    """
    if not is_clip_available():
        return {url: None for url in image_urls}
    
    start_time = time.perf_counter()
    results = {}
    urls_to_process = []
    
    # Check cache first
    for url in image_urls:
        if use_cache and url in _image_embedding_cache:
            results[url] = _image_embedding_cache[url]
        else:
            urls_to_process.append(url)
    
    if not urls_to_process:
        print(f"   ✅ All {len(image_urls)} embeddings from cache")
        return results
    
    try:
        import torch
        import requests
        from PIL import Image
        from io import BytesIO
        
        # Download and preprocess all images
        images = []
        valid_urls = []
        
        for url in urls_to_process:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(_clip_preprocess(img))
                    valid_urls.append(url)
            except:
                results[url] = None
        
        if not images:
            return results
        
        # Batch process with torch.stack
        batch_input = torch.stack(images).to(_device)
        
        # Get embeddings for entire batch
        with torch.no_grad():
            batch_features = _clip_model.encode_image(batch_input)
            # Normalize for cosine similarity
            batch_features = batch_features / batch_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy and cache
        batch_embeddings = batch_features.cpu().numpy()
        
        for url, embedding in zip(valid_urls, batch_embeddings):
            results[url] = embedding
            if use_cache:
                _image_embedding_cache[url] = embedding
        
        # Save cache
        if use_cache:
            _save_image_cache()
        
        elapsed = time.perf_counter() - start_time
        print(f"   ⚡ Batch processed {len(valid_urls)} images in {elapsed*1000:.1f}ms ({elapsed*1000/len(valid_urls):.1f}ms/image)")
        
    except Exception as e:
        print(f"⚠️ Error in batch image embedding: {e}")
        for url in urls_to_process:
            if url not in results:
                results[url] = None
    
    return results


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
    """Clear the embedding caches (useful for testing or memory management)."""
    global _image_embedding_cache
    
    # Clear LRU cache for text embeddings
    get_text_embedding.cache_clear()
    
    # Clear image cache
    _image_embedding_cache.clear()
    _save_image_cache()
    
    print("🧹 CLIP embedding caches cleared")


def get_cache_stats() -> dict:
    """
    Get statistics about the embedding caches.
    
    Returns:
        dict with keys for text and image cache stats
    """
    text_cache_info = get_text_embedding.cache_info()
    
    return {
        'text_cache': {
            'hits': text_cache_info.hits,
            'misses': text_cache_info.misses,
            'size': text_cache_info.currsize,
            'max_size': text_cache_info.maxsize
        },
        'image_cache': {
            'size': len(_image_embedding_cache),
            'max_size': CACHE_MAX_ENTRIES,
            'sample_urls': list(_image_embedding_cache.keys())[:5]
        }
    }


# Pre-check on module import
if __name__ != "__main__":
    # Silently check availability on import (don't print if just importing)
    try:
        is_clip_available()
    except:
        pass
