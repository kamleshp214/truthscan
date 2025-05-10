document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const articleTextArea = document.getElementById('article-text');
    const articleUrlInput = document.getElementById('article-url');
    const verifyButton = document.getElementById('verify-btn');
    const resultSection = document.getElementById('result-section');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultContent = document.getElementById('result-content');
    const resultIcon = document.getElementById('result-icon');
    const resultHeading = document.getElementById('result-heading');
    const confidenceBar = document.getElementById('confidence-bar');
    const confidenceText = document.getElementById('confidence-text');
    const resultMessage = document.getElementById('result-message');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const newVerificationBtn = document.getElementById('new-verification-btn');

    // API Configuration
    const API_URL = '/api/verify';
    const TIMEOUT_DURATION = 30000; // 30 seconds

    // Event Listeners
    verifyButton.addEventListener('click', handleVerification);
    newVerificationBtn.addEventListener('click', resetForm);
    
    // Auto-focus on the text area when the page loads
    articleTextArea.focus();

    // Client-side validation
    function validateInputs() {
        const articleText = articleTextArea.value.trim();
        const articleUrl = articleUrlInput.value.trim();
        
        // Check if at least one input is provided
        if (!articleText && !articleUrl) {
            showError('Please provide either article text or a valid URL');
            return false;
        }
        
        // If URL is provided, validate the format
        if (articleUrl) {
            const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
            if (!urlPattern.test(articleUrl)) {
                showError('Please enter a valid URL format (e.g., https://example.com/news)');
                return false;
            }
        }
        
        return true;
    }

    // Handle the verification process
    async function handleVerification() {
        // Reset UI state
        hideError();
        
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
                displayResult(data);
            } else {
                const errorData = await response.json();
                showError(errorData.detail || 'An error occurred during verification');
            }
        } catch (error) {
            // Handle fetch errors
            if (error.name === 'AbortError') {
                showError('Request timed out. Please try again.');
            } else {
                console.error('Error during verification:', error);
                showError('Failed to connect to the verification service. Please try again later.');
            }
        } finally {
            // Hide loading spinner
            hideLoading();
        }
    }

    // Display the verification result
    function displayResult(data) {
        // Set icon and heading based on result
        if (data.result === 'real') {
            resultIcon.className = 'result-icon real';
            resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
            resultHeading.textContent = 'This news is likely real';
            resultHeading.style.color = 'var(--success-color)';
        } else {
            resultIcon.className = 'result-icon fake';
            resultIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
            resultHeading.textContent = 'This news is likely fake';
            resultHeading.style.color = 'var(--danger-color)';
        }
        
        // Set confidence bar
        const confidencePercentage = Math.round(data.confidence * 100);
        confidenceBar.style.width = `${confidencePercentage}%`;
        confidenceText.textContent = `Confidence: ${confidencePercentage}%`;
        
        // Set confidence bar color based on confidence level
        if (confidencePercentage >= 70) {
            confidenceBar.className = 'confidence-bar high-confidence';
        } else if (confidencePercentage <= 40) {
            confidenceBar.className = 'confidence-bar low-confidence';
        } else {
            confidenceBar.className = 'confidence-bar';
        }
        
        // Set explanation message
        resultMessage.textContent = data.message || 'No additional details available.';
        
        // Show result content
        resultContent.style.display = 'block';
    }

    // Show loading spinner
    function showLoading() {
        resultSection.style.display = 'block';
        loadingSpinner.style.display = 'flex';
        resultContent.style.display = 'none';
        errorMessage.style.display = 'none';
        
        // Disable verify button during loading
        verifyButton.disabled = true;
        verifyButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
    }

    // Hide loading spinner
    function hideLoading() {
        loadingSpinner.style.display = 'none';
        
        // Re-enable verify button
        verifyButton.disabled = false;
        verifyButton.innerHTML = '<i class="fas fa-check-circle"></i> Verify';
    }

    // Show error message
    function showError(message) {
        resultSection.style.display = 'block';
        errorMessage.style.display = 'flex';
        errorText.textContent = message;
        loadingSpinner.style.display = 'none';
        resultContent.style.display = 'none';
    }

    // Hide error message
    function hideError() {
        errorMessage.style.display = 'none';
    }

    // Reset the form for a new verification
    function resetForm() {
        articleTextArea.value = '';
        articleUrlInput.value = '';
        resultSection.style.display = 'none';
        articleTextArea.focus();
    }
    
    // Handle Enter key press in URL input field
    articleUrlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent default form submission
            verifyButton.click();
        }
    });
    
    // Add character counter for text area
    articleTextArea.addEventListener('input', () => {
        const currentLength = articleTextArea.value.length;
        
        // If text is getting long, show a warning about potentially slow processing
        if (currentLength > 5000) {
            const warningElement = document.getElementById('length-warning') || document.createElement('div');
            warningElement.id = 'length-warning';
            warningElement.className = 'error-message';
            warningElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i><p>Long text may take longer to process</p>';
            
            if (!document.getElementById('length-warning')) {
                articleTextArea.parentNode.appendChild(warningElement);
            }
        } else {
            const existingWarning = document.getElementById('length-warning');
            if (existingWarning) {
                existingWarning.remove();
            }
        }
    });
});
