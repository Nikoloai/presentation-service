# 🎨 AI Presentation Generator

An MVP service that automatically creates PowerPoint presentations using AI-generated content and images.

## ✨ Features

- **AI-Powered Content**: Generates presentation content using OpenAI ChatGPT
- **Automatic Images**: Searches and adds relevant images using Pexels API
- **Beautiful Design**: Creates professional-looking slides with text and images
- **Easy to Use**: Simple web interface - just enter a topic and number of slides
- **Instant Download**: Get your PPTX file immediately

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Pexels API key ([Get one here](https://www.pexels.com/api) - free registration)

### Installation

1. **Clone or download this project**

2. **Install dependencies**
```bash
cd presentation-service
pip install -r requirements.txt
```

3. **Set up API keys**

Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
OPENAI_API_KEY=sk-your-actual-openai-key
PEXELS_API_KEY=your-actual-pexels-key
```

### Running the Application

1. **Start the server**
```bash
python app.py
```

2. **Open your browser**
Navigate to: `http://localhost:5000`

3. **Create a presentation**
   - Enter a topic (e.g., "Python for Beginners")
   - Select number of slides (3-10)
   - Click "Create Presentation"
   - Wait 30-60 seconds
   - Download your PPTX file!

## 📁 Project Structure

```
presentation-service/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore file
├── README.md             # This file
├── templates/
│   └── index.html        # Web interface
├── static/
│   ├── style.css         # Styling
│   └── script.js         # Frontend logic
└── output/               # Generated presentations (auto-created)
```

## 🔧 How It Works

1. **User Input**: Enter topic and number of slides
2. **Content Generation**: ChatGPT creates structured content for each slide
3. **Image Search**: Pexels API finds relevant images based on slide titles
4. **Presentation Assembly**: python-pptx creates PPTX with text and images
5. **Download**: User receives ready-to-use presentation

## 🌐 API Keys Setup

### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key and add to `.env`

**Note**: OpenAI API is paid, but new accounts get free credits. Pricing: ~$0.002 per presentation.

### Pexels API Key

1. Go to [Pexels API](https://www.pexels.com/api)
2. Click "Get Started" and sign up (free)
3. Get your API key from the dashboard
4. Copy the key and add to `.env`

**Note**: Pexels API is completely free with 200 requests/hour limit.

## 🎯 Example Usage

**Topic**: "Machine Learning Basics"
**Slides**: 5

The system will generate:
- Slide 1: Introduction to ML
- Slide 2: Types of ML
- Slide 3: Key Algorithms
- Slide 4: Applications
- Slide 5: Getting Started

Each slide includes:
- Title
- Bullet points or text content
- Relevant image

## ⚙️ Configuration

Edit `app.py` to customize:
- Slide dimensions (default: 960x540 px)
- Font sizes and colors
- Layout style
- Image positioning

## 🚢 Deployment

### Local Deployment
Already configured! Just run `python app.py`

### Heroku Deployment

1. Create `Procfile`:
```
web: python app.py
```

2. Deploy:
```bash
heroku create your-app-name
heroku config:set OPENAI_API_KEY=your_key
heroku config:set PEXELS_API_KEY=your_key
git push heroku main
```

### Other Platforms
Works on: Render, Railway, PythonAnywhere, DigitalOcean, etc.

## 🛠️ Troubleshooting

**Error: "OpenAI API key not configured"**
- Make sure `.env` file exists with correct API key
- Check that the key starts with `sk-`

**Error: "Pexels API key not configured"**
- Verify Pexels API key in `.env`
- Check key is valid in Pexels dashboard

**Slow generation**
- Normal! Takes 30-60 seconds
- ChatGPT API: ~10-15 seconds
- Image downloads: ~3-5 seconds per slide
- PPTX creation: ~5 seconds

**No images in slides**
- Check Pexels API key
- Verify internet connection
- Images are optional - presentation still works without them

## 📝 License

This project is open source and available for personal and commercial use.

## 🤝 Contributing

Feel free to fork, modify, and improve this project!

## 📧 Support

For issues or questions, check the console output for detailed error messages.

---

**Built with ❤️ using Flask, OpenAI, and Pexels**
