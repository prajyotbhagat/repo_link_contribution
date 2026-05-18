import os
import re
import nltk
from nltk.tokenize import word_tokenize
import google.generativeai as genai

def analyze_readme_quality(readme_text):
    if not readme_text:
        return 0.0

    score = 0.0
    text_lower = readme_text.lower()
    
    # 1. Check for code blocks (indicates examples/usage)
    if "```" in readme_text:
        score += 30.0

    # 2. Check for key sections
    key_sections = ["install", "usage", "contribut", "license", "documentation", "getting started"]
    found_sections = sum(1 for section in key_sections if section in text_lower)
    score += (found_sections / len(key_sections)) * 40.0

    # 3. Readability / Length check (not too short)
    try:
        tokens = word_tokenize(readme_text)
        if len(tokens) > 200:
            score += 15.0
        elif len(tokens) > 50:
            score += 5.0
    except Exception:
        if len(readme_text) > 1000:
            score += 15.0

    # 4. Check for badges
    if "[!" in readme_text or "<img src=" in readme_text:
        score += 15.0

    return min(100.0, score)

def extract_topics(readme_text):
    if not readme_text:
        return []
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return []
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "Extract up to 5 key technical topics or keywords from the following README snippet. Return only the topics separated by commas, no other text:\n\n" + readme_text[:3000]
        response = model.generate_content(prompt)
        topics = [t.strip().lower() for t in response.text.split(',') if t.strip()]
        return topics[:5]
    except Exception as e:
        print(f"Error extracting topics: {e}")
        return []
