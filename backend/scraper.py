import logging
import requests
from bs4 import BeautifulSoup
import trafilatura
from typing import Optional

logger = logging.getLogger(__name__)

def extract_text_from_url(url: str) -> Optional[str]:
    """
    Extract the main text content from a URL.
    Uses trafilatura as primary extractor, falls back to BeautifulSoup if needed.
    
    Args:
        url: The URL to extract text from
        
    Returns:
        Extracted text or None if extraction failed
    """
    try:
        # First try using trafilatura which is better at extracting main content
        logger.debug(f"Attempting to extract text from {url} using trafilatura")
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted_text = trafilatura.extract(downloaded)
            if extracted_text:
                logger.debug("Successfully extracted text using trafilatura")
                return extracted_text
        
        # Fallback to BeautifulSoup if trafilatura fails
        logger.debug("Trafilatura extraction failed, falling back to BeautifulSoup")
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
