import os
import asyncio
import base64
import json
from io import BytesIO
import mss
import mss.tools
from PIL import Image, ImageGrab
from google import genai
from google.genai import types
from typing import Callable, Optional, Dict, Any
import sounddevice as sd
import numpy as np
import queue
import threading

class GeminiLiveStreamer:
    """
    Manages the continuous bidirectional WebSocket connection to the Gemini Multimodal Live API.
    Handles streaming screen frames and receiving real-time interaction predictions.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash-exp-image-generation" # Start with established bidi model
        self.session = None
        self.is_streaming = False
        self.on_response_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Audio configuration
        self.sample_rate = 16000
        self.audio_in_queue = queue.Queue()
        self.audio_out_queue = queue.Queue()
        self._audio_input_stream = None
        self._audio_output_stream = None

    async def start_session(self, system_instruction: str = None):
        """Establishes the WebSocket session and blocks until closed."""
        self.model = "gemini-2.0-flash-exp-image-generation"
        print(f"[LiveStreamer] Connecting to {self.model} (Audio Optimized)...")
        
        config = {
            "response_modalities": ["AUDIO"],
        }
        if system_instruction:
            config["system_instruction"] = system_instruction

        print("[LiveStreamer] Initializing audio streams...")
        try:
            self._setup_audio_streams()
        except Exception as e:
            print(f"[LiveStreamer] Audio hardware error: {e}")

        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                print("[LiveStreamer] Connection established! Session Active.")
                self.session = session
                self.is_streaming = True
                
                # Start background processes
                tasks = [
                    asyncio.create_task(self._listen_for_responses()),
                ]
                if self._audio_input_stream:
                    tasks.append(asyncio.create_task(self._stream_audio_input_loop()))
                
                await asyncio.gather(*tasks)
                
        except asyncio.CancelledError:
             print("[LiveStreamer] Background session cancelled safely.")
        except Exception as e:
            print(f"[LiveStreamer] Failed during live session: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_streaming = False
            self.session = None
            self._cleanup_audio()

    async def disconnect(self):
        """Signals the session to close."""
        self.is_streaming = False
        print("[LiveStreamer] Disconnect requested (session will organically close).")

    def _capture_screen_compressed(self) -> bytes:
        """Captures the primary monitor and compresses it heavily for fast streaming."""
        img = ImageGrab.grab() # more stable
        img.thumbnail((1024, 1024))
        output = BytesIO()
        img.save(output, format="JPEG", quality=60)
        return output.getvalue()

    async def stream_screen_loop(self, fps: float = 1.0):
        """Continuously captures and sends frames to the session."""
        print(f"[LiveStreamer] Starting screen stream at {fps} fps...")
        interval = 1.0 / fps
        while self.is_streaming and self.session:
            try:
                frame_bytes = self._capture_screen_compressed()
                await self.session.send(
                    input=types.LiveClientRealtimeInput(
                        media_chunks=[
                            types.Blob(
                                mime_type="image/jpeg",
                                data=frame_bytes
                            )
                        ]
                    )
                )
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"[LiveStreamer] Error sending frame: {e}")
                break

    async def send_prompt(self, text: str):
         if not self.session or not self.is_streaming:
             return
         await self.session.send(
             input=types.LiveClientContent(
                 turns=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                 turn_complete=True
             )
         )

    async def _listen_for_responses(self):
        print("[LiveStreamer] Listener task started.")
        try:
            async for response in self.session.receive():
                if response.server_content:
                    if response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.text:
                                try:
                                    json_data = json.loads(part.text)
                                    if self.on_response_callback:
                                         self.on_response_callback(json_data)
                                except json.JSONDecodeError:
                                    if self.on_response_callback:
                                         self.on_response_callback({"text_response": part.text})
                            
                            if part.inline_data:
                                self.audio_out_queue.put(part.inline_data.data)
        except asyncio.CancelledError:
             pass
        except Exception as e:
             print(f"[LiveStreamer] Error in listener loop: {e}")
             self.is_streaming = False

    def _setup_audio_streams(self):
        def input_callback(indata, frames, time, status):
            self.audio_in_queue.put(indata.copy())

        def output_callback(outdata, frames, time, status):
             try:
                 data = self.audio_out_queue.get_nowait()
                 decoded = np.frombuffer(data, dtype='int16')
                 # Handle cases where the decoded chunk size exceeds or is less than the expected frames
                 chunk_len = min(len(decoded), frames)
                 outdata[:chunk_len] = decoded[:chunk_len].reshape(-1, 1)
                 if chunk_len < frames:
                      outdata[chunk_len:] = 0
             except queue.Empty:
                 outdata.fill(0)

        self._audio_input_stream = sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype='int16', callback=input_callback
        )
        self._audio_output_stream = sd.OutputStream(
            samplerate=24000, channels=1, dtype='int16', callback=output_callback
        )
        self._audio_input_stream.start()
        self._audio_output_stream.start()

    async def _stream_audio_input_loop(self):
        while self.is_streaming and self.session:
            try:
                data = await asyncio.to_thread(self.audio_in_queue.get, timeout=1.0)
                # Using the documentation's helper pattern for real-time input
                await self.session.send_realtime_input(
                    audio={"data": data.tobytes(), "mime_type": "audio/pcm"}
                )
            except queue.Empty:
                continue
            except Exception as e:
                break

    def _cleanup_audio(self):
        if self._audio_input_stream:
            self._audio_input_stream.stop()
            self._audio_input_stream.close()
        if self._audio_output_stream:
            self._audio_output_stream.stop()
            self._audio_output_stream.close()

    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self.on_response_callback = callback
