// DOM Elements
const presentationForm = document.getElementById('presentationForm');
const formSection = document.getElementById('formSection');
const loadingSection = document.getElementById('loadingSection');
const previewSection = document.getElementById('previewSection');
const errorSection = document.getElementById('errorSection');

const topicInput = document.getElementById('topic');
const numSlidesInput = document.getElementById('numSlides');
const submitBtn = document.getElementById('submitBtn');

const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');

const previewTopic = document.getElementById('previewTopic');
const previewSlideCount = document.getElementById('previewSlideCount');
const slidesPreview = document.getElementById('slidesPreview');

const downloadBtn = document.getElementById('downloadBtn');
const createNewBtn = document.getElementById('createNewBtn');
const tryAgainBtn = document.getElementById('tryAgainBtn');

const errorMessage = document.getElementById('errorMessage');

// Global variables
let currentFilename = null;
let progressInterval = null;

// Form submission
presentationForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const topic = topicInput.value.trim();
    const numSlides = parseInt(numSlidesInput.value);
    
    // Validation
    if (!topic) {
        showError('Please enter a presentation topic');
        return;
    }
    
    if (numSlides < 3 || numSlides > 10) {
        showError('Number of slides must be between 3 and 10');
        return;
    }
    
    // Start presentation creation
    createPresentation(topic, numSlides);
});

// Create presentation function
async function createPresentation(topic, numSlides) {
    // Show loading section
    formSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    previewSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    
    // Animate progress steps
    animateProgressSteps();
    
    try {
        const response = await fetch('/api/create-presentation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                topic: topic,
                num_slides: numSlides
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create presentation');
        }
        
        // Stop progress animation
        if (progressInterval) {
            clearInterval(progressInterval);
        }
        
        // Show preview
        currentFilename = data.filename;
        showPreview(topic, data.slides);
        
    } catch (error) {
        console.error('Error:', error);
        
        // Stop progress animation
        if (progressInterval) {
            clearInterval(progressInterval);
        }
        
        showError(error.message || 'An unexpected error occurred');
    }
}

// Animate progress steps
function animateProgressSteps() {
    let currentStep = 1;
    
    // Reset all steps
    step1.classList.remove('active');
    step2.classList.remove('active');
    step3.classList.remove('active');
    step1.classList.add('active');
    
    progressInterval = setInterval(() => {
        currentStep++;
        
        if (currentStep === 2) {
            step2.classList.add('active');
        } else if (currentStep === 3) {
            step3.classList.add('active');
        } else if (currentStep > 3) {
            // Reset to step 1
            currentStep = 1;
            step1.classList.remove('active');
            step2.classList.remove('active');
            step3.classList.remove('active');
            step1.classList.add('active');
        }
    }, 2000);
}

// Show preview
function showPreview(topic, slides) {
    loadingSection.classList.add('hidden');
    previewSection.classList.remove('hidden');
    
    previewTopic.textContent = topic;
    previewSlideCount.textContent = `${slides.length} slides created`;
    
    // Clear previous slides
    slidesPreview.innerHTML = '';
    
    // Add each slide to preview
    slides.forEach((slide, index) => {
        const slideItem = document.createElement('div');
        slideItem.className = 'slide-item';
        
        const slideTitle = document.createElement('h4');
        slideTitle.textContent = `Slide ${index + 1}: ${slide.title}`;
        
        const slideContent = document.createElement('p');
        slideContent.textContent = slide.content;
        
        slideItem.appendChild(slideTitle);
        slideItem.appendChild(slideContent);
        slidesPreview.appendChild(slideItem);
    });
}

// Show error
function showError(message) {
    formSection.classList.add('hidden');
    loadingSection.classList.add('hidden');
    previewSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    
    errorMessage.textContent = message;
}

// Download button handler
downloadBtn.addEventListener('click', () => {
    if (currentFilename) {
        window.location.href = `/api/download/${currentFilename}`;
    }
});

// Create new presentation button handler
createNewBtn.addEventListener('click', () => {
    previewSection.classList.add('hidden');
    formSection.classList.remove('hidden');
    
    // Reset form
    topicInput.value = '';
    numSlidesInput.value = 5;
    currentFilename = null;
});

// Try again button handler
tryAgainBtn.addEventListener('click', () => {
    errorSection.classList.add('hidden');
    formSection.classList.remove('hidden');
});

// Input validation feedback
numSlidesInput.addEventListener('input', (e) => {
    const value = parseInt(e.target.value);
    
    if (value < 3) {
        e.target.value = 3;
    } else if (value > 10) {
        e.target.value = 10;
    }
});
