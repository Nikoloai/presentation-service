# Railway Deployment Guide

## Quick Start

### 1. Build Docker Image
```bash
docker build -t presentation-service .
```

### 2. Run Locally with Docker
```bash
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=your_openai_key \
  -e PEXELS_API_KEY=your_pexels_key \
  -e LIBRETRANSLATE_ENABLED=false \
  presentation-service
```

### 3. Deploy to Railway

1. **Push to GitHub/GitLab**
   - Commit all files including Dockerfile
   - Push to your repository

2. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure Environment Variables**
   Set these in Railway dashboard:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `PEXELS_API_KEY` - Your Pexels API key
   - `LIBRETRANSLATE_ENABLED` - Set to `false` (or `true` if running separate LibreTranslate service)
   - `LIBRETRANSLATE_URL` - (Optional) URL of LibreTranslate service if enabled

4. **Deploy**
   - Railway will automatically detect Dockerfile
   - Build and deploy will start automatically
   - Access your app at the provided Railway URL

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for text generation |
| `PEXELS_API_KEY` | Yes | - | Pexels API key for image search |
| `LIBRETRANSLATE_ENABLED` | No | `false` | Enable LibreTranslate for keyword translation |
| `LIBRETRANSLATE_URL` | No | `http://localhost:5001` | LibreTranslate service URL |
| `LIBRETRANSLATE_TIMEOUT` | No | `10` | LibreTranslate request timeout (seconds) |
| `PORT` | No | `5000` | Port to run the service on |

## Features Implemented

### ✅ Title Overflow Fix
- Automatically reduces font size by 25% for titles > 70 characters
- Title width limited to 8.5 inches with margins
- Word wrap enabled for all text boxes
- Long titles: 33pt (dark slides) / 27pt (content slides)
- Short titles: 44pt (dark slides) / 36pt (content slides)

### ✅ Docker Configuration
- Multi-stage build for optimization
- Python 3.11-slim base image
- Gunicorn for production deployment
- 2 workers, 120s timeout
- Automatic directory creation (output, image_cache)

### ✅ Railway-Ready
- Environment variable support
- CORS enabled for cross-origin requests
- Health check compatible
- Proper logging to stdout/stderr

## Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Python
python app.py

# Or run with Docker
docker build -t presentation-service .
docker run -p 5000:5000 --env-file .env presentation-service
```

## API Endpoints

- `GET /` - Web interface
- `POST /api/create-presentation` - Generate presentation
- `GET /api/download/<filename>` - Download presentation file

## Troubleshooting

### Title Still Overflowing
- Ensure titles are not extremely long (>100 chars)
- Check slide layout configuration
- Verify font size adjustments in logs

### Docker Build Fails
- Check internet connection
- Ensure Dockerfile syntax is correct
- Verify Python version compatibility

### Railway Deployment Issues
- Verify environment variables are set
- Check Railway logs for errors
- Ensure PORT variable is not overridden
