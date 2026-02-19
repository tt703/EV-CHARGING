import asyncio
import websockets
import json

import time

SERVER_URL = "ws://localhost:8887/ocpp/"
CHARGER_ID = "ZA-ABB-001"
POWER_KW = 7.5

async def start_charger():
    uri = SERVER_URL + CHARGER_ID
    print(f"Conecting to: {uri}")

    async with websockets.connect(uri, subprotocols=['ocpp1.6'], ping_interval=None) as websocket:
        print("Connected to Central System")

        #1. Boot
        boot_req = [2, "boot1","BootNotification",{"vendor":"ABB","model":"Terra"}]
        await websocket.send(json.dumps(boot_req))


        #2. State variables
        is_charging = False
        print("Standby Mode. Waiting for WhatsApp command...")

        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(),timeout=0.1)

                data = json.loads(message)
                if isinstance(data, list) and data[0] == 2:
                    action = data[2]
                    if action == "RemoteStartTransaction":
                        if not is_charging:
                            print("\n Command Received:  START CHARGING")
                            is_charging = True
                        elif action == "RemoteStopTransaction":
                            if is_charging:
                                print("\n Command Received: STOP CHARGING")
                                is_charging = False
                                print("💤 Entering Standby...")
            except asyncio.TimeoutError:
                pass 
            except Exception as e:
                print(f"Network Glitch: {e}")
                break

            if is_charging:
                kwh = POWER_KW * (5/3600)

                meter_req = [
                    2, f"mv_{int(time.time())}","MeterValues",
                    {"meterValue": [{"sampledValue": [{"value": f"{kwh:.5f}"}]}]}
                ]
                await websocket.send(json.dumps(meter_req))
                print(f"Charging... Sent {kwh:.5f} kWh")

        await asyncio.sleep(5)

        if not is_charging:
            hb = [2,f"hb_{int(time.time())}", "Heartbeat", {}]
            await websocket.send(json.dumps(hb))
            print("Heartbeat")

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(start_charger())
        except Exception as e:
            print(f"Connection Dropped ({e}). Reconnecting in 5s")
            time.sleep(5)
