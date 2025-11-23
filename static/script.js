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
const languageSelect = document.getElementById('languageSelect');
const themeSelect = document.getElementById('themeSelect');
const htmlRoot = document.getElementById('htmlRoot');

// Global variables
let currentFilename = null;
let progressInterval = null;
let currentLanguage = 'en';
let currentTheme = 'light';

// Language management
function initLanguage() {
    // Load saved language from localStorage or use browser language
    const savedLang = localStorage.getItem('preferredLanguage');
    const browserLang = navigator.language.split('-')[0];
    
    // Check if browser language is supported
    const supportedLangs = ['en', 'es', 'ru', 'zh', 'fr'];
    const defaultLang = supportedLangs.includes(browserLang) ? browserLang : 'en';
    
    currentLanguage = savedLang || defaultLang;
    languageSelect.value = currentLanguage;
    applyTranslations(currentLanguage);
}

function applyTranslations(lang) {
    currentLanguage = lang;
    htmlRoot.setAttribute('lang', lang);
    
    const t = translations[lang];
    
    // Apply translations to all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (t[key]) {
            element.textContent = t[key];
        }
    });
    
    // Apply placeholder translations
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        if (t[key]) {
            element.placeholder = t[key];
        }
    });
    
    // Update theme names in dropdown
    updateThemeDropdown(lang);
    
    // Save to localStorage
    localStorage.setItem('preferredLanguage', lang);
}

function updateThemeDropdown(lang) {
    const themeOptions = themeSelect.querySelectorAll('option');
    themeOptions.forEach(option => {
        const themeKey = option.value;
        if (themeNames[lang] && themeNames[lang][themeKey]) {
            option.textContent = themeNames[lang][themeKey];
        }
    });
}

function t(key) {
    return translations[currentLanguage][key] || key;
}

// Language selector event
languageSelect.addEventListener('change', (e) => {
    applyTranslations(e.target.value);
});

// Initialize language on page load
initLanguage();

// Theme management
function initTheme() {
    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('preferredTheme');
    
    currentTheme = savedTheme || 'light';
    themeSelect.value = currentTheme;
    applyTheme(currentTheme);
}

function applyTheme(themeName) {
    currentTheme = themeName;
    
    const theme = themes[themeName];
    if (!theme) return;
    
    const root = document.documentElement;
    
    // Apply all color variables
    Object.keys(theme.colors).forEach(key => {
        const cssVar = `--color-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
        root.style.setProperty(cssVar, theme.colors[key]);
    });
    
    // Apply special effects if they exist
    if (theme.special) {
        Object.keys(theme.special).forEach(key => {
            const cssVar = `--${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
            root.style.setProperty(cssVar, theme.special[key]);
        });
    }
    
    // Save to localStorage
    localStorage.setItem('preferredTheme', themeName);
}

// Theme selector event
themeSelect.addEventListener('change', (e) => {
    applyTheme(e.target.value);
});

// Initialize theme on page load
initTheme();

// Form submission
presentationForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const topic = topicInput.value.trim();
    const numSlides = parseInt(numSlidesInput.value);
    
    // Validation
    if (!topic) {
        showError(t('errorTopicRequired'));
        return;
    }
    
    if (numSlides < 3 || numSlides > 10) {
        showError(t('errorSlidesRange'));
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
        
        showError(error.message || t('errorUnexpected'));
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
    previewSlideCount.textContent = `${slides.length} ${t('slideCount')}`;
    
    // Clear previous slides
    slidesPreview.innerHTML = '';
    
    // Add each slide to preview
    slides.forEach((slide, index) => {
        const slideItem = document.createElement('div');
        slideItem.className = 'slide-item';
        
        const slideTitle = document.createElement('h4');
        slideTitle.textContent = `${t('slidePrefix')} ${index + 1}: ${slide.title}`;
        
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
