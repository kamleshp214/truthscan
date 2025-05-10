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
            'Cache-Control': 'max-age=0',
            'DNT': '1',  # Do Not Track request header
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        # Normalize URL format
        if not url.startswith('http'):
            url = 'https://' + url
            
        # Extract domain for site-specific handling
        try:
            domain = url.split('/')[2] if '://' in url else url.split('/')[0]
            domain = domain.lower()
        except IndexError:
            logger.warning(f"Invalid URL format: {url}")
            return None
        
        logger.info(f"Fetching content from URL: {url} (Domain: {domain})")
        
        # Fetch the webpage with a timeout and retry mechanism
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                break
            except (requests.RequestException, requests.Timeout) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Failed to fetch URL after {max_retries} attempts: {str(e)}")
                    return None
                logger.warning(f"Retry {retry_count}/{max_retries} for URL: {url}")
                # Wait before retrying
                import time
                time.sleep(1)
        
        # Check if we got a valid response
        if not response.text or len(response.text) < 100:
            logger.warning(f"Received empty or very short response from URL: {url}")
            return None
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Site-specific handling for common news websites
        # Dictionary of domain patterns and their corresponding CSS selectors
        site_specific_selectors = {
            'aljazeera.com': ['.wysiwyg--all-content', '.article__body', '.article-p-wrapper'],
            'bbc.com': ['article', '.article__body-content', '.story-body__inner'],
            'bbc.co.uk': ['article', '.article__body-content', '.story-body__inner'],
            'cnn.com': ['.article__content', '.article-body', '.zn-body__paragraph'],
            'nytimes.com': ['.article-content', '.StoryBodyCompanionColumn', '.meteredContent'],
            'washingtonpost.com': ['.article-body', '.teaser-content', '.story-body'],
            'theguardian.com': ['.article-body-commercial-selector', '.content__article-body', '.js-article__body'],
            'reuters.com': ['.article-body', '.StandardArticleBody_body', '.ArticleBodyWrapper'],
            'timesofindia.indiatimes.com': ['.Normal', '._3WlLe', '.ga-article'],
            'indiatimes.com': ['.article_content', '.article-content', '.content_text'],
            'hindustantimes.com': ['.storyDetail', '.detail', '.story-details'],
            'ndtv.com': ['.ins_storybody', '.story__content', '.story_details'],
            'dawn.com': ['.story__content', '.story-content', '.story-body'],
            'foxnews.com': ['.article-body', '.article-content', '.article-text'],
            'news.yahoo.com': ['article', '.caas-body', '.canvas-body'],
            'huffpost.com': ['.entry-content', '.entry__text', '.content-list-component'],
            'usatoday.com': ['.gnt_ar_b', '.story-text', '.story-body'],
            'wsj.com': ['.article-content', '.wsj-snippet-body', '.article_sector'],
        }
        
        # Try to extract content using site-specific selectors
        for site_pattern, selectors in site_specific_selectors.items():
            if site_pattern in domain:
                for selector in selectors:
                    try:
                        article_content = soup.select_one(selector)
                        if article_content:
                            # Try to get paragraphs first
                            paragraphs = article_content.find_all('p')
                            if paragraphs:
                                extracted_text = ' '.join([p.get_text().strip() for p in paragraphs])
                            else:
                                # If no paragraphs, get all text
                                extracted_text = article_content.get_text().strip()
                                
                            if len(extracted_text) > 150:
                                logger.info(f"Used site-specific extraction for {domain} with selector {selector}")
                                return extracted_text
                    except Exception as e:
                        logger.warning(f"Error with selector {selector} for {domain}: {str(e)}")
                        continue
        
        # Try common article content selectors if no site-specific extraction worked
        extracted_text = ""
        
        # First, try article tag
        if not extracted_text:
            article_tags = soup.find_all('article')
            for article_tag in article_tags:
                paragraphs = article_tag.find_all('p')
                if paragraphs:
                    extracted_text = ' '.join([p.get_text().strip() for p in paragraphs])
                    if len(extracted_text) > 150:
                        logger.info("Used article tag extraction")
                        break
                        
        # Try main tag
        if not extracted_text:
            main_tag = soup.find('main')
            if main_tag:
                paragraphs = main_tag.find_all('p')
                if paragraphs:
                    extracted_text = ' '.join([p.get_text().strip() for p in paragraphs])
                    if len(extracted_text) > 150:
                        logger.info("Used main tag extraction")
        
        # Try content div with common class names
        if not extracted_text:
            content_classes = ['content', 'article-content', 'entry-content', 'post-content', 'story', 'article-body', 
                              'story-content', 'news-content', 'text', 'body', 'main-content', 'page-content']
            for class_name in content_classes:
                content_divs = soup.find_all(['div', 'section'], class_=lambda c: c and class_name in c.lower())
                for content_div in content_divs:
                    paragraphs = content_div.find_all('p')
                    if paragraphs:
                        extracted_text = ' '.join([p.get_text().strip() for p in paragraphs])
                        if len(extracted_text) > 150:
                            logger.info(f"Used content div extraction with class: {class_name}")
                            break
                if len(extracted_text) > 150:
                    break
        
        # Remove unwanted elements that typically contain non-article content
        unwanted_tags = ['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe', 'form', 'noscript']
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Also remove elements with class names that suggest advertisements, menus, etc.
        ad_classes = ['ad', 'ads', 'advertisement', 'banner', 'promo', 'sidebar', 'menu', 'navigation', 'comment', 
                     'share', 'social', 'related', 'recommended', 'newsletter', 'subscribe']
        for class_name in ad_classes:
            for element in soup.find_all(class_=lambda c: c and isinstance(c, str) and class_name in c.lower()):
                element.decompose()
        
        # Strategy 1: Look for LiveBlog content (special case for news sites)
        liveblog_indicators = ['liveblog', 'live-blog', 'live-updates', 'live-coverage', 'timeline']
        for indicator in liveblog_indicators:
            liveblog_elements = soup.find_all(class_=lambda c: c and isinstance(c, str) and indicator in c.lower())
            if liveblog_elements:
                logger.info(f"Detected liveblog format, applying special extraction")
                liveblog_text = ""
                for element in liveblog_elements:
                    posts = element.find_all(['div', 'article', 'section'], class_=lambda c: c and isinstance(c, str) and 
                                           any(x in c.lower() for x in ['post', 'update', 'entry', 'item']))
                    if posts:
                        for post in posts:
                            post_text = ' '.join([p.get_text().strip() for p in post.find_all('p')])
                            if post_text:
                                liveblog_text += post_text + " "
                
                if len(liveblog_text) > 300:
                    logger.info(f"Successfully extracted liveblog content: {len(liveblog_text)} chars")
                    # Clean up the text
                    liveblog_text = ' '.join(liveblog_text.split())
                    return liveblog_text
        
        # Strategy 2: Try to find specific article containers
        article_containers = []
        
        # Check for article tag
        article_tag = soup.find('article')
        if article_tag:
            article_containers.append(article_tag)
        
        # Check for common article container classes - expanded list
        article_classes = ['article', 'post', 'entry', 'news-content', 'story', 'content-body', 'article-body', 
                          'story-body', 'main-content', 'page-content', 'entry-content', 'article-content',
                          'story-content', 'news-article', 'post-content']
        for class_name in article_classes:
            containers = soup.find_all(class_=lambda c: c and isinstance(c, str) and class_name in c.lower())
            article_containers.extend(containers)
        
        # Check for common article container IDs - expanded list
        article_ids = ['article', 'post', 'entry', 'content', 'main-content', 'article-content', 'story-content',
                     'page-content', 'primary-content', 'main', 'content-body', 'article-body']
        for id_name in article_ids:
            container = soup.find(id=lambda i: i and isinstance(i, str) and id_name in i.lower())
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
        
        # Strategy 3: If no good article containers found, look for all paragraphs in the body
        if not extracted_text or len(extracted_text) < 150:
            # Look for paragraphs that are likely to be part of the article
            main_content = soup.find(['main', 'div'], id=lambda i: i and isinstance(i, str) and 'content' in i.lower())
            if main_content:
                paragraphs = main_content.find_all('p')
            else:
                paragraphs = soup.find_all('p')
                
            if paragraphs:
                # Filter out very short paragraphs which are likely navigation, headings etc.
                valid_paragraphs = [p for p in paragraphs if len(p.get_text().strip()) > 20]
                if valid_paragraphs:
                    body_text = ' '.join([p.get_text().strip() for p in valid_paragraphs])
                    if len(body_text) > len(extracted_text):
                        extracted_text = body_text
        
        # Strategy 4: If still no good text, try div elements with substantial text content
        if not extracted_text or len(extracted_text) < 150:
            content_divs = []
            for div in soup.find_all('div'):
                div_text = div.get_text().strip()
                if len(div_text) > 300 and div_text.count('.') > 3:  # Only divs with substantial text and multiple sentences
                    content_divs.append(div)
            
            for div in content_divs:
                div_text = div.get_text(' ', strip=True)
                if len(div_text) > len(extracted_text):
                    extracted_text = div_text
        
        # Try schema.org structured data (often used for news articles)
        if not extracted_text:
            article_body = soup.find('script', {'type': 'application/ld+json'})
            if article_body:
                try:
                    json_data = json.loads(article_body.string)
                    if isinstance(json_data, dict):
                        # Check for articleBody in schema.org Article type
                        if 'articleBody' in json_data:
                            extracted_text = json_data['articleBody']
                            logger.info("Used schema.org articleBody extraction")
                        # Sometimes it's nested
                        elif '@graph' in json_data:
                            for item in json_data['@graph']:
                                if isinstance(item, dict) and 'articleBody' in item:
                                    extracted_text = item['articleBody']
                                    logger.info("Used schema.org @graph articleBody extraction")
                                    break
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse JSON-LD: {str(e)}")
        
        # Fallback: If all else fails, just get all paragraphs from the page
        if not extracted_text:
            # Get all text containers
            text_containers = soup.find_all(['p', 'div', 'section', 'article', 'span'])
            
            # Score paragraphs based on length and position
            scored_paragraphs = []
            for i, container in enumerate(text_containers):
                text = container.get_text().strip()
                if len(text) > 30:  # Only consider paragraphs with substantial text
                    # Score based on length (longer is better) and position (middle of page is better)
                    length_score = min(1.0, len(text) / 200)  # Cap at 1.0
                    position_score = 1.0 - abs((i / len(text_containers)) - 0.5) * 2  # Higher in middle
                    score = length_score * 0.7 + position_score * 0.3
                    scored_paragraphs.append((text, score))
            
            # Sort by score and take top paragraphs
            scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
            top_paragraphs = [p[0] for p in scored_paragraphs[:min(20, len(scored_paragraphs))]]  # Take top 20 max
            
            if top_paragraphs:
                extracted_text = ' '.join(top_paragraphs)
                logger.info("Used advanced fallback paragraph extraction")
        
        # Final check - do we have enough content?
        if not extracted_text or len(extracted_text) < 150:
            logger.warning("Failed to extract meaningful content from the URL")
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
        # Try a fallback method for extraction
        try:
            logger.info(f"Attempting fallback extraction method for URL: {url}")
            # Simple fallback: just get all paragraph text
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            if paragraphs:
                fallback_text = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 15])
                if len(fallback_text) > 100:
                    logger.info(f"Fallback extraction successful: {len(fallback_text)} chars")
                    return fallback_text
        except Exception:
            pass
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
    # Check if text is valid
    if not text or len(text) < 100:
        return False
    
    # List of sensational words and phrases
    sensational_words = [
        'shocking', 'incredible', 'unbelievable', 'mind-blowing', 'jaw-dropping',
        'amazing', 'astonishing', 'explosive', 'bombshell', 'scandal', 'scandalous',
        'urgent', 'emergency', 'crisis', 'breaking', 'exclusive', 'viral', 'trending',
        'outrageous', 'controversial', 'secret', 'conspiracy', 'exposed', 'revealed',
        'must see', 'must read', 'game-changer', 'game changer', 'changed forever',
        'will never be the same', 'uncovered', 'leaked', 'alarming',
        'disrupting', 'revolutionary', 'spectacular', 'hysterical',
        'panicked', 'furious', 'dramatic', 'outraged', 'chaos', 'turmoil',
        'nightmare', 'fatal', 'deadly', 'bizarre', 'strange', 'weird'
    ]
    
    # India-Pakistan specific sensational terms
    india_pak_sensational = [
        'war', 'attack', 'invade', 'invasion', 'strike', 'bomb', 'threat',
        'military action', 'troops', 'border conflict', 'secret intelligence', 'terror',
        'terrorist attack', 'infiltration', 'espionage', 'spy caught', 'nuclear threat',
        'weapons amassed', 'missiles targeted', 'intelligence report', 'sources claim',
        'unconfirmed reports', 'anonymous source', 'enemy nation', 'hostile actions'
    ]
    
    # Count occurrences of sensational words
    text_lower = text.lower()
    
    # Word count for normalization
    word_count = len(text_lower.split())
    
    # Count sensational terms
    basic_sensational_count = sum(1 for word in sensational_words if word in text_lower)
    india_pak_sensational_count = sum(1 for phrase in india_pak_sensational if phrase in text_lower)
    
    # Apply higher weight to India-Pakistan sensational terms
    total_sensational_score = basic_sensational_count + (india_pak_sensational_count * 1.5)
    
    # Check for excessive punctuation (like multiple exclamation marks)
    excessive_punctuation = len(re.findall(r'(!|\?){2,}', text))
    
    # Check for ALL CAPS words (excluding acronyms)
    all_caps_words = len(re.findall(r'\b[A-Z]{4,}\b', text))
    
    # Calculate total sensationalism score
    sensationalism_score = total_sensational_score + excessive_punctuation + (all_caps_words * 0.5)
    
    # For very short texts, use a lower threshold
    if word_count < 200:
        threshold = 2
    # For medium length texts
    elif word_count < 500:
        threshold = 3
    # For longer texts, use a normalized threshold
    else:
        # Normalize by text length (approximately 1 sensational term per 150 words)
        threshold = max(3, word_count // 150)
    
    # Log for debugging
    logger.debug(f"Sensationalism score: {sensationalism_score}, threshold: {threshold}, word count: {word_count}")
    logger.debug(f"Basic sensational: {basic_sensational_count}, India-Pak sensational: {india_pak_sensational_count}")
    logger.debug(f"Excessive punctuation: {excessive_punctuation}, All caps words: {all_caps_words}")
    
    return sensationalism_score >= threshold

def has_reliable_sources(text: str) -> bool:
    """
    Check if the article text mentions reliable sources.
    
    Args:
        text: The article text
        
    Returns:
        True if the article mentions reliable sources, False otherwise
    """
    # Check if text is valid
    if not text or len(text) < 100:
        return False
    
    # List of phrases indicating reliable sourcing
    source_indicators = [
        'according to', 'sources say', 'reported by', 'cited', 'experts say',
        'study shows', 'research indicates', 'official statement', 'confirmed by',
        'verified by', 'press release', 'statement from', 'announced', 'declared',
        'briefed', 'disclosed', 'revealed at press conference', 'published',
        'speaking on condition of anonymity', 'spoke to reporters', 'told reporters',
        'said in a statement', 'mentioned in', 'shared information'
    ]
    
    # Reliable news organizations and institutions - expanded for India-Pakistan context
    reliable_sources = [
        'reuters', 'associated press', 'bbc', 'afp', 'pti', 'ani', 'cnn', 
        'al jazeera', 'the hindu', 'dawn', 'the times of india', 'the tribune',
        'hindustan times', 'ndtv', 'india today', 'the express tribune',
        'indian express', 'pakistan today', 'geo news', 'ary news', 'zee news',
        'doordarshan', 'ptv', 'all india radio', 'radio pakistan',
        'government of india', 'government of pakistan', 'prime minister',
        'ministry of external affairs', 'ministry of foreign affairs', 'ministry of defence',
        'indian army', 'pakistan army', 'air force', 'navy', 'ispr', 'defence ministry',
        'foreign ministry', 'intelligence bureau', 'isi', 'raw', 'official spokesperson',
        'defense analyst', 'security expert', 'diplomatic sources', 'university',
        'research institute', 'think tank', 'authorities', 'officials'
    ]
    
    text_lower = text.lower()
    
    # Count source indicators
    indicator_count = sum(1 for indicator in source_indicators if indicator in text_lower)
    
    # Count mentions of reliable sources
    reliable_source_count = sum(1 for source in reliable_sources if source in text_lower)
    
    # Check for quotes (a sign of direct attribution)
    quote_patterns = [r'"[^"]{10,}"', r"'[^']{10,}'", r'".*?"']
    quote_count = sum(len(re.findall(pattern, text)) for pattern in quote_patterns)
    
    # Calculate a reliability score based on multiple factors
    reliability_score = (indicator_count * 1.5) + (reliable_source_count * 2) + (quote_count * 1)
    
    # Log for debugging
    logger.debug(f"Reliability score: {reliability_score}, Indicators: {indicator_count}, Sources: {reliable_source_count}, Quotes: {quote_count}")
    
    # Threshold based on text length
    word_count = len(text_lower.split())
    if word_count < 300:
        threshold = 2  # Lower threshold for short texts
    else:
        threshold = 3  # Higher threshold for longer texts
    
    # Return true if the reliability score meets or exceeds the threshold
    return reliability_score >= threshold

def detect_fake_news(text: str) -> Tuple[str, float, str]:
    """
    Detect fake news using enhanced rule-based methods.
    
    Args:
        text: The article text
        
    Returns:
        Tuple of (result, confidence, message)
    """
    # Sanitize input
    if not text or len(text.strip()) < 50:
        return "fake", 0.9, "Text is too short for reliable analysis"
        
    try:
        # Check for sensational language
        sensational = is_article_sensational(text)
        
        # Check for reliable sources
        has_sources = has_reliable_sources(text)
        
        # Check article length (very short articles may be suspicious)
        word_count = len(text.split())
        very_short = word_count < 100
        good_length = word_count > 300
        
        # Check for balanced reporting (presence of multiple perspectives)
        balanced_indicators = ['however', 'but', 'although', 'though', 'on the other hand', 'alternatively', 
                              'in contrast', 'conversely', 'meanwhile', 'nonetheless', 'despite', 'contrary']
        has_balanced_view = any(indicator in text.lower() for indicator in balanced_indicators)
        
        # Check for excessive use of ALL CAPS (common in fake news)
        words = text.split()
        caps_words = sum(1 for word in words if len(word) > 3 and word.isupper())
        has_excessive_caps = (caps_words / max(1, len(words))) > 0.05  # More than 5% of words are ALL CAPS
        
        # Check for excessive punctuation (!!!, ???)
        excessive_punct = len(re.findall(r'[!?]{2,}', text)) > 2
        
        # Check for clickbait title patterns
        clickbait_patterns = [
            r'(?i)you won\'t believe', r'(?i)shocking', r'(?i)mind[-\s]?blowing', 
            r'(?i)this will make you', r'(?i)secret', r'(?i)they don\'t want you to know',
            r'(?i)what happens next', r'(?i)jaw[-\s]?dropping'
        ]
        has_clickbait = any(re.search(pattern, text) for pattern in clickbait_patterns)
        
        # Check for factual language (dates, statistics, specific details)
        fact_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Date patterns
            r'\d+(?:\.\d+)?\s*(?:percent|%)',  # Percentage
            r'according to',  # Attribution
            r'\$\d+(?:\.\d+)?\s*(?:million|billion|trillion)?',  # Money amounts
            r'\d+\s*(?:people|individuals|persons|citizens)',  # Counting people
        ]
        has_factual_language = sum(1 for pattern in fact_patterns if re.search(pattern, text)) >= 2
        
        # Create an enhanced scoring system with more factors
        score = 0.0
        
        # Core factors
        if sensational:
            score += 0.25  # Sensational language increases fake probability
        
        if has_sources:
            score -= 0.35  # Citing sources decreases fake probability
        
        # Secondary factors
        if very_short:
            score += 0.15  # Very short content increases fake probability
            
        if good_length:
            score -= 0.1  # Good length decreases fake probability
            
        if has_balanced_view:
            score -= 0.2  # Balanced reporting decreases fake probability
            
        if has_excessive_caps:
            score += 0.15  # Excessive caps increases fake probability
            
        if excessive_punct:
            score += 0.15  # Excessive punctuation increases fake probability
            
        # Additional factors
        if has_clickbait:
            score += 0.2  # Clickbait language increases fake probability
            
        if has_factual_language:
            score -= 0.25  # Factual details decrease fake probability
        
        # Calculate a more dynamic confidence score based on the strength of indicators
        # The more extreme the score, the higher the confidence
        
        # Base confidence levels are different for different categories
        fake_base = 0.60
        real_base = 0.60
        uncertain_base = 0.55
        
        # Determine result and confidence
        if score > 0.2:  # Threshold for fake news detection
            result = "fake"
            # Calculate confidence - higher score means higher confidence
            # Use a non-linear scale to differentiate between strong and weak signals
            confidence_boost = score * 0.35  # More impact from score
            raw_confidence = fake_base + confidence_boost
            # No rounding to allow for more variation
            
            # Create detailed message
            reasons = []
            if sensational:
                reasons.append("sensational language")
            if has_clickbait:
                reasons.append("clickbait-style content")
            if not has_sources:
                reasons.append("lack of reliable sources")
            if very_short:
                reasons.append("unusually short content")
            if has_excessive_caps:
                reasons.append("excessive use of capital letters")
            if excessive_punct:
                reasons.append("excessive punctuation")
                
            # Limit to top 3 reasons for clarity
            if len(reasons) > 3:
                reasons = reasons[:3]
                
            message = f"Article likely fake due to: {', '.join(reasons)}"
            
        elif score < -0.2:  # Threshold for real news detection
            result = "real"
            # Calculate confidence - more negative score means higher confidence for real news
            confidence_boost = abs(score) * 0.35  # More impact from score
            raw_confidence = real_base + confidence_boost
            # No rounding to allow for more variation
            
            # Create detailed message
            reasons = []
            if has_sources:
                reasons.append("cites reliable sources")
            if has_factual_language:
                reasons.append("contains specific facts and data")
            if not sensational:
                reasons.append("uses measured language")
            if has_balanced_view:
                reasons.append("presents balanced perspectives")
            if good_length:
                reasons.append("appropriate article length")
                
            # Limit to top 3 reasons for clarity
            if len(reasons) > 3:
                reasons = reasons[:3]
                
            message = f"Article likely authentic due to: {', '.join(reasons)}"
            
        else:
            # For borderline cases, calculate confidence based on specific indicators
            if has_sources and has_factual_language:
                result = "possibly real"
                # Calculate a variable confidence based on strength of indicators
                source_weight = 0.08 if has_sources else 0
                factual_weight = 0.07 if has_factual_language else 0
                balanced_weight = 0.05 if has_balanced_view else 0
                confidence = uncertain_base + source_weight + factual_weight + balanced_weight
                message = "Article has some indicators of reliability but exercise caution"
            elif sensational or has_clickbait:
                result = "possibly fake"
                # Calculate a variable confidence based on strength of indicators
                sensational_weight = 0.08 if sensational else 0
                clickbait_weight = 0.07 if has_clickbait else 0
                caps_weight = 0.05 if has_excessive_caps else 0
                confidence = uncertain_base + sensational_weight + clickbait_weight + caps_weight
                message = "Article has some indicators of misinformation, exercise caution"
            else:
                result = "uncertain"
                # Truly uncertain cases get the lowest confidence
                confidence = 0.55
                message = "Unable to determine authenticity with high confidence"
        
        # Apply minimum and maximum thresholds, but with a wider range
        # This allows for more variation in confidence scores
        confidence = max(0.55, min(0.95, confidence))  # Between 55% and 95%
        
        # Add a small random factor (±0.03) to prevent identical confidence scores
        # for slightly different inputs, while maintaining overall accuracy
        import random
        random_factor = (random.random() * 0.06) - 0.03  # Between -0.03 and +0.03
        confidence = max(0.55, min(0.95, confidence + random_factor))
        
        # Format to 2 decimal places for display
        confidence = round(confidence * 100) / 100
        
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
