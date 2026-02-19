import asyncio
import websockets
import json
import ssl

async def simulate_charger():
    # --- IMPORTANT: CONNECT TO AZURE (wss://) ---
    uri = "wss://ev-charger-app-703.azurewebsites.net/ABB-Sim-001"
    
    print(f"🔌 Connecting to Cloud: {uri} ...")
    
    # Create an SSL context to handle the secure connection (Required for Azure)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(uri, ssl=ssl_context, subprotocols=['ocpp1.6']) as websocket:
            print("✅ CONNECTED to Azure!")

            # SEND: BootNotification
            boot_request = [
                2, "msg-1001", "BootNotification", 
                {"chargePointModel": "TerraAC", "chargePointVendor": "ABB"}
            ]
            
            print(f"📤 Sending: {boot_request}")
            await websocket.send(json.dumps(boot_request))

            # RECEIVE: Server Response
            response = await websocket.recv()
            print(f"📥 Server Replied: {response}")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

asyncio.run(simulate_charger())