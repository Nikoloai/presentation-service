"""
Integration tests for CLIP-enhanced image search in presentation generation

Tests the complete workflow from slide content to CLIP-powered image selection,
ensuring all components work together correctly.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
import app
from services import clip_client, image_matcher


class TestCLIPIntegration(unittest.TestCase):
    """Integration tests for CLIP in the full presentation workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.slide_title = "Revenue Growth Analysis"
        self.slide_content = "Our Q4 2024 revenue increased by 45% compared to last year."
        self.main_topic = "Business Performance"
        
        self.mock_candidates = [
            {
                'url': 'https://example.com/financial-chart.jpg',
                'description': 'Business financial growth chart showing revenue increase',
                'author': 'John Doe',
                'source': 'Pexels',
                'attribution': 'Photo by John Doe on Pexels'
            },
            {
                'url': 'https://example.com/team-meeting.jpg',
                'description': 'Professional business team working in modern office',
                'author': 'Jane Smith',
                'source': 'Unsplash',
                'attribution': 'Photo by Jane Smith on Unsplash'
            },
            {
                'url': 'https://example.com/landscape.jpg',
                'description': 'Beautiful mountain landscape with trees and sky',
                'author': 'Bob Johnson',
                'source': 'Pexels',
                'attribution': 'Photo by Bob Johnson on Pexels'
            }
        ]
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_search_image_for_slide_with_clip(self):
        """Test that search_image_for_slide uses CLIP when available"""
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download:
            
            # Setup mocks
            mock_get_images.return_value = self.mock_candidates
            mock_download.return_value = b'fake_image_data'
            
            # Call the function
            image_data, image_url, query = app.search_image_for_slide(
                slide_title=self.slide_title,
                slide_content=self.slide_content,
                main_topic=self.main_topic,
                exclude_images=[],
                presentation_type='business'
            )
            
            # Verify CLIP was used (get_images should be called)
            mock_get_images.assert_called()
            
            # Should return valid results
            self.assertIsNotNone(image_data)
            self.assertIsNotNone(image_url)
            self.assertIsNotNone(query)
            
            # URL should be one of our candidates
            self.assertIn(image_url, [c['url'] for c in self.mock_candidates])
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_clip_selects_most_relevant_image(self):
        """Test that CLIP selects the most semantically relevant image"""
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download:
            
            mock_get_images.return_value = self.mock_candidates
            mock_download.return_value = b'fake_image_data'
            
            # Call function
            image_data, image_url, query = app.search_image_for_slide(
                slide_title=self.slide_title,
                slide_content=self.slide_content,
                main_topic=self.main_topic,
                exclude_images=[],
                presentation_type='business'
            )
            
            # The financial chart should be selected (most relevant)
            # We can't guarantee exact selection, but we can verify it's not the landscape
            if image_url:
                self.assertNotEqual(
                    image_url,
                    'https://example.com/landscape.jpg',
                    "CLIP should not select irrelevant landscape image for business slide"
                )
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_clip_respects_exclude_images(self):
        """Test that CLIP respects the exclude_images list"""
        
        # Exclude the most relevant image
        exclude = ['https://example.com/financial-chart.jpg']
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download:
            
            mock_get_images.return_value = self.mock_candidates
            mock_download.return_value = b'fake_image_data'
            
            image_data, image_url, query = app.search_image_for_slide(
                slide_title=self.slide_title,
                slide_content=self.slide_content,
                main_topic=self.main_topic,
                exclude_images=exclude,
                presentation_type='business'
            )
            
            # Should not return excluded image
            if image_url:
                self.assertNotIn(image_url, exclude)
    
    def test_fallback_when_clip_unavailable(self):
        """Test graceful fallback when CLIP is not available"""
        
        with patch('app.CLIP_ENABLED', False), \
             patch('app.is_clip_available', return_value=False), \
             patch('app.search_image_with_fallback') as mock_fallback:
            
            # Setup mock for fallback
            mock_fallback.return_value = (b'image_data', 'http://example.com/img.jpg', {})
            
            # Call function
            image_data, image_url, query = app.search_image_for_slide(
                slide_title=self.slide_title,
                slide_content=self.slide_content,
                main_topic=self.main_topic,
                exclude_images=[],
                presentation_type='business'
            )
            
            # Fallback should be called
            mock_fallback.assert_called_once()
            
            # Should still return results
            self.assertIsNotNone(image_data)
            self.assertIsNotNone(image_url)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_clip_with_no_suitable_candidates(self):
        """Test CLIP behavior when no candidates meet threshold"""
        
        # Create candidates with very different content
        dissimilar_candidates = [
            {
                'url': 'https://example.com/cat.jpg',
                'description': 'Cute cat sleeping on sofa',
                'author': 'Test',
                'source': 'Test'
            },
            {
                'url': 'https://example.com/flower.jpg',
                'description': 'Beautiful red roses in garden',
                'author': 'Test',
                'source': 'Test'
            }
        ]
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.search_image_with_fallback') as mock_fallback:
            
            mock_get_images.return_value = dissimilar_candidates
            mock_fallback.return_value = (b'fallback_image', 'http://fallback.jpg', {})
            
            # Call with very high threshold (should reject all)
            with patch.object(app, 'clip_pick_best_image', 
                            wraps=image_matcher.pick_best_image_for_slide) as mock_clip:
                
                image_data, image_url, query = app.search_image_for_slide(
                    slide_title=self.slide_title,
                    slide_content=self.slide_content,
                    main_topic=self.main_topic,
                    exclude_images=[],
                    presentation_type='business'
                )
            
            # Fallback should be called when CLIP finds nothing
            mock_fallback.assert_called()


