import logging
import os
import re
from typing import Tuple
import numpy as np

# Initialize logger
logger = logging.getLogger(__name__)

# Global variable to store the model and tokenizer
model = None
tokenizer = None

def load_model():
    """
    Load the pre-trained model for fake news detection.
    Caches the model to avoid reloading for each request.
    """
    global model, tokenizer
    
    if model is not None and tokenizer is not None:
        return model, tokenizer
    
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        # Try to load a pre-trained fake news detection model
        # For India-Pakistan context, we might want a model fine-tuned on regional data
        # but we'll use a general model as a starting point
        model_name = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
        
        logger.info(f"Loading model: {model_name}")
        
        # Load the model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        logger.info("Model loaded successfully")
        return model, tokenizer
        
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        logger.warning("Will use rule-based detection as fallback")
        return None, None

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

def rule_based_fake_news_detection(text: str) -> Tuple[str, float, str]:
    """
    Detect fake news using rule-based methods when model is unavailable.
    
    Args:
        text: The article text
        
    Returns:
        Tuple of (result, confidence, message)
    """
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

def model_based_fake_news_detection(text: str, model, tokenizer) -> Tuple[str, float, str]:
    """
    Detect fake news using the pre-trained model.
    
    Args:
        text: The article text
        model: The pre-trained model
        tokenizer: The tokenizer for the model
        
    Returns:
        Tuple of (result, confidence, message)
    """
    try:
        # Prepare the text for the model
        # Truncate text if it's too long
        max_length = 512
        if len(text.split()) > max_length:
            text = " ".join(text.split()[:max_length])
        
        # Tokenize the text
        encoded_input = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        # Get the model prediction
        import torch
        with torch.no_grad():
            outputs = model(**encoded_input)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=1)
            
        # Get the highest probability class
        # For MNLI models: 0 = contradiction, 1 = neutral, 2 = entailment
        # We'll consider contradiction as fake, entailment as real
        pred_class = torch.argmax(predictions, dim=1).item()
        confidence = predictions[0][pred_class].item()
        
        if pred_class == 0:  # Contradiction - likely fake
            result = "fake"
            message = "Content appears to contradict known facts"
        elif pred_class == 2:  # Entailment - likely real
            result = "real"
            message = "Content appears consistent with known facts"
        else:  # Neutral - uncertain
            # For neutral predictions, we'll still make a call but with lower confidence
            # Check for contextual clues to lean one way or the other
            is_sensational = is_article_sensational(text)
            has_sources = has_reliable_sources(text)
            
            if is_sensational and not has_sources:
                result = "fake"
                message = "Content is sensationalized and lacks reliable sources"
                confidence = 0.65
            elif has_sources and not is_sensational:
                result = "real"
                message = "Content cites reliable sources and uses measured language"
                confidence = 0.65
            else:
                result = "fake"  # Default to caution
                message = "Unable to verify with high confidence, exercise caution"
                confidence = 0.55
        
        return result, confidence, message
        
    except Exception as e:
        logger.error(f"Error in model-based detection: {str(e)}")
        # Fall back to rule-based detection
        logger.info("Falling back to rule-based detection")
        return rule_based_fake_news_detection(text)

def detect_fake_news(text: str) -> Tuple[str, float, str]:
    """
    Detect if the given text is fake news.
    
    Args:
        text: The article text to analyze
        
    Returns:
        Tuple of (result, confidence, message)
    """
    # Sanitize input
    if not text or len(text.strip()) < 20:
        return "fake", 0.9, "Text is too short for reliable analysis"
    
    try:
        # Try to use the model-based approach
        current_model, current_tokenizer = load_model()
        
        if current_model and current_tokenizer:
            logger.debug("Using model-based detection")
            return model_based_fake_news_detection(text, current_model, current_tokenizer)
        else:
            # Fall back to rule-based approach
            logger.debug("Using rule-based detection")
            return rule_based_fake_news_detection(text)
            
    except Exception as e:
        logger.error(f"Error in fake news detection: {str(e)}")
        # In case of any errors, use rule-based approach
        logger.info("Error occurred, using rule-based detection")
        return rule_based_fake_news_detection(text)
