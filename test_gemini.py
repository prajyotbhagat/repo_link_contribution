import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

print("Available embedding models:")
for m in genai.list_models():
    if 'embedContent' in m.supported_generation_methods:
        print(m.name)

try:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content="Hello world"
    )
    print("Successfully embedded with models/gemini-embedding-001")
except Exception as e:
    print(f"Error with gemini-embedding-001: {e}")

try:
    result = genai.embed_content(
        model="models/embedding-001",
        content="Hello world"
    )
    print("Successfully embedded with models/embedding-001")
except Exception as e:
    print(f"Error with embedding-001: {e}")
