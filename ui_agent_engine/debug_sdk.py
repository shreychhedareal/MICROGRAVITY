import asyncio
import os
from google import genai

async def test_connection():
    api_key = "INSERT_API_KEY"
    client = genai.Client(api_key=api_key)
    print(f"Client: {type(client)}")
    print(f"Client.aio: {type(client.aio)}")
    print(f"Client.aio.live: {type(client.aio.live)}")
    
    try:
        # Check if connect is a method or something else
        connect_attr = getattr(client.aio.live, 'connect', None)
        print(f"Connect attribute: {type(connect_attr)}")
        
        async with client.aio.live.connect(model='gemini-2.0-flash-exp') as session:
            print(f"Session established: {type(session)}")
            print("Closing session...")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
