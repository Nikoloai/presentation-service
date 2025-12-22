# CLIP Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install Dependencies

```bash
cd d:/presentation-service
pip install -r requirements.txt
```

⏱ **Time:** ~5-10 minutes (PyTorch download ~2GB)

### 2. Start Application

```bash
python app.py
```

**Expected output:**
```
📦 CLIP services imported successfully
🔄 Loading CLIP model (this may take a minute on first run)...
✅ CLIP model loaded successfully
   → Model: clip-ViT-B-32
   → Embedding dimension: 512
✅ Payment verification: ENABLED (production mode)
 * Running on http://127.0.0.1:5000
```

⏱ **First run:** ~30-60 seconds (model download)  
⏱ **Next runs:** instant (model cached)

### 3. Test CLIP

```bash
# Quick test
python -m services.image_matcher
```

**Expected output:**
```
============================================================
Testing CLIP Image Matcher
============================================================

Slide: 'Revenue Growth Analysis'

  🤖 CLIP semantic matching for: 'Revenue Growth Analysis'
     [1] Business chart showing financial growth → 0.823
     [2] Professional business team working      → 0.542
     [3] Beautiful mountain landscape            → 0.187

✅ Best match selected:
   URL: https://example.com/chart.jpg
   Description: Business chart showing financial growth
```

### 4. Run Tests (Optional)

```bash
# All tests
python -m pytest tests/ -v

# Just CLIP tests
python -m pytest tests/test_clip_client.py tests/test_image_matcher.py -v
```

---

## ✅ Verification Checklist

After installation, verify:

- [ ] Application starts without errors
- [ ] CLIP services imported successfully
- [ ] Model loaded (first run takes ~1 minute)
- [ ] Tests pass (optional but recommended)
- [ ] Create a test presentation and check logs for "🤖 Using CLIP semantic matching"

---

## 🎯 How to Use

### Automatic (Recommended)

CLIP is automatically used when you create presentations. No code changes needed!

Just create a presentation as usual:
```bash
POST /api/create-presentation
{
  "topic": "Business Growth",
  "slides": 10,
  "presentation_type": "business"
}
```

In the logs, you'll see:
```
🔍 Searching image for slide: 'Revenue Analysis'
  🤖 Using CLIP semantic matching for better relevance
  📊 Found 15 candidates, applying CLIP ranking...
     [1] Financial chart showing revenue growth → 0.782
     [2] Business meeting presentation         → 0.543
  ✅ CLIP selected best match: https://...
```

### Manual Configuration

If you want to adjust CLIP behavior, edit `app.py`:

```python
# Line ~2165 in search_image_for_slide()

# Adjust number of candidates (default: 15)
candidate_count = 15  # Try 10 for faster, 20 for more choice

# Adjust similarity threshold (default: 0.25)
similarity_threshold=0.25  # Higher = stricter matching
```

---

## 🔧 Configuration Options

### 1. Enable/Disable CLIP

**Option A:** Environment variable (`.env` file)
```bash
CLIP_ENABLED=true   # Enable CLIP (default)
CLIP_ENABLED=false  # Disable CLIP, use keyword search only
```

**Option B:** Code (app.py, line ~30)
```python
CLIP_ENABLED = False  # Temporarily disable
```

### 2. Adjust Similarity Threshold

**File:** `app.py`, function `search_image_for_slide()` (~line 2200)

```python
similarity_threshold=0.25  # Change this value
```

**Recommendations:**
- `0.15-0.20` = Very permissive (accepts most images)
- `0.25-0.30` = **Recommended** (good balance)
- `0.35-0.45` = Strict (only highly relevant images)
- `0.50+` = Very strict (may reject too many)

### 3. Number of Candidates

**File:** `app.py`, function `search_image_for_slide()` (~line 2172)

```python
candidate_count = 15  # Change this value
```

**Trade-offs:**
- `5-10` = Faster processing, fewer options
- `10-15` = **Recommended** (balanced)
- `15-20` = More options, slower processing

---

## 📊 Performance

### Typical Performance (CPU)

| Operation | Time |
|-----------|------|
| First model load | 30-60 sec |
| Process 1 slide | 1-2 sec |
| Process 10-slide presentation | 10-20 sec |

### With GPU

| Operation | Time |
|-----------|------|
| First model load | 30-60 sec |
| Process 1 slide | 0.3-0.5 sec |
| Process 10-slide presentation | 3-5 sec |

### Memory Usage

- **Model:** ~600 MB
- **Cache:** ~5-10 MB
- **Total:** ~1 GB peak

---

## ❓ Troubleshooting

### Problem: ModuleNotFoundError: No module named 'torch'

**Solution:**
```bash
pip install torch torchvision sentence-transformers
```

### Problem: CLIP model download timeout

**Solution:**
```bash
# Download manually
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('clip-ViT-B-32')"
```

### Problem: Application works but CLIP not being used

**Check logs for:**
```
⚠️ CLIP services not available
```

**Solution:**
1. Verify dependencies: `pip list | grep -E "torch|sentence"`
2. Reinstall if needed: `pip install --force-reinstall sentence-transformers`
3. Check `CLIP_ENABLED` is not set to `false`

### Problem: Too slow on my machine

**Solutions:**
1. Reduce candidate count to 10 (line ~2172 in app.py)
2. Increase threshold to 0.3-0.4 (fewer iterations)
3. Use GPU if available
4. Disable CLIP: `CLIP_ENABLED=false`

---

## 📚 Additional Resources

- **Full Documentation:** [CLIP_INTEGRATION_GUIDE.md](CLIP_INTEGRATION_GUIDE.md)
- **Changes Summary:** [CLIP_CHANGES_SUMMARY.md](CLIP_CHANGES_SUMMARY.md)
- **Tests:** `tests/test_clip_client.py`, `tests/test_image_matcher.py`

---

## 🎉 You're Ready!

CLIP is now integrated and working. Create a presentation and enjoy more relevant images!

**Questions?** Check the [full documentation](CLIP_INTEGRATION_GUIDE.md) or create an issue.

---

**Version:** 1.0.0  
**Last Updated:** 2024-12-21
