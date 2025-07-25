import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print("Loaded key:", repr(api_key))

client = OpenAI(api_key=api_key)
try:
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Ping?"}],
        max_tokens=2,
    )
    print("Test success:", resp.choices[0].message.content)
except Exception as e:
    print("Test failed:", e)
