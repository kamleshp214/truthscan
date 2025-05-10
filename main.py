import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# ---- SCRAPER FUNCTIONS ----

def extract_text_from_url(url: str) -> Optional[str]:
    """
    Extract the main text content from a URL using BeautifulSoup.
    
    Args:
        url: The URL to extract text from
        
    Returns:
        Extracted text or None if extraction failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
            tag.decompose()
        
        # Try to find the main article content
        article = soup.find('article')
        if article:
            paragraphs = article.find_all('p')
        else:
            # If no article tag, look for paragraphs in the body
            paragraphs = soup.find_all('p')
        
        # Extract text from paragraphs
        text = ' '.join([p.get_text().strip() for p in paragraphs])
        
        # Clean up the text - remove extra whitespace
        text = ' '.join(text.split())
        
        if text:
            logger.debug("Successfully extracted text using BeautifulSoup")
            return text
        else:
            logger.warning("Failed to extract meaningful text from the URL")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting text from URL: {str(e)}")
        return None

# ---- DETECTOR FUNCTIONS ----

def is_article_sensational(text: str) -> bool:
    """
    Check if the article text contains sensational language.
    
    Args:
        text: The article text
        
    Returns:
        True if the article appears sensational, False otherwise
    """
    # List of sensational words and phrases
    sensational_words = [
        'shocking', 'incredible', 'unbelievable', 'mind-blowing', 'jaw-dropping',
        'amazing', 'astonishing', 'explosive', 'bombshell', 'scandal', 'scandalous',
        'urgent', 'emergency', 'crisis', 'breaking', 'exclusive', 'viral', 'trending',
        'outrageous', 'controversial', 'secret', 'conspiracy', 'exposed', 'revealed'
    ]
    
    # Count occurrences of sensational words
    text_lower = text.lower()
    sensational_count = sum(1 for word in sensational_words if word in text_lower)
    
    # Check for excessive punctuation (like multiple exclamation marks)
    excessive_punctuation = bool(re.search(r'(!|\?){2,}', text))
    
    # Check for ALL CAPS words (excluding acronyms)
    all_caps_words = len(re.findall(r'\b[A-Z]{4,}\b', text))
    
    # Combine factors to determine if the article is sensational
    return (sensational_count > 3) or excessive_punctuation or (all_caps_words > 5)

def has_reliable_sources(text: str) -> bool:
    """
    Check if the article text mentions reliable sources.
    
    Args:
        text: The article text
        
    Returns:
        True if the article mentions reliable sources, False otherwise
    """
    # List of phrases indicating reliable sourcing
    source_indicators = [
        'according to', 'sources say', 'reported by', 'cited', 'experts say',
        'study shows', 'research indicates', 'official statement', 'confirmed by',
        'verified by', 'press release', 'statement from'
    ]
    
    # Reliable news organizations and institutions
    reliable_sources = [
        'reuters', 'associated press', 'bbc', 'afp', 'pti', 'ani', 'cnn', 
        'al jazeera', 'the hindu', 'dawn', 'the times of india', 'the tribune',
        'hindustan times', 'ndtv', 'india today', 'the express tribune',
        'government of india', 'government of pakistan', 'ministry of', 'university',
        'research institute', 'official', 'authorities'
    ]
    
    text_lower = text.lower()
    
    # Check for source indicators
    has_indicators = any(indicator in text_lower for indicator in source_indicators)
    
    # Check for mentions of reliable sources
    has_sources = any(source in text_lower for source in reliable_sources)
    
    return has_indicators and has_sources

def detect_fake_news(text: str) -> Tuple[str, float, str]:
    """
    Detect fake news using rule-based methods.
    
    Args:
        text: The article text
        
    Returns:
        Tuple of (result, confidence, message)
    """
    # Sanitize input
    if not text or len(text.strip()) < 20:
        return "fake", 0.9, "Text is too short for reliable analysis"
        
    try:
        # Check for sensational language
        sensational = is_article_sensational(text)
        
        # Check for reliable sources
        has_sources = has_reliable_sources(text)
        
        # Check article length (very short articles may be suspicious)
        very_short = len(text.split()) < 100
        
        # Create a simple scoring system
        score = 0.0
        
        if sensational:
            score += 0.4  # Sensational language increases fake probability
        
        if has_sources:
            score -= 0.3  # Citing sources decreases fake probability
        
        if very_short:
            score += 0.2  # Very short content increases fake probability
        
        # Base confidence level
        base_confidence = 0.6
        
        # Determine result and confidence
        if score > 0.2:
            result = "fake"
            confidence = base_confidence + (score * 0.2)  # Boost confidence based on score
            message = "Article contains sensational language and lacks reliable sources"
        elif score < -0.1:
            result = "real"
            confidence = base_confidence + (abs(score) * 0.2)  # Boost confidence based on score
            message = "Article cites reliable sources and uses measured language"
        else:
            result = "uncertain"
            confidence = base_confidence
            message = "Unable to determine authenticity with high confidence"
        
        # Cap confidence at 0.9 for rule-based detection
        confidence = min(0.9, confidence)
        
        # If result is uncertain, lean toward fake but with low confidence
        if result == "uncertain":
            result = "fake"
            confidence = 0.55
            message = "Unable to verify authenticity, exercise caution"
        
        return result, confidence, message
        
    except Exception as e:
        logger.error(f"Error in fake news detection: {str(e)}")
        # In case of any errors, return a safe default
        return "uncertain", 0.5, "Error during analysis, unable to verify"

# ---- ROUTES ----

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

@app.route('/api/verify', methods=['POST'])
def api_verify():
    """API endpoint for verifying news articles"""
    # Get the JSON data from the request
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    try:
        # Process the request
        text = data.get('text')
        url = data.get('url')
        
        # Validate input
        if not text and not url:
            return jsonify({"error": "Please provide valid article text or URL"}), 400
            
        text_to_analyze = text
        
        # If URL is provided, scrape the text
        if url:
            try:
                logger.debug(f"Extracting text from URL: {url}")
                extracted_text = extract_text_from_url(url)
                if not extracted_text and not text_to_analyze:
                    return jsonify({"error": "Could not extract text from the provided URL"}), 400
                
                # If both text and URL are provided, prioritize text from URL
                if extracted_text:
                    text_to_analyze = extracted_text
            except Exception as e:
                logger.error(f"Error extracting text from URL: {str(e)}")
                return jsonify({"error": f"Failed to process the URL: {str(e)}"}), 500
        
        # Detect fake news
        try:
            logger.debug("Analyzing text for fake news detection")
            result, confidence, message = detect_fake_news(text_to_analyze)
            return jsonify({
                "result": result,
                "confidence": confidence,
                "message": message
            })
        except Exception as e:
            logger.error(f"Error during fake news detection: {str(e)}")
            return jsonify({"error": f"Error analyzing text: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in verify endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Serve static files from the static directory
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the static directory"""
    return send_from_directory('static', path)

if __name__ == "__main__":
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
