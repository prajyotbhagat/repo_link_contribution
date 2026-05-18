"""
AI summarizer for GitHub issues using Gemini API.
"""
import os
import google.generativeai as genai

def summarize_issue(title: str, body: str, max_sentences: int = 3) -> str:
    """
    Generate a concise AI summary of a GitHub issue using Gemini API.

    Args:
        title: The issue title.
        body: The issue body (markdown).
        max_sentences: Number of sentences to include in the summary.

    Returns:
        A plain-text summary string.
    """
    if not body or len(body.strip()) < 50:
        return title.strip()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return title.strip()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Summarize the following GitHub issue in a maximum of {max_sentences} sentences. Focus on the core problem and any proposed solution. Do not use markdown.\n\nTitle: {title}\nBody:\n{body[:3000]}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error summarizing issue: {e}")
        return title.strip()
