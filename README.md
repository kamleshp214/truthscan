# Fake News Detector

A full-stack web application for detecting fake news using rule-based text analysis, particularly relevant for the India-Pakistan context where misinformation can have serious consequences.

![Fake News Detector](https://img.shields.io/badge/Status-Ready%20for%20Deployment-success)

## 🌟 Features

- **Text Analysis**: Paste article text directly for analysis
- **URL Processing**: Enter news article URLs to automatically extract and analyze content
- **Rule-Based Detection**: Analyzes text patterns, sensational language, and source attribution
- **Confidence Scoring**: Provides a confidence level for each verification result
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5
- **Backend**: Python with Flask
- **Text Processing**: BeautifulSoup4 for web scraping and extraction
- **API**: RESTful API design for communication between frontend and backend

## 📋 Requirements

- Python 3.11 or higher
- Flask and its dependencies (flask-cors)
- BeautifulSoup4 for web content extraction
- Requests for HTTP requests

## 🚀 Installation & Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fake-news-detector.git
   cd fake-news-detector
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

4. Access the application in your browser:
   ```
   http://localhost:5000
   ```

## 📊 How it Works

The fake news detection system uses a combination of techniques:

1. **Sensational Language Detection**: Identifies words and phrases commonly used in clickbait and fake news
2. **Source Analysis**: Checks for mentions of reliable sources and proper attribution
3. **Text Pattern Analysis**: Evaluates the article's structure and tone for indicators of potential misinformation
4. **URL Content Extraction**: Automatically pulls the main content from news URLs for analysis

## 🔍 Usage

1. Enter either article text or a URL in the provided input fields
2. Click the "Verify" button to analyze the content
3. View the verification result with confidence score and explanation
4. Use the "New Verification" button to analyze another article

## ⚙️ Configuration

No additional configuration is required for basic usage. For deployment, consider:

- Setting environment variables for production
- Configuring CORS settings for specific domains
- Setting up a proper web server like Gunicorn

## 📝 Limitations

- The system uses rule-based detection rather than advanced ML models
- Results are indicative and not guaranteed
- URLs with complex JavaScript rendering might not be properly scraped
- Always cross-verify information with multiple reliable sources

## 🌱 Future Enhancements

- Integration with pre-trained ML models for more accurate detection
- Support for regional languages and context-specific misinformation
- User accounts to save verification history
- API access for third-party integrations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Disclaimer**: This tool provides an automated assessment and should not be the sole basis for determining the veracity of news. Always cross-check information with multiple reliable sources.