# Quick Start Guide

## Step 1: Install Dependencies

```bash
cd presentation-service
pip install -r requirements.txt
```

## Step 2: Get API Keys

### OpenAI API Key (Required)
1. Visit: https://platform.openai.com/api-keys
2. Sign up/login
3. Create new secret key
4. Copy the key (starts with `sk-`)

### Pexels API Key (Required)
1. Visit: https://www.pexels.com/api
2. Sign up (free)
3. Get API key from dashboard

## Step 3: Configure Environment

Create `.env` file in project root:

```
OPENAI_API_KEY=sk-your-actual-key-here
PEXELS_API_KEY=your-pexels-key-here
```

## Step 4: Run the Application

```bash
python app.py
```

## Step 5: Access the Application

Open browser: http://localhost:5000

## Step 6: Create Your First Presentation

1. Enter topic: "Artificial Intelligence"
2. Select slides: 5
3. Click "Create Presentation"
4. Wait ~30-60 seconds
5. Download PPTX file

## Troubleshooting

**Import Error**
```bash
pip install -r requirements.txt --upgrade
```

**API Key Error**
- Check `.env` file exists
- Verify keys are correct
- No quotes needed around keys

**Port Already in Use**
Edit `app.py` line 320:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

## Features

✅ AI-generated content using ChatGPT
✅ Automatic image search and download
✅ Professional slide design
✅ Download PPTX files
✅ Preview generated slides
✅ Error handling

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript
- **AI**: OpenAI GPT-3.5
- **Images**: Pexels API
- **PPTX**: python-pptx

## Cost

- **OpenAI**: ~$0.002 per presentation (free credits for new users)
- **Pexels**: Free (200 requests/hour)

## Example Topics

- "Python Programming Basics"
- "Digital Marketing Strategy"
- "Climate Change Solutions"
- "Healthy Eating Habits"
- "Machine Learning Introduction"

Enjoy creating presentations! 🎨
