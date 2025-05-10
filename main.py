import os
import re
import logging
import requests
import json
from bs4 import BeautifulSoup
from typing import Tuple, Optional, Dict, Any, List, Union
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app and configure it
app = Flask(__name__, static_folder='static')
app.config['JSON_SORT_KEYS'] = False  # Preserve order in JSON responses
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Limit request size to 5MB
CORS(app)  # Enable CORS for all routes

# ---- SCRAPER FUNCTIONS ----

def extract_text_from_url(url: str) -> Optional[str]:
    """
    Extract the main text content from a URL using BeautifulSoup.
    Enhanced to handle complex news sites with multiple extraction strategies.
    
    Args:
        url: The URL to extract text from
        
    Returns:
        Extracted text or None if extraction failed
    """
    try:
        # Use a realistic browser user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        logger.info(f"Fetching content from URL: {url}")
        # Fetch the webpage with a timeout
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements that typically contain non-article content
        unwanted_tags = ['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe', 'form', 'noscript']
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Also remove elements with class names that suggest advertisements, menus, etc.
        ad_classes = ['ad', 'ads', 'advertisement', 'banner', 'promo', 'sidebar', 'menu', 'navigation', 'comment']
        for class_name in ad_classes:
            for element in soup.find_all(class_=lambda c: c and class_name in c.lower()):
                element.decompose()
        
        # Strategy 1: Try to find specific article containers
        article_containers = []
        
        # Check for article tag
        article_tag = soup.find('article')
        if article_tag:
            article_containers.append(article_tag)
        
        # Check for common article container classes
        article_classes = ['article', 'post', 'entry', 'news-content', 'story']
        for class_name in article_classes:
            containers = soup.find_all(class_=lambda c: c and class_name in c.lower())
            article_containers.extend(containers)
        
        # Check for common article container IDs
        article_ids = ['article', 'post', 'entry', 'content', 'main-content']
        for id_name in article_ids:
            container = soup.find(id=lambda i: i and id_name in i.lower())
            if container:
                article_containers.append(container)
        
        # Try extracting text from article containers
        extracted_text = ""
        for container in article_containers:
            paragraphs = container.find_all('p')
            if paragraphs:
                container_text = ' '.join([p.get_text().strip() for p in paragraphs])
                if container_text and len(container_text) > len(extracted_text):
                    extracted_text = container_text
        
        # Strategy 2: If no good article containers found, look for all paragraphs in the body
        if not extracted_text or len(extracted_text) < 200:
            all_paragraphs = soup.find_all('p')
            if all_paragraphs:
                body_text = ' '.join([p.get_text().strip() for p in all_paragraphs])
                if len(body_text) > len(extracted_text):
                    extracted_text = body_text
        
        # Strategy 3: If still no good text, try div elements with substantial text content
        if not extracted_text or len(extracted_text) < 200:
            content_divs = []
            for div in soup.find_all('div'):
                if len(div.get_text()) > 500:  # Only divs with substantial text
                    content_divs.append(div)
            
            for div in content_divs:
                div_text = div.get_text(' ', strip=True)
                if len(div_text) > len(extracted_text):
                    extracted_text = div_text
        
        # Clean up the text
        if extracted_text:
            # Remove excessive whitespace and normalize
            extracted_text = ' '.join(extracted_text.split())
            
            # Remove very short lines that might be navigation, ads, etc.
            lines = [line for line in extracted_text.splitlines() if len(line) > 30]
            extracted_text = ' '.join(lines)
            
            # If it's too short, it's probably not useful content
            if len(extracted_text) < 150:
                logger.warning(f"Extracted text is too short ({len(extracted_text)} chars), probably not good content")
                return None
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters of text from URL")
            return extracted_text
        else:
            logger.warning("Failed to extract meaningful text from the URL")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error when fetching URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error when fetching URL: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting text from URL: {str(e)}")
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
    try:
        # Get the JSON data from the request
        data = request.get_json()
        if not data:
            logger.warning("Invalid or missing JSON data in request")
            return jsonify({"error": "Invalid JSON data"}), 400
        
        # Log the request (sanitized to avoid logging potentially large texts)
        has_text = bool(data.get('text'))
        has_url = bool(data.get('url'))
        logger.info(f"Received verification request - has text: {has_text}, has URL: {has_url}")
        
        # Validate that at least one input type is provided
        if not has_text and not has_url:
            logger.warning("Request missing both text and URL")
            return jsonify({"error": "Please provide either article text or a valid URL"}), 400
        
        text_to_analyze = data.get('text', '')
            
        # Process URL if provided
        if has_url:
            url = data.get('url')
            try:
                logger.info(f"Attempting to extract content from URL: {url}")
                extracted_text = extract_text_from_url(url)
                
                if extracted_text:
                    logger.info(f"Successfully extracted text from URL (Length: {len(extracted_text)} chars)")
                    # If we have text from URL, use it (prioritize URL over provided text)
                    text_to_analyze = extracted_text
                    
                elif not text_to_analyze:
                    # We couldn't extract text and there's no direct text provided
                    logger.warning(f"Failed to extract content from URL: {url}")
                    return jsonify({
                        "error": "Could not extract any meaningful text from the provided URL. " +
                                "Please check that the URL points to a valid article, or paste the article text directly."
                    }), 400
            except Exception as e:
                logger.error(f"Error processing URL ({url}): {str(e)}")
                
                if not text_to_analyze:
                    # Only return an error if we have no text to fall back on
                    return jsonify({
                        "error": f"Failed to process the URL. {str(e)}"
                    }), 500
                
                # Otherwise, we'll continue with the provided text
                logger.info("Using provided text instead of URL content due to extraction error")
        
        # Ensure we have something to analyze
        if not text_to_analyze or len(text_to_analyze.strip()) < 20:
            logger.warning("Text too short or empty for analysis")
            return jsonify({
                "error": "The text is too short for meaningful analysis. Please provide a longer article text."
            }), 400
        
        # Run the fake news detection
        try:
            logger.info(f"Analyzing text for fake news detection (Length: {len(text_to_analyze)} chars)")
            result, confidence, message = detect_fake_news(text_to_analyze)
            
            logger.info(f"Analysis complete - Result: {result}, Confidence: {confidence:.2f}")
            return jsonify({
                "result": result,
                "confidence": confidence,
                "message": message
            })
            
        except Exception as e:
            logger.error(f"Error during fake news detection: {str(e)}")
            return jsonify({
                "error": "An error occurred during content analysis. Please try again with a different article."
            }), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in verify endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

# Serve static files from the static directory
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the static directory"""
    return send_from_directory('static', path)

if __name__ == "__main__":
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
