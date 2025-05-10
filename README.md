# TruthScan: Advanced Fake News Detection Platform

TruthScan is a sophisticated web application designed to analyze news articles and identify potential misinformation, particularly in the India-Pakistan context where accurate news is critical. This tool uses advanced text analysis and pattern recognition to evaluate the credibility of news content.

![TruthScan](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

## 🚀 Features

- **Dual Input Methods**
  - Paste full article text directly for analysis
  - Enter article URL for automatic content extraction and analysis

- **Comprehensive Analysis Factors**
  - Sensational language detection (exaggerated claims, clickbait patterns)
  - Source attribution evaluation (credible source references)
  - Content depth assessment (substantive vs. superficial coverage)

- **Clean, Intuitive Interface**
  - Modern, responsive design with Bootstrap
  - Real-time analysis feedback
  - Detailed breakdown of verification results

- **Advanced URL Content Extraction**
  - Multi-strategy content extraction for complex news sites
  - Robust error handling and fallback mechanisms
  - Smart filtering of non-article elements (ads, navigation, etc.)

## 🛠️ Technology Stack

- **Frontend**
  - HTML5, CSS3 with custom animations and transitions
  - Vanilla JavaScript (ES6+) for interactivity
  - Fully responsive design with Bootstrap 5

- **Backend**
  - Python with Flask framework
  - BeautifulSoup4 for advanced web scraping
  - Rule-based algorithm for fact-checking analysis

## 📋 Requirements

- Python 3.11 or higher
- Flask and Flask-CORS for the web server
- BeautifulSoup4 for HTML parsing and content extraction
- Requests library for HTTP requests

## 🚀 Installation & Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/truthscan.git
   cd truthscan
   ```

2. Install required packages:
   ```bash
   pip install flask flask-cors beautifulsoup4 requests
   ```

3. Run the application:
   ```bash
   python main.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## 🔍 How TruthScan Works

TruthScan employs a multi-faceted approach to analyzing news content:

1. **Content Extraction**
   - For URL inputs, TruthScan employs multiple extraction strategies to identify and extract the main article content.
   - Advanced filtering removes ads, navigation, and other non-article elements.

2. **Text Analysis**
   - The content is analyzed for indicators of potential misinformation:
     - **Sensational Language**: Identifies hyperbolic, emotionally charged language commonly used in clickbait.
     - **Source Attribution**: Evaluates whether the article cites credible sources.
     - **Content Depth**: Assesses the substance and thoroughness of the reporting.

3. **Result Generation**
   - The analysis produces a verdict (real, fake, or uncertain) with a confidence score.
   - Detailed explanation of the factors that contributed to the verdict.

## 📱 Usage Guide

1. **Choose Input Method**
   - Toggle between text input and URL input tabs based on your preference.

2. **Submit Content**
   - For text input: Copy and paste the full news article text.
   - For URL input: Enter the complete URL of the news article.

3. **Review Results**
   - View the overall verdict and confidence score.
   - Examine the detailed breakdown of analysis factors.
   - Use the "New Analysis" button to analyze another article.

## ⚠️ Limitations & Disclaimer

- TruthScan provides an automated assessment and should not be the sole basis for determining the veracity of news.
- The system uses rule-based detection which, while effective, is not infallible.
- Always cross-check information with multiple reliable sources.
- URL extraction may not work perfectly on all websites due to variations in HTML structure.

## 💡 Future Enhancements

- Integration with external fact-checking databases
- Support for vernacular languages prevalent in the India-Pakistan region
- Machine learning-based classification for higher accuracy
- User accounts to save verification history
- Browser extension for one-click verification

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Note: This tool is designed for educational and informational purposes. It should be used as part of a broader media literacy approach.*