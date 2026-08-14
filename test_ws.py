import asyncio
import aiohttp
import json
import time

async def main():
    async with aiohttp.ClientSession() as session:
        print("Connecting to ws://127.0.0.1:14398/ws...")
        async with session.ws_connect('ws://127.0.0.1:14398/ws') as ws:
            print("Connected!")
            
            # Request start star trails
            msg = {
                "type": "start_star_trails",
                "durationSeconds": 3600,
                "sampleIntervalSeconds": 60,
                "magnitudeLimit": 6.0,
                "playbackRate": 50.0
            }
            print(f"Sending: {msg}")
            await ws.send_json(msg)
            
            # Wait for responses
            try:
                async for ws_msg in ws:
                    if ws_msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(ws_msg.data)
                        print(f"Received JSON: {data.get('type')}")
                    elif ws_msg.type == aiohttp.WSMsgType.BINARY:
                        print(f"Received BINARY message of {len(ws_msg.data)} bytes")
                        # Parse binary header
                        import struct
                        header_len = struct.unpack('<I', ws_msg.data[:4])[0]
                        header_json = ws_msg.data[4:4+header_len].decode('utf-8')
                        print(f"Binary header: {header_json}")
            except asyncio.TimeoutError:
                print("Timeout waiting for response.")

if __name__ == "__main__":
    asyncio.run(main())
