"""
Semantic Image Matcher Service

Uses CLIP embeddings to find the best matching image for slide content.
Improves upon keyword-based search by understanding semantic meaning.

Features:
- Semantic similarity scoring using CLIP
- Threshold-based filtering (rejects poor matches)
- Graceful fallback to keyword search if CLIP unavailable
- Integration with duplicate prevention system
"""

from typing import Optional, List, Dict, Tuple
import numpy as np

from services.clip_client import (
    get_text_embedding,
    compute_similarity,
    is_clip_available
)


# Configuration
SIMILARITY_THRESHOLD = 0.25  # Minimum similarity score to accept an image
# Lower threshold = more permissive (more images accepted)
# Higher threshold = more strict (fewer but more relevant images)
# 0.25 is a good default for CLIP embeddings


def pick_best_image_for_slide(
    slide_title: str,
    slide_content: str,
    image_candidates: List[Dict],
    exclude_images: Optional[List[str]] = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD
) -> Optional[Dict]:
    """
    Select the best image for a slide using CLIP semantic matching.
    
    Args:
        slide_title: Title of the slide
        slide_content: Main content/text of the slide
        image_candidates: List of candidate images with structure:
            [
                {
                    'url': 'https://...',
                    'description': 'Text description of image',
                    'author': 'Photographer name',
                    'source': 'Pexels/Unsplash',
                    ...
                }
            ]
        exclude_images: List of image URLs to exclude (for duplicate prevention)
        similarity_threshold: Minimum similarity score to accept (0-1 range)
    
    Returns:
        Best matching image dict or None if no good match found
    
    Algorithm:
        1. Combine slide title + content into semantic context
        2. Get CLIP embedding for the context
        3. For each candidate, get embedding for its description
        4. Compute cosine similarity between context and each candidate
        5. Return candidate with highest similarity above threshold
        6. If CLIP unavailable, return first non-excluded candidate (fallback)
    """
    if not image_candidates:
        return None
    
    if exclude_images is None:
        exclude_images = []
    
    # Filter out excluded images
    candidates = [
        img for img in image_candidates
        if img.get('url') not in exclude_images
    ]
    
    if not candidates:
        print("  ⚠️ All image candidates are in exclude list")
        return None
    
    # If CLIP not available, fall back to first valid candidate
    if not is_clip_available():
        print("  ⚠️ CLIP unavailable, using fallback (first candidate)")
        return candidates[0]
    
    # Combine slide context for semantic matching
    slide_context = f"{slide_title}. {slide_content[:200]}"  # Limit content length
    
    print(f"  🤖 CLIP semantic matching for: '{slide_title}'")
    print(f"     Context: {slide_context[:80]}...")
    
    # Get embedding for slide context
    context_embedding = get_text_embedding(slide_context)
    
    if context_embedding is None:
        print("  ⚠️ Failed to get context embedding, using fallback")
        return candidates[0]
    
    # Score each candidate
    scored_candidates = []
    
    for idx, candidate in enumerate(candidates):
        # Get text description for the image
        # Use description if available, otherwise use search query or title
        img_description = (
            candidate.get('description') or
            candidate.get('alt') or
            candidate.get('attribution') or
            slide_title  # Fallback to slide title
        )
        
        # Get embedding for image description
        img_embedding = get_text_embedding(img_description)
        
        if img_embedding is None:
            # Skip this candidate if embedding fails
            continue
        
        # Compute similarity
        similarity = compute_similarity(context_embedding, img_embedding)
        
        scored_candidates.append({
            'candidate': candidate,
            'similarity': similarity,
            'description': img_description[:60]
        })
        
        print(f"     [{idx+1}] {img_description[:40]:40s} → {similarity:.3f}")
    
    if not scored_candidates:
        print("  ❌ No candidates could be scored")
        return None
    
    # Sort by similarity (descending)
    scored_candidates.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Print top 3 candidates for debugging
    print(f"\n  🏆 Top 3 candidates:")
    for i, item in enumerate(scored_candidates[:3]):
        source = item['candidate'].get('source', 'Unknown')
        print(f"     [{i+1}] {item['description'][:35]:35s} → {item['similarity']:.3f} ({source})")
    
    # Get best candidate
    best = scored_candidates[0]
    
    # Check if it meets threshold
    if best['similarity'] < similarity_threshold:
        print(f"\n  ❌ Best match ({best['similarity']:.3f}) below threshold ({similarity_threshold:.3f})")
        return None
    
    print(f"\n  ✅ Best match: '{best['description']}' (similarity: {best['similarity']:.3f})")
    
    # Add similarity score to returned candidate for logging
    result = best['candidate'].copy()
    result['_clip_similarity'] = f"{best['similarity']:.3f}"
    
    return result


