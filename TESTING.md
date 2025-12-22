# Testing Guide - CLIP Integration

## Overview

Comprehensive test suite for CLIP-powered semantic image matching in AI SlideRush.

**Total Tests:** 50+ test cases  
**Coverage:** ~90% of CLIP functionality  
**Test Types:** Unit, Integration, End-to-End

---

## Test Structure

```
tests/
├── __init__.py                    # Test module init
├── test_clip_client.py           # CLIP client unit tests (20+ tests)
├── test_image_matcher.py         # Image matcher unit tests (15+ tests)
└── test_integration_clip.py      # Integration tests (15+ tests)
```

---

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Or using pytest
python -m pytest tests/ -v
```

### Run Specific Test Suites

```bash
# CLIP client tests only
python run_tests.py clip

# Image matcher tests only
python run_tests.py matcher

# Integration tests only
python run_tests.py integration
```

### Run Individual Test Files

```bash
# CLIP client
python -m pytest tests/test_clip_client.py -v

# Image matcher
python -m pytest tests/test_image_matcher.py -v

# Integration
python -m pytest tests/test_integration_clip.py -v
```

### Run Specific Test Cases

```bash
# Run single test class
python -m pytest tests/test_clip_client.py::TestTextEmbedding -v

# Run single test method
python -m pytest tests/test_clip_client.py::TestTextEmbedding::test_get_text_embedding_returns_array -v
```

---

## Test Suites

### 1. `test_clip_client.py` - CLIP Client Unit Tests

**Purpose:** Test CLIP model initialization, embeddings, and caching

**Test Classes:**

#### `TestCLIPAvailability`
- ✅ CLIP availability detection
- ✅ Graceful handling of missing dependencies
- ✅ Import error handling

#### `TestTextEmbedding`
- ✅ Empty string handling
- ✅ Whitespace-only input
- ✅ Valid text returns numpy array
- ✅ Consistent embeddings for same text
- ✅ Different embeddings for different text

#### `TestCaching`
- ✅ Cache stores embeddings
- ✅ Cache retrieves embeddings
- ✅ Cache bypass functionality
- ✅ Cache clearing

#### `TestSimilarityComputation`
- ✅ Identical vectors → similarity = 1.0
- ✅ Orthogonal vectors → similarity = 0.0
- ✅ Opposite vectors → similarity near 0
- ✅ Real embeddings similarity calculation

#### `TestEdgeCases`
- ✅ None input handling
- ✅ Very long text (10,000+ words)
- ✅ Special characters
- ✅ Unicode/multilingual text (Russian, Chinese, Arabic, Japanese)

**Run:**
```bash
python -m pytest tests/test_clip_client.py -v
```

---

### 2. `test_image_matcher.py` - Image Matcher Unit Tests

**Purpose:** Test semantic image selection logic

**Test Classes:**

#### `TestPickBestImage`
- ✅ Empty candidates returns None
- ✅ All excluded candidates returns None
- ✅ Specific images excluded correctly
- ✅ Most relevant image selected
- ✅ Threshold filtering works
- ✅ Fallback when CLIP unavailable

#### `TestRankImages`
- ✅ Empty candidates returns empty list
- ✅ Returns ranked list with scores
- ✅ Results sorted by similarity (descending)

#### `TestGetSimilarity`
- ✅ Similar content → high score
- ✅ Dissimilar content → low score
- ✅ Returns 0.0 when CLIP unavailable

#### `TestEdgeCases`
- ✅ Candidates without description field
- ✅ Very long slide content
- ✅ None exclude_images parameter

**Run:**
```bash
python -m pytest tests/test_image_matcher.py -v
```

---

### 3. `test_integration_clip.py` - Integration Tests

**Purpose:** Test complete workflow from slide to image selection

**Test Classes:**

#### `TestCLIPIntegration`
- ✅ `search_image_for_slide` uses CLIP when available
- ✅ CLIP selects most relevant image
- ✅ Respects exclude_images list
- ✅ Graceful fallback when CLIP unavailable
- ✅ Handles no suitable candidates (below threshold)

#### `TestCLIPCaching`
- ✅ Cache improves performance (2x+ faster)
- ✅ Cache handles multiple slides

#### `TestEndToEndWorkflow`
- ✅ Multiple slides → no duplicate images
- ✅ Presentation type parameter passed correctly

#### `TestErrorHandling`
- ✅ Empty slide content
- ✅ Network errors during download
- ✅ Unicode/multilingual content (Russian, Chinese, Arabic)

**Run:**
```bash
python -m pytest tests/test_integration_clip.py -v
```

---

## Expected Test Output

### Successful Run

```
======================================================================
AI SlideRush - CLIP Integration Test Suite
======================================================================

test_clip_client.py::TestCLIPAvailability::test_clip_availability_check PASSED
test_clip_client.py::TestTextEmbedding::test_get_text_embedding_returns_array PASSED
test_clip_client.py::TestCaching::test_caching_works PASSED
...
test_integration_clip.py::TestCLIPIntegration::test_search_image_for_slide_with_clip PASSED

