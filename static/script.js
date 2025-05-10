/**
 * TruthScan - Advanced Fake News Detector
 * Main JavaScript functionality
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - Tabs
    const textTab = document.querySelector('.tool-tab[data-tab="text-tab"]');
    const urlTab = document.querySelector('.tool-tab[data-tab="url-tab"]');
    const textTabContent = document.getElementById('text-tab');
    const urlTabContent = document.getElementById('url-tab');
    
    // DOM Elements - Form
    const articleTextArea = document.getElementById('article-text');
    const articleUrlInput = document.getElementById('article-url');
    const verifyBtn = document.getElementById('verify-btn');
    
    // DOM Elements - Results
    const resultsCard = document.getElementById('results-card');
    const loadingContainer = document.getElementById('loading-container');
    const resultsContent = document.getElementById('results-content');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    
    // DOM Elements - Analysis Results
    const verdictIndicator = document.getElementById('verdict-indicator');
    const verdictIcon = document.getElementById('verdict-icon');
    const verdictText = document.getElementById('verdict-text');
    const confidenceBar = document.getElementById('confidence-bar');
    const confidencePercentage = document.getElementById('confidence-percentage');
    const analysisMessage = document.getElementById('analysis-message');
    const newAnalysisBtn = document.getElementById('new-analysis-btn');
    
    // DOM Elements - Analysis Factors
    const factorSensational = document.getElementById('factor-sensational');
    const factorSources = document.getElementById('factor-sources');
    const factorLength = document.getElementById('factor-length');
    
    // API Configuration
    const API_URL = '/api/verify';
    const TIMEOUT_DURATION = 30000; // 30 seconds
    
    // Initialize Tabs
    function initTabs() {
        textTab.addEventListener('click', () => {
            textTab.classList.add('active');
            urlTab.classList.remove('active');
            textTabContent.classList.remove('d-none');
            urlTabContent.classList.add('d-none');
            articleTextArea.focus();
        });
        
        urlTab.addEventListener('click', () => {
            urlTab.classList.add('active');
            textTab.classList.remove('active');
            urlTabContent.classList.remove('d-none');
            textTabContent.classList.add('d-none');
            articleUrlInput.focus();
        });
    }
    
    // Initialize Smooth Scrolling
    function initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    window.scrollTo({
                        top: target.offsetTop - 80, // Offset for fixed header
                        behavior: 'smooth'
                    });
                }
            });
        });
    }
    
    // Validate Inputs
    function validateInputs() {
        const text = articleTextArea.value.trim();
        const url = articleUrlInput.value.trim();
        
        // Check if at least one input is provided
        if (!text && !url) {
            showError('Please provide either article text or a URL to analyze.');
            return false;
        }
        
        // If URL is provided, validate format
        if (url && !isValidUrl(url)) {
            showError('Please enter a valid URL (e.g., https://example.com/news).');
            return false;
        }
        
        return true;
    }
    
    // Validate URL format
    function isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    // Show Error Message
    function showError(message) {
        resultsCard.style.display = 'block';
        loadingContainer.style.display = 'none';
        resultsContent.style.display = 'none';
        errorContainer.style.display = 'flex';
        errorMessage.textContent = message;
        
        // Scroll to results card
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Show Loading State
    function showLoading() {
        resultsCard.style.display = 'block';
        loadingContainer.style.display = 'flex';
        resultsContent.style.display = 'none';
        errorContainer.style.display = 'none';
        
        // Disable verify button
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Analyzing...';
        
        // Scroll to results card
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Hide Loading State
    function hideLoading() {
        loadingContainer.style.display = 'none';
        
        // Re-enable verify button
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = '<i class="fas fa-microscope me-2"></i>Analyze Content';
    }
    
    // Display Results
    function displayResults(data) {
        // Update verdict based on result
        if (data.result === 'real') {
            verdictIndicator.className = 'verdict-indicator real';
            verdictIcon.className = 'fas fa-check-circle';
            verdictText.textContent = 'This content appears to be real';
            verdictText.className = 'verdict-text text-success';
        } else if (data.result === 'fake') {
            verdictIndicator.className = 'verdict-indicator fake';
            verdictIcon.className = 'fas fa-times-circle';
            verdictText.textContent = 'This content may be fake';
            verdictText.className = 'verdict-text text-danger';
        } else {
            verdictIndicator.className = 'verdict-indicator uncertain';
            verdictIcon.className = 'fas fa-question-circle';
            verdictText.textContent = 'Verification uncertain';
            verdictText.className = 'verdict-text text-warning';
        }
        
        // Update confidence percentage and bar
        const percentage = Math.round(data.confidence * 100);
        confidencePercentage.textContent = `${percentage}%`;
        confidenceBar.style.width = `${percentage}%`;
        
        // Set confidence bar class based on confidence level
        if (percentage >= 70) {
            confidenceBar.className = 'confidence-bar high';
        } else if (percentage >= 50) {
            confidenceBar.className = 'confidence-bar medium';
        } else {
            confidenceBar.className = 'confidence-bar low';
        }
        
        // Set analysis message
        analysisMessage.textContent = data.message || 'No additional details available.';
        
        // Update analysis factors
        updateAnalysisFactors(data);
        
        // Show results content
        resultsContent.style.display = 'block';
        
        // Scroll to results section for better visibility
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Update Analysis Factors
    function updateAnalysisFactors(data) {
        // These values are inferred from the message and confidence
        const isSensational = data.message.toLowerCase().includes('sensational');
        const hasSources = data.message.toLowerCase().includes('sources');
        const isShort = data.message.toLowerCase().includes('short');
        
        // Update sensationalism factor
        const sensationalIcon = factorSensational.querySelector('.factor-indicator i');
        if (isSensational) {
            sensationalIcon.className = 'fas fa-circle-xmark';
            factorSensational.querySelector('.factor-details p').textContent = 'Contains sensational language';
        } else {
            sensationalIcon.className = 'fas fa-circle-check';
            factorSensational.querySelector('.factor-details p').textContent = 'No excessive sensationalism detected';
        }
        
        // Update sources factor
        const sourcesIcon = factorSources.querySelector('.factor-indicator i');
        if (hasSources) {
            sourcesIcon.className = 'fas fa-circle-check';
            factorSources.querySelector('.factor-details p').textContent = 'References to credible sources found';
        } else {
            sourcesIcon.className = 'fas fa-circle-xmark';
            factorSources.querySelector('.factor-details p').textContent = 'No credible source references found';
        }
        
        // Update length factor
        const lengthIcon = factorLength.querySelector('.factor-indicator i');
        if (isShort) {
            lengthIcon.className = 'fas fa-circle-xmark';
            factorLength.querySelector('.factor-details p').textContent = 'Content is too short for thorough analysis';
        } else {
            lengthIcon.className = 'fas fa-circle-check';
            factorLength.querySelector('.factor-details p').textContent = 'Content has sufficient depth';
        }
    }
    
    // Reset Analysis Form
    function resetAnalysisForm() {
        articleTextArea.value = '';
        articleUrlInput.value = '';
        resultsCard.style.display = 'none';
        
        // Reset to text tab
        textTab.click();
        
        // Scroll to tool section
        document.getElementById('tool').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Handle Verification Process
    async function handleVerification() {
        // Validate inputs
        if (!validateInputs()) {
            return;
        }
        
        // Show loading state
        showLoading();
        
        // Prepare request data
        const requestData = {
            text: articleTextArea.value.trim(),
            url: articleUrlInput.value.trim()
        };
        
        // If empty, don't include the field in the payload
        if (!requestData.text) delete requestData.text;
        if (!requestData.url) delete requestData.url;
        
        try {
            // Set up timeout controller
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_DURATION);
            
            // Send API request
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            // Clear timeout
            clearTimeout(timeoutId);
            
            // Handle response
            if (response.ok) {
                const data = await response.json();
                displayResults(data);
            } else {
                const errorData = await response.json();
                showError(errorData.error || 'An error occurred during verification. Please try again.');
            }
        } catch (error) {
            // Handle fetch errors
            if (error.name === 'AbortError') {
                showError('Request timed out. Please try again or use a different article.');
            } else {
                console.error('Error during verification:', error);
                showError('Failed to connect to the verification service. Please try again later.');
            }
        } finally {
            // Hide loading spinner
            hideLoading();
        }
    }
    
    // Initialize the application
    function init() {
        // Initialize tabs
        initTabs();
        
        // Initialize smooth scrolling
        initSmoothScrolling();
        
        // Event Listeners
        verifyBtn.addEventListener('click', handleVerification);
        newAnalysisBtn.addEventListener('click', resetAnalysisForm);
        
        // Handle Enter key press in URL input
        articleUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                verifyBtn.click();
            }
        });
        
        // Focus on text area on page load
        articleTextArea.focus();
    }
    
    // Initialize the app
    init();
});