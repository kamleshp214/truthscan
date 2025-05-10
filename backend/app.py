import logging
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import re
from .scraper import extract_text_from_url
from .detector import detect_fake_news

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Fake News Detection API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VerificationRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None

    @validator('url')
    def url_must_be_valid(cls, v):
        if v is not None:
            # Simple URL validation pattern
            pattern = re.compile(
                r'^(?:http|https)://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
                r'localhost|'  # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IPv4
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if not pattern.match(v):
                raise ValueError('Invalid URL format')
        return v

    @validator('text', 'url')
    def one_field_must_be_provided(cls, v, values, **kwargs):
        field = kwargs.get('field')
        if field == 'text' and v is None and 'url' not in values:
            raise ValueError('Either text or url must be provided')
        if field == 'url' and v is None and 'text' not in values:
            pass  # URL can be None if text is provided, validated in text
        return v

class VerificationResponse(BaseModel):
    result: str
    confidence: float
    message: str

@app.get("/")
async def root():
    return {"message": "Welcome to the Fake News Detection API"}

@app.post("/verify", response_model=VerificationResponse)
async def verify_news(request: VerificationRequest):
    try:
        # Validate input
        if not request.text and not request.url:
            raise HTTPException(status_code=400, detail="Please provide valid article text or URL")
        
        text_to_analyze = request.text
        
        # If URL is provided, scrape the text from the URL
        if request.url:
            try:
                logger.debug(f"Extracting text from URL: {request.url}")
                extracted_text = extract_text_from_url(request.url)
                if not extracted_text and not text_to_analyze:
                    raise HTTPException(
                        status_code=400, 
                        detail="Could not extract text from the provided URL"
                    )
                # If both text and URL are provided, prioritize text from URL
                if extracted_text:
                    text_to_analyze = extracted_text
            except Exception as e:
                logger.error(f"Error extracting text from URL: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to process the URL: {str(e)}"
                )
        
        # Detect fake news
        try:
            logger.debug("Analyzing text for fake news detection")
            result, confidence, message = detect_fake_news(text_to_analyze)
            return VerificationResponse(
                result=result,
                confidence=confidence,
                message=message
            )
        except Exception as e:
            logger.error(f"Error during fake news detection: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error analyzing text: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in verify endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process the request")
