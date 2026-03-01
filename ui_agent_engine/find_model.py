import asyncio
from google import genai
import os

async def find_bidi_model():
    api_key = "INSERT_API_KEY"
    client = genai.Client(api_key=api_key)
    
    models = [m.name for m in client.models.list()]
    print(f"Testing models: {models}")
    
    for model_name in models:
        # Only test gemini models
        if "gemini" not in model_name:
             continue
             
        # Strip 'models/' prefix if present
        clean_name = model_name.split('/')[-1]
        
        print(f"Testing {clean_name}...")
        try:
            async with client.aio.live.connect(model=clean_name) as session:
                print(f"SUCCESS: {clean_name} supports Bidi!")
                return clean_name
        except Exception as e:
            msg = str(e)
            if "1008" in msg or "not support BidiGenerateContent" in msg:
                 print(f"SKIP: {clean_name} does not support Bidi.")
            else:
                 print(f"ERROR on {clean_name}: {e}")

if __name__ == "__main__":
    asyncio.run(find_bidi_model())