def rank_images_by_relevance(
    slide_title: str,
    slide_content: str,
    image_candidates: List[Dict],
    top_k: int = 5
) -> List[Tuple[Dict, float]]:
    """
    Rank all image candidates by semantic relevance.
    
    Args:
        slide_title: Title of the slide
        slide_content: Main content of the slide
        image_candidates: List of candidate images
        top_k: Return top K results (default: 5)
    
    Returns:
        List of tuples: [(image_dict, similarity_score), ...]
        Sorted by similarity (highest first)
    """
    if not image_candidates:
        return []
    
    if not is_clip_available():
        # Fallback: return all candidates with score 0
        return [(img, 0.0) for img in image_candidates[:top_k]]
    
    # Get slide context embedding
    slide_context = f"{slide_title}. {slide_content[:200]}"
    context_embedding = get_text_embedding(slide_context)
    
    if context_embedding is None:
        return [(img, 0.0) for img in image_candidates[:top_k]]
    
    # Score all candidates
    scored = []
    
    for candidate in image_candidates:
        img_description = (
            candidate.get('description') or
            candidate.get('attribution') or
            slide_title
        )
        
        img_embedding = get_text_embedding(img_description)
        
        if img_embedding is not None:
            similarity = compute_similarity(context_embedding, img_embedding)
            scored.append((candidate, similarity))
    
    # Sort by similarity
    scored.sort(key=lambda x: x[1], reverse=True)
    
    return scored[:top_k]


def get_similarity_for_image(
    slide_title: str,
    slide_content: str,
    image_description: str
) -> float:
    """
    Get semantic similarity score between slide content and image description.
    
    Useful for debugging or fine-tuning threshold values.
    
    Args:
        slide_title: Slide title
        slide_content: Slide content
        image_description: Description of the image
    
    Returns:
        float: Similarity score (0-1) or 0.0 if CLIP unavailable
    """
    if not is_clip_available():
        return 0.0
    
    slide_context = f"{slide_title}. {slide_content[:200]}"
    
    context_emb = get_text_embedding(slide_context)
    image_emb = get_text_embedding(image_description)
    
    if context_emb is None or image_emb is None:
        return 0.0
    
    return compute_similarity(context_emb, image_emb)


def test_matcher():
    """
    Simple test function to verify CLIP matching works.
    
    Usage:
        python -m services.image_matcher
    """
    print("\n" + "="*60)
    print("Testing CLIP Image Matcher")
    print("="*60 + "\n")
    
    # Test data
    slide_title = "Revenue Growth Analysis"
    slide_content = "Our Q4 2024 financial results show a 45% increase in revenue compared to last year. Sales performance exceeded expectations."
    
    test_candidates = [
        {
            'url': 'https://example.com/chart.jpg',
            'description': 'Business chart showing financial growth and revenue increase',
            'source': 'Pexels'
        },
        {
            'url': 'https://example.com/nature.jpg',
            'description': 'Beautiful mountain landscape with sunset',
            'source': 'Unsplash'
        },
        {
            'url': 'https://example.com/team.jpg',
            'description': 'Professional business team working in modern office',
            'source': 'Pexels'
        }
    ]
    
    print(f"Slide: '{slide_title}'")
    print(f"Content: {slide_content[:80]}...\n")
    
    if not is_clip_available():
        print("❌ CLIP not available - install dependencies first")
        return
    
    print("Testing semantic matching...\n")
    
    best = pick_best_image_for_slide(
        slide_title=slide_title,
        slide_content=slide_content,
        image_candidates=test_candidates
    )
    
    if best:
        print(f"\n✅ Best match selected:")
        print(f"   URL: {best['url']}")
        print(f"   Description: {best['description']}")
    else:
        print("\n❌ No suitable match found")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    test_matcher()
