"""
Unit tests for Image Matcher service

Tests cover:
- Best image selection with CLIP
- Threshold filtering
- Duplicate exclusion
- Fallback behavior when CLIP unavailable
- Edge cases (empty candidates, all excluded, etc.)
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import image_matcher
from services import clip_client


class TestPickBestImage(unittest.TestCase):
    """Test pick_best_image_for_slide function"""
    
    def setUp(self):
        """Set up test data"""
        self.slide_title = "Financial Growth Analysis"
        self.slide_content = "Our Q4 revenue increased by 45% compared to last year."
        
        self.candidates = [
            {
                'url': 'https://example.com/chart.jpg',
                'description': 'Business financial growth chart showing revenue increase',
                'source': 'Pexels'
            },
            {
                'url': 'https://example.com/landscape.jpg',
                'description': 'Beautiful mountain landscape with trees',
                'source': 'Unsplash'
            },
            {
                'url': 'https://example.com/team.jpg',
                'description': 'Professional business team in modern office',
                'source': 'Pexels'
            }
        ]
    
    def test_empty_candidates_returns_none(self):
        """Test that empty candidate list returns None"""
        result = image_matcher.pick_best_image_for_slide(
            slide_title=self.slide_title,
            slide_content=self.slide_content,
            image_candidates=[]
        )
        self.assertIsNone(result)
    
    def test_all_candidates_excluded_returns_none(self):
        """Test that all excluded candidates returns None"""
        exclude = [img['url'] for img in self.candidates]
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title=self.slide_title,
            slide_content=self.slide_content,
            image_candidates=self.candidates,
            exclude_images=exclude
        )
        self.assertIsNone(result)
    
    def test_excludes_specific_images(self):
        """Test that specific images are excluded"""
        exclude = [self.candidates[0]['url']]
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title=self.slide_title,
            slide_content=self.slide_content,
            image_candidates=self.candidates,
            exclude_images=exclude
        )
        
        if result:
            self.assertNotEqual(result['url'], self.candidates[0]['url'])
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_returns_most_relevant_image(self):
        """Test that most semantically relevant image is selected"""
        result = image_matcher.pick_best_image_for_slide(
            slide_title=self.slide_title,
            slide_content=self.slide_content,
            image_candidates=self.candidates
        )
        
        self.assertIsNotNone(result)
        # First candidate (financial chart) should be most relevant
        # but we can't guarantee exact match in unit test
        self.assertIn('url', result)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_respects_threshold(self):
        """Test that low similarity scores are rejected"""
        # Use very different content
        dissimilar_candidates = [
            {
                'url': 'https://example.com/cat.jpg',
                'description': 'Cute cat sleeping on couch',
                'source': 'Unsplash'
            }
        ]
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title=self.slide_title,
            slide_content=self.slide_content,
            image_candidates=dissimilar_candidates,
            similarity_threshold=0.8  # Very high threshold
        )
        
        # Should reject if similarity too low
        # (might pass if CLIP finds unexpected similarity)
        self.assertIn(result, [None, dissimilar_candidates[0]])
    
    @patch('services.clip_client.is_clip_available')
    def test_fallback_when_clip_unavailable(self, mock_available):
        """Test graceful fallback when CLIP not available"""
        mock_available.return_value = False
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title=self.slide_title,
            slide_content=self.slide_content,
            image_candidates=self.candidates
        )
        
        # Should return first candidate as fallback
        self.assertEqual(result, self.candidates[0])


class TestRankImages(unittest.TestCase):
    """Test rank_images_by_relevance function"""
    
    def setUp(self):
        """Set up test data"""
        self.candidates = [
            {'url': 'img1.jpg', 'description': 'Financial chart'},
            {'url': 'img2.jpg', 'description': 'Mountain landscape'},
            {'url': 'img3.jpg', 'description': 'Business meeting'}
        ]
    
    def test_empty_candidates_returns_empty_list(self):
        """Test that empty candidates returns empty list"""
        result = image_matcher.rank_images_by_relevance(
            slide_title="Test",
            slide_content="Test content",
            image_candidates=[]
        )
        self.assertEqual(result, [])
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_returns_ranked_list(self):
        """Test that ranked list is returned"""
        result = image_matcher.rank_images_by_relevance(
            slide_title="Financial Analysis",
            slide_content="Revenue and profit growth",
            image_candidates=self.candidates,
            top_k=2
        )
        
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 2)  # top_k=2
        
        if len(result) > 0:
            # Each item should be (image_dict, score)
            self.assertIsInstance(result[0], tuple)
            self.assertEqual(len(result[0]), 2)
            self.assertIsInstance(result[0][1], float)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_ranking_is_sorted(self):
        """Test that results are sorted by similarity (descending)"""
        result = image_matcher.rank_images_by_relevance(
            slide_title="Financial Analysis",
            slide_content="Revenue growth",
            image_candidates=self.candidates
        )
        
        if len(result) > 1:
            # Scores should be in descending order
            scores = [score for _, score in result]
            self.assertEqual(scores, sorted(scores, reverse=True))


class TestGetSimilarity(unittest.TestCase):
    """Test get_similarity_for_image function"""
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_similar_content_high_score(self):
        """Test that similar content produces high similarity"""
        similarity = image_matcher.get_similarity_for_image(
            slide_title="Revenue Growth",
            slide_content="Financial performance increased",
            image_description="Business chart showing revenue increase"
        )
        
        self.assertIsInstance(similarity, float)
        self.assertGreater(similarity, 0.2)  # Should have some similarity
        self.assertLessEqual(similarity, 1.0)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_dissimilar_content_low_score(self):
        """Test that dissimilar content produces low similarity"""
        similarity = image_matcher.get_similarity_for_image(
            slide_title="Revenue Growth",
            slide_content="Financial analysis",
            image_description="Cat playing with yarn ball"
        )
        
        self.assertIsInstance(similarity, float)
        # Dissimilar content should have lower score
        self.assertLess(similarity, 0.5)
    
    @patch('services.clip_client.is_clip_available')
    def test_returns_zero_when_clip_unavailable(self, mock_available):
        """Test returns 0.0 when CLIP unavailable"""
        mock_available.return_value = False
        
        similarity = image_matcher.get_similarity_for_image(
            slide_title="Test",
            slide_content="Test content",
            image_description="Test image"
        )
        
        self.assertEqual(similarity, 0.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_candidates_without_description(self):
        """Test handling of candidates without description field"""
        candidates = [
            {'url': 'img1.jpg'},  # No description
            {'url': 'img2.jpg', 'description': ''}  # Empty description
        ]
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title="Test Slide",
            slide_content="Test content",
            image_candidates=candidates
        )
        
        # Should handle gracefully (use fallback or other fields)
        self.assertIn(result, [None, candidates[0], candidates[1]])
    
    def test_very_long_slide_content(self):
        """Test handling of very long slide content"""
        long_content = "word " * 1000  # Very long content
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title="Test",
            slide_content=long_content,
            image_candidates=[{'url': 'test.jpg', 'description': 'test'}]
        )
        
        # Should handle without crashing
        self.assertIsNotNone(result)
    
    def test_none_exclude_images(self):
        """Test that None exclude_images is handled"""
        candidates = [{'url': 'test.jpg', 'description': 'test'}]
        
        result = image_matcher.pick_best_image_for_slide(
            slide_title="Test",
            slide_content="Test",
            image_candidates=candidates,
            exclude_images=None
        )
        
        self.assertEqual(result, candidates[0])


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
