// DOM Elements
let presentationForm;
let formSection;
let loadingSection;
let previewSection;
let errorSection;

let topicInput;
let numSlidesInput;
let submitBtn;

let step1;
let step2;
let step3;

let previewTopic;
let previewSlideCount;
let slidesPreview;

let downloadBtn;
let createNewBtn;
let tryAgainBtn;

let errorMessage;
let languageSelect;
let htmlRoot;

// Global variables
let currentFilename = null;
let progressInterval = null;
let currentLanguage = 'en';

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
    if (htmlRoot) {
        htmlRoot.setAttribute('lang', lang);
    }
    
    const t = translations[lang];
    if (!t) {
        console.error('Translations not found for language:', lang);
        return;
    }
    
    // Apply translations to all elements with data-i18n attribute
    const i18nElements = document.querySelectorAll('[data-i18n]');
    if (i18nElements) {
        i18nElements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (t[key]) {
                element.textContent = t[key];
            }
        });
    }
    
    // Apply placeholder translations
    const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
    if (placeholderElements) {
        placeholderElements.forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            if (t[key]) {
                element.placeholder = t[key];
            }
        });
    }
    
    // Update presentation theme names in dropdown
    updatePresentationThemeDropdown(lang);
    
    // Update presentation type names in dropdown
    updatePresentationTypeDropdown(lang);
    
    // Save to localStorage
    localStorage.setItem('preferredLanguage', lang);
}

function updatePresentationThemeDropdown(lang) {
    const presentationThemeSelect = document.getElementById('presentationTheme');
    if (!presentationThemeSelect) {
        return;
    }
    
    const themeOptions = presentationThemeSelect.querySelectorAll('option');
    if (!themeOptions || themeOptions.length === 0) {
        return;
    }
    
    themeOptions.forEach(option => {
        const themeKey = option.value;
        if (themeNames[lang] && themeNames[lang][themeKey]) {
            option.textContent = themeNames[lang][themeKey];
        }
    });
}

function updatePresentationTypeDropdown(lang) {
    const presentationTypeSelect = document.getElementById('presentationType');
    if (!presentationTypeSelect) {
        return;
    }
    
    const typeOptions = presentationTypeSelect.querySelectorAll('option');
    if (!typeOptions || typeOptions.length === 0) {
        return;
    }
    
    typeOptions.forEach(option => {
        const typeKey = option.value;
        if (presentationTypeNames[lang] && presentationTypeNames[lang][typeKey]) {
            option.textContent = presentationTypeNames[lang][typeKey];
        }
    });
}

function t(key) {
    return translations[currentLanguage][key] || key;
}

// Language selector event
function initEventListeners() {
    if (languageSelect) {
        languageSelect.addEventListener('change', (e) => {
            applyTranslations(e.target.value);
        });
    }

    // Form submission
    if (presentationForm) {
        presentationForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const topic = topicInput.value.trim();
            const numSlides = parseInt(numSlidesInput.value);
            const presentationTheme = document.getElementById('presentationTheme').value;
            const presentationType = document.getElementById('presentationType').value;
            
            // Validation
            if (!topic) {
                showError(t('errorTopicRequired'));
                return;
            }
            
            if (numSlides < 3 || numSlides > 10 || isNaN(numSlides)) {
                showError(t('errorSlidesRange'));
                return;
            }
            
            // Start presentation creation
            createPresentation(topic, numSlides, presentationTheme, presentationType);
        });
    }

    // Download button handler
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            if (currentFilename) {
                window.location.href = `/api/download/${currentFilename}`;
            }
        });
    }

    // Create new presentation button handler
    if (createNewBtn) {
        createNewBtn.addEventListener('click', () => {
            previewSection.classList.add('hidden');
            formSection.classList.remove('hidden');
            
            // Reset form
            topicInput.value = '';
            numSlidesInput.value = 5;
            currentFilename = null;
        });
    }

    // Try again button handler
    if (tryAgainBtn) {
        tryAgainBtn.addEventListener('click', () => {
            errorSection.classList.add('hidden');
            formSection.classList.remove('hidden');
        });
    }

    // Input validation feedback
    if (numSlidesInput) {
        numSlidesInput.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            if (value < 3 || value > 10) {
                e.target.style.borderColor = 'var(--color-error)';
            } else {
                e.target.style.borderColor = '';
            }
        });
    }
}

