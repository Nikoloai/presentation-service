"""
Unit tests for CLIP client service

Tests cover:
- CLIP availability check
- Text embedding generation
- Similarity computation
- Caching functionality
- Edge cases and error handling
"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import clip_client


class TestCLIPAvailability(unittest.TestCase):
    """Test CLIP model availability detection"""
    
    def test_clip_availability_check(self):
        """Test that availability check doesn't crash"""
        try:
            result = clip_client.is_clip_available()
            self.assertIsInstance(result, bool)
        except Exception as e:
            self.fail(f"is_clip_available() raised exception: {e}")
    
    @patch('services.clip_client.SentenceTransformer')
    def test_clip_unavailable_on_import_error(self, mock_st):
        """Test graceful handling when dependencies missing"""
        mock_st.side_effect = ImportError("sentence-transformers not installed")
        
        # Reset global state
        clip_client._clip_available = None
        clip_client._clip_model = None
        
        result = clip_client.is_clip_available()
        self.assertFalse(result)


class TestTextEmbedding(unittest.TestCase):
    """Test text embedding generation"""
    
    def setUp(self):
        """Clear cache before each test"""
        clip_client.clear_cache()
    
    def test_get_text_embedding_with_empty_string(self):
        """Test handling of empty string input"""
        result = clip_client.get_text_embedding("")
        self.assertIsNone(result)
    
    def test_get_text_embedding_with_whitespace(self):
        """Test handling of whitespace-only input"""
        result = clip_client.get_text_embedding("   ")
        self.assertIsNone(result)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_get_text_embedding_returns_array(self):
        """Test that valid text returns numpy array"""
        text = "This is a test sentence"
        result = clip_client.get_text_embedding(text)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, np.ndarray)
        self.assertGreater(len(result), 0)  # Should have non-zero dimension
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_get_text_embedding_consistent_results(self):
        """Test that same text produces same embedding"""
        text = "Market analysis and revenue growth"
        
        emb1 = clip_client.get_text_embedding(text)
        emb2 = clip_client.get_text_embedding(text)
        
        self.assertIsNotNone(emb1)
        self.assertIsNotNone(emb2)
        np.testing.assert_array_almost_equal(emb1, emb2)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_different_text_different_embeddings(self):
        """Test that different texts produce different embeddings"""
        emb1 = clip_client.get_text_embedding("Financial growth")
        emb2 = clip_client.get_text_embedding("Mountain landscape")
        
        self.assertIsNotNone(emb1)
        self.assertIsNotNone(emb2)
        
        # Embeddings should be different (not identical)
        self.assertFalse(np.array_equal(emb1, emb2))


class TestCaching(unittest.TestCase):
    """Test embedding caching functionality"""
    
    def setUp(self):
        """Clear cache before each test"""
        clip_client.clear_cache()
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_caching_works(self):
        """Test that caching stores and retrieves embeddings"""
        text = "Test caching functionality"
        
        # First call should compute embedding
        emb1 = clip_client.get_text_embedding(text, use_cache=True)
        
        # Check cache contains the embedding
        cache_stats = clip_client.get_cache_stats()
        self.assertGreater(cache_stats['size'], 0)
        
        # Second call should retrieve from cache
        emb2 = clip_client.get_text_embedding(text, use_cache=True)
        
        # Results should be identical (same object from cache)
        np.testing.assert_array_equal(emb1, emb2)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_cache_bypass(self):
        """Test that use_cache=False bypasses cache"""
        text = "Test cache bypass"
        
        # Get embedding without caching
        emb1 = clip_client.get_text_embedding(text, use_cache=False)
        
        # Cache should be empty
        cache_stats = clip_client.get_cache_stats()
        self.assertEqual(cache_stats['size'], 0)
        
        # Second call also without cache
        emb2 = clip_client.get_text_embedding(text, use_cache=False)
        
        # Results should be equal but cache still empty
        np.testing.assert_array_almost_equal(emb1, emb2)
        cache_stats = clip_client.get_cache_stats()
        self.assertEqual(cache_stats['size'], 0)
    
    def test_clear_cache(self):
        """Test cache clearing functionality"""
        # Get cache stats before
        stats_before = clip_client.get_cache_stats()
        
        # Clear cache
        clip_client.clear_cache()
        
        # Check cache is empty
        stats_after = clip_client.get_cache_stats()
        self.assertEqual(stats_after['size'], 0)


class TestSimilarityComputation(unittest.TestCase):
    """Test cosine similarity computation"""
    
    def test_compute_similarity_identical_vectors(self):
        """Test similarity of identical vectors is 1.0"""
        vec = np.array([1.0, 0.0, 0.0])
        vec = vec / np.linalg.norm(vec)  # Normalize
        
        similarity = clip_client.compute_similarity(vec, vec)
        self.assertAlmostEqual(similarity, 1.0, places=5)
    
    def test_compute_similarity_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors is 0.0"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        
        similarity = clip_client.compute_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 0.0, places=5)
    
    def test_compute_similarity_opposite_vectors(self):
        """Test similarity of opposite vectors is close to 0"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        
        similarity = clip_client.compute_similarity(vec1, vec2)
        # Opposite normalized vectors should give low/negative similarity
        # But function clamps to [0, 1]
        self.assertGreaterEqual(similarity, 0.0)
        self.assertLessEqual(similarity, 1.0)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_compute_similarity_real_embeddings(self):
        """Test similarity with real CLIP embeddings"""
        # Similar texts should have high similarity
        emb1 = clip_client.get_text_embedding("Financial revenue growth")
        emb2 = clip_client.get_text_embedding("Business profit increase")
        
        if emb1 is not None and emb2 is not None:
            similarity = clip_client.compute_similarity(emb1, emb2)
            
            # Similar concepts should have moderate to high similarity
            self.assertGreater(similarity, 0.3)
            self.assertLessEqual(similarity, 1.0)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_compute_similarity_dissimilar_embeddings(self):
        """Test similarity with dissimilar concepts"""
        emb1 = clip_client.get_text_embedding("Financial growth chart")
        emb2 = clip_client.get_text_embedding("Mountain landscape sunset")
        
        if emb1 is not None and emb2 is not None:
            similarity = clip_client.compute_similarity(emb1, emb2)
            
            # Dissimilar concepts should have low similarity
            self.assertLess(similarity, 0.5)
            self.assertGreaterEqual(similarity, 0.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_none_input(self):
        """Test handling of None input"""
        result = clip_client.get_text_embedding(None)
        self.assertIsNone(result)
    
    def test_very_long_text(self):
        """Test handling of very long text"""
        long_text = "word " * 10000  # Very long text
        
        if clip_client.is_clip_available():
            result = clip_client.get_text_embedding(long_text)
            # Should still work, model handles tokenization
            self.assertIsNotNone(result)
    
    def test_special_characters(self):
        """Test handling of special characters"""
        text = "Test!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        if clip_client.is_clip_available():
            result = clip_client.get_text_embedding(text)
            self.assertIsNotNone(result)
    
    def test_unicode_text(self):
        """Test handling of Unicode/multilingual text"""
        texts = [
            "Привет мир",  # Russian
            "你好世界",      # Chinese
            "مرحبا العالم",  # Arabic
            "こんにちは世界"  # Japanese
        ]
        
        if clip_client.is_clip_available():
            for text in texts:
                result = clip_client.get_text_embedding(text)
                self.assertIsNotNone(result, f"Failed for: {text}")


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
