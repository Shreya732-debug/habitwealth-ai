# backend/test_gemini.py
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("=" * 50)
print("API Key loaded:", api_key[:8] + "..." if api_key else "NOT FOUND")
print("=" * 50)

# Test 1 — Basic connection
print("\nSending first message to Gemini...")
print("-" * 50)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello! Tell me your name and one thing you can help me with regarding finances. Keep it to 2 sentences.",
    config=types.GenerateContentConfig(
        system_instruction="""
        You are a personal finance assistant called FinanceGPT.
        You help users manage their monthly budgets, track expenses,
        and make smart spending decisions.
        Always be concise, friendly, and financially responsible.
        """,
        temperature=0.7,
        max_output_tokens=200,
    )
)

print("Gemini's response:")
print(response.text)
print("Finish reason:", response.candidates[0].finish_reason)
print("-" * 50)

# Test 2 — Finance specific question
print("\n" + "=" * 50)
print("Testing finance context...")
print("-" * 50)

response2 = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="If I earn 25000 per month and spend 18000, what is my monthly savings rate? Show the calculation.",
    config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=300,
    )
)

print("Finance question response:")
print(response2.text)
print("-" * 50)

print("\n✅ All tests passed — Gemini API is connected and working correctly!")