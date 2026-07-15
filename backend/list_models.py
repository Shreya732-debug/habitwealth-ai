# backend/test_gemini.py
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Testing Gemini 2.5 Flash connection...\n")

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Say hello and confirm you are working. Be brief.",
    config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=100,
    )
)

print("Response:", response.text)
print("\nAvailable models:")
for model in client.models.list():
    print(" ", model.name)