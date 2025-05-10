from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Main route for serving the frontend
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

# API proxy route to forward requests to the FastAPI backend
@app.route('/api/verify', methods=['POST'])
def api_verify():
    # Get the JSON data from the request
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    try:
        # Import the necessary components for verification
        from backend.detector import detect_fake_news
        from backend.scraper import extract_text_from_url
        
        # Process the request similar to how backend/app.py does it
        text = data.get('text')
        url = data.get('url')
        
        if not text and not url:
            return jsonify({"error": "Please provide valid article text or URL"}), 400
            
        text_to_analyze = text
        
        # If URL is provided, scrape the text
        if url:
            extracted_text = extract_text_from_url(url)
            if not extracted_text and not text_to_analyze:
                return jsonify({"error": "Could not extract text from the provided URL"}), 400
            
            if extracted_text:
                text_to_analyze = extracted_text
        
        # Analyze the text
        result, confidence, message = detect_fake_news(text_to_analyze)
        
        # Create the response
        result = {
            "result": result,
            "confidence": confidence,
            "message": message
        }
        
        # Return the result as JSON
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Static files route
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