// Create presentation function
async function createPresentation(topic, numSlides, theme, presentationType) {
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
                num_slides: numSlides,
                language: currentLanguage,  // Send selected language to backend
                theme: theme,  // Send selected presentation theme to backend
                presentation_type: presentationType  // Send presentation type
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
        showPreview(topic, data.slides, data.presentation_type);
        
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

// Simple Markdown renderer for **bold** with HTML escaping
function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function renderMarkdown(str) {
    const safe = escapeHtml(str);
    return safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

// Show preview
function showPreview(topic, slides, presentationType) {
    loadingSection.classList.add('hidden');
    previewSection.classList.remove('hidden');
    
    previewTopic.textContent = topic;
    
    // Add presentation type info if available
    let slideCountText = `${slides.length} ${t('slideCount')}`;
    if (presentationType && presentationTypeNames[currentLanguage]) {
        const typeName = presentationTypeNames[currentLanguage][presentationType];
        if (typeName) {
            slideCountText += ` • ${typeName}`;
        }
    }
    previewSlideCount.textContent = slideCountText;
    
    // Clear previous slides
    slidesPreview.innerHTML = '';
    
    // Add each slide to preview
    slides.forEach((slide, index) => {
        const slideItem = document.createElement('div');
        slideItem.className = 'slide-item';
        
        const slideTitle = document.createElement('h4');
        slideTitle.textContent = `${t('slidePrefix')} ${index + 1}: ${slide.title}`;
        
        const slideContent = document.createElement('p');
        let content = slide.content;
        
        // Limit content length to 300 characters
        const MAX_CONTENT_LENGTH = 300;
        if (content.length > MAX_CONTENT_LENGTH) {
            content = content.substring(0, MAX_CONTENT_LENGTH) + '...';
            
            // Add warning indicator
            const warningText = document.createElement('small');
            warningText.style.color = 'var(--color-error)';
            warningText.style.display = 'block';
            warningText.style.marginTop = '5px';
            warningText.textContent = '⚠️ Content truncated for display';
            slideItem.appendChild(warningText);
        }
        
        // Render content with basic markdown (bold)
        slideContent.innerHTML = renderMarkdown(content);
        
        // Dynamic font size adjustment based on content length
        if (content.length > 200) {
            slideContent.style.fontSize = '0.9em';
        } else if (content.length > 150) {
            slideContent.style.fontSize = '0.95em';
        }
        
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

// Initialize DOM elements
function initDOMElements() {
    presentationForm = document.getElementById('presentationForm');
    formSection = document.getElementById('formSection');
    loadingSection = document.getElementById('loadingSection');
    previewSection = document.getElementById('previewSection');
    errorSection = document.getElementById('errorSection');

    topicInput = document.getElementById('topic');
    numSlidesInput = document.getElementById('numSlides');
    submitBtn = document.getElementById('submitBtn');

    step1 = document.getElementById('step1');
    step2 = document.getElementById('step2');
    step3 = document.getElementById('step3');

    previewTopic = document.getElementById('previewTopic');
    previewSlideCount = document.getElementById('previewSlideCount');
    slidesPreview = document.getElementById('slidesPreview');

    downloadBtn = document.getElementById('downloadBtn');
    createNewBtn = document.getElementById('createNewBtn');
    tryAgainBtn = document.getElementById('tryAgainBtn');

    errorMessage = document.getElementById('errorMessage');
    languageSelect = document.getElementById('languageSelect');
    htmlRoot = document.getElementById('htmlRoot');
}

// Initialize application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initDOMElements();
        initLanguage();
        initEventListeners();
    });
} else {
    // DOM already loaded
    initDOMElements();
    initLanguage();
    initEventListeners();
}