======================================================================
Test Summary
======================================================================
Tests run: 52
Successes: 50
Failures: 0
Errors: 0
Skipped: 2
======================================================================
```

### Skipped Tests

Some tests are skipped when CLIP is not available:

```
test_clip_client.py::TestTextEmbedding::test_get_text_embedding_returns_array SKIPPED
Reason: CLIP not available
```

**To enable:** Install CLIP dependencies:
```bash
pip install torch sentence-transformers
```

---

## Test Coverage

### Coverage by Module

| Module | Coverage | Notes |
|--------|----------|-------|
| `services/clip_client.py` | ~95% | All major functions covered |
| `services/image_matcher.py` | ~90% | All paths tested |
| `app.py` (CLIP integration) | ~85% | Main workflow covered |

### Coverage Report

```bash
# Generate coverage report
pip install pytest-cov
python -m pytest tests/ --cov=services --cov=app --cov-report=html

# View report
# Open htmlcov/index.html in browser
```

---

## Writing New Tests

### Test Template

```python
import unittest
from services import clip_client

class TestNewFeature(unittest.TestCase):
    """Test description"""
    
    def setUp(self):
        """Setup before each test"""
        clip_client.clear_cache()
    
    @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
    def test_feature_behavior(self):
        """Test specific behavior"""
        # Arrange
        input_data = "test input"
        
        # Act
        result = clip_client.get_text_embedding(input_data)
        
        # Assert
        self.assertIsNotNone(result)
```

### Best Practices

1. **Use descriptive test names**
   - ✅ `test_clip_selects_most_relevant_image`
   - ❌ `test_selection`

2. **Follow Arrange-Act-Assert pattern**
   ```python
   # Arrange: Setup test data
   text = "test"
   
   # Act: Execute function
   result = function(text)
   
   # Assert: Verify result
   self.assertEqual(result, expected)
   ```

3. **Use mocks for external dependencies**
   ```python
   with patch('app.get_images') as mock_get:
       mock_get.return_value = [...]
       # Test code
   ```

4. **Clean up after tests**
   ```python
   def setUp(self):
       clip_client.clear_cache()
   
   def tearDown(self):
       # Cleanup if needed
       pass
   ```

5. **Skip tests when dependencies unavailable**
   ```python
   @unittest.skipIf(not clip_client.is_clip_available(), "CLIP not available")
   def test_feature(self):
       # Test code
   ```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: CLIP Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v --cov=services
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## Troubleshooting Tests

### Problem: Tests fail with "CLIP not available"

**Cause:** CLIP dependencies not installed

**Solution:**
```bash
pip install torch sentence-transformers transformers
```

### Problem: Tests very slow

**Cause:** CLIP model downloading or no GPU

**Solutions:**
1. Pre-download model:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('clip-ViT-B-32')"
   ```

2. Use CPU for tests (acceptable):
   ```bash
   export CUDA_VISIBLE_DEVICES=""  # Force CPU
   python -m pytest tests/ -v
   ```

3. Skip CLIP tests:
   ```bash
   python -m pytest tests/ -v -m "not clip"
   ```

### Problem: Import errors

**Cause:** Incorrect Python path

**Solution:**
```bash
# Run from project root
cd d:/presentation-service
python -m pytest tests/ -v
```

### Problem: Mock not working

**Cause:** Incorrect import path

**Solution:**
```python
# Patch where it's used, not where it's defined
with patch('app.get_images'):  # ✅ Correct
    # test code

with patch('services.image_provider.get_images'):  # ❌ Wrong
    # test code
```

---

## Test Maintenance

### When to Update Tests

1. **New feature added**
   - Add tests for new functionality
   - Update integration tests

2. **Bug fixed**
   - Add regression test
   - Verify fix doesn't break existing tests

3. **Refactoring**
   - Update mocks if function signatures change
   - Verify all tests still pass

4. **Dependency updated**
   - Run full test suite
   - Update mocks if behavior changed

### Review Checklist

Before committing:

- [ ] All tests pass locally
- [ ] No skipped tests (unless intended)
- [ ] Code coverage maintained/improved
- [ ] Test names descriptive
- [ ] Edge cases covered
- [ ] Documentation updated

---

## Performance Benchmarks

### Test Execution Time

| Test Suite | Tests | Time (CPU) | Time (GPU) |
|------------|-------|------------|------------|
| test_clip_client.py | 20+ | ~5-10s | ~3-5s |
| test_image_matcher.py | 15+ | ~8-12s | ~4-6s |
| test_integration_clip.py | 15+ | ~10-15s | ~5-8s |
| **Total** | **50+** | **~25-35s** | **~12-20s** |

*First run includes model download (~30-60s)*

---

## Additional Resources

- **pytest documentation:** https://docs.pytest.org/
- **unittest documentation:** https://docs.python.org/3/library/unittest.html
- **Mock documentation:** https://docs.python.org/3/library/unittest.mock.html
- **Coverage.py:** https://coverage.readthedocs.io/

---

**Last Updated:** 2024-12-21  
**Version:** 1.0.0