class TestCLIPCaching(unittest.TestCase):
    """Test CLIP caching behavior"""
    
    def setUp(self):
        """Clear cache before each test"""
        clip_client.clear_cache()
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_cache_improves_performance(self):
        """Test that caching improves performance on repeated queries"""
        import time
        
        text = "Business revenue growth analysis"
        
        # First call (uncached)
        start1 = time.time()
        emb1 = clip_client.get_text_embedding(text)
        time1 = time.time() - start1
        
        # Second call (should be cached)
        start2 = time.time()
        emb2 = clip_client.get_text_embedding(text)
        time2 = time.time() - start2
        
        # Verify results are identical
        import numpy as np
        np.testing.assert_array_equal(emb1, emb2)
        
        # Cached call should be significantly faster
        # (allow some tolerance for system variance)
        self.assertLess(
            time2,
            time1 * 0.5,  # Cached should be at least 2x faster
            "Cached embedding retrieval should be much faster"
        )
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_cache_handles_multiple_slides(self):
        """Test cache performance with multiple slide queries"""
        
        slides = [
            "Introduction to Business",
            "Market Analysis",
            "Revenue Growth",
            "Customer Satisfaction",
            "Future Roadmap"
        ]
        
        # Get embeddings for all slides
        embeddings = []
        for slide in slides:
            emb = clip_client.get_text_embedding(slide)
            embeddings.append(emb)
        
        # Cache should contain all slides
        stats = clip_client.get_cache_stats()
        self.assertGreaterEqual(stats['size'], len(slides))
        
        # Verify all embeddings are valid
        for emb in embeddings:
            self.assertIsNotNone(emb)
            self.assertEqual(len(emb.shape), 1)  # 1D array


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end tests simulating real presentation generation"""
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_multiple_slides_no_duplicate_images(self):
        """Test that multiple slides don't get duplicate images"""
        
        slides = [
            {"title": "Revenue Analysis", "content": "Q4 revenue increased 45%"},
            {"title": "Market Share", "content": "We captured 23% market share"},
            {"title": "Customer Growth", "content": "Customer base grew by 12%"}
        ]
        
        used_images = set()
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download:
            
            # Return different images for each call
            mock_get_images.side_effect = [
                [
                    {'url': f'http://example.com/img{i}.jpg', 
                     'description': f'Image {i}',
                     'author': 'Test',
                     'source': 'Test'}
                    for i in range(15)
                ]
                for _ in range(len(slides))
            ]
            
            mock_download.return_value = b'fake_image_data'
            
            # Process each slide
            for slide in slides:
                exclude = list(used_images)
                
                image_data, image_url, query = app.search_image_for_slide(
                    slide_title=slide['title'],
                    slide_content=slide['content'],
                    main_topic="Business Performance",
                    exclude_images=exclude,
                    presentation_type='business'
                )
                
                if image_url:
                    # Verify no duplicates
                    self.assertNotIn(image_url, used_images,
                                   "Should not reuse images across slides")
                    used_images.add(image_url)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_presentation_type_affects_selection(self):
        """Test that presentation_type parameter is passed correctly"""
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download:
            
            mock_get_images.return_value = [
                {
                    'url': 'http://example.com/scientific.jpg',
                    'description': 'Scientific research laboratory',
                    'author': 'Test',
                    'source': 'Test'
                }
            ]
            mock_download.return_value = b'fake_image_data'
            
            # Call with scientific presentation type
            image_data, image_url, query = app.search_image_for_slide(
                slide_title="Research Methodology",
                slide_content="Double-blind controlled experiment",
                main_topic="Scientific Study",
                exclude_images=[],
                presentation_type='scientific'
            )
            
            # Should work without errors
            self.assertIsNotNone(image_data)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def test_empty_slide_content(self):
        """Test handling of empty slide content"""
        
        with patch('app.search_image_with_fallback') as mock_fallback:
            mock_fallback.return_value = (b'data', 'http://img.jpg', {})
            
            # Should not crash with empty content
            image_data, image_url, query = app.search_image_for_slide(
                slide_title="Empty Slide",
                slide_content="",
                main_topic="Test",
                exclude_images=[],
                presentation_type='business'
            )
            
            # Should still return something (via fallback)
            self.assertIsNotNone(image_data)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_network_error_during_download(self):
        """Test handling of network errors during image download"""
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download, \
             patch('app.search_image_with_fallback') as mock_fallback:
            
            mock_get_images.return_value = [
                {'url': 'http://example.com/img.jpg', 'description': 'Test'}
            ]
            # Simulate download failure
            mock_download.return_value = None
            mock_fallback.return_value = (b'fallback', 'http://fallback.jpg', {})
            
            image_data, image_url, query = app.search_image_for_slide(
                slide_title="Test",
                slide_content="Test content",
                main_topic="Test",
                exclude_images=[],
                presentation_type='business'
            )
            
            # Should fall back gracefully
            self.assertIsNotNone(image_data)
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_unicode_content(self):
        """Test handling of Unicode/multilingual content"""
        
        unicode_slides = [
            ("Русский текст", "Презентация на русском языке"),
            ("中文标题", "中文内容演示文稿"),
            ("العنوان العربي", "محتوى العرض التقديمي")
        ]
        
        with patch('app.get_images') as mock_get_images, \
             patch('app.download_image') as mock_download:
            
            mock_get_images.return_value = [
                {'url': 'http://example.com/img.jpg', 
                 'description': 'Test image',
                 'author': 'Test',
                 'source': 'Test'}
            ]
            mock_download.return_value = b'fake_image_data'
            
            for title, content in unicode_slides:
                # Should handle Unicode without errors
                try:
                    image_data, image_url, query = app.search_image_for_slide(
                        slide_title=title,
                        slide_content=content,
                        main_topic="Test",
                        exclude_images=[],
                        presentation_type='general'
                    )
                    self.assertIsNotNone(image_data)
                except Exception as e:
                    self.fail(f"Unicode content caused error: {e}")


def run_tests():
    """Run all integration tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
