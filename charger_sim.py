import asyncio
import websockets
import json
import time
from datetime import datetime, timezone

SERVER_URL = "ws://localhost:8887/ocpp/"
CHARGER_ID = "ZA-ABB-001"
POWER_KW = 7.5

is_charging = False

# 1. The Listener Task (Runs continuously in the background)
async def listen_for_commands(websocket):
    global is_charging
    try:
        async for message in websocket:
            data = json.loads(message)
            
            # If it is a CALL (Request) from the Java Server
            if data[0] == 2:  
                message_id = data[1]
                command_name = data[2]

                if command_name == "RemoteStartTransaction":
                    print("⚡ Start Command Received!")
                    is_charging = True
                    # Acknowledge the command back to the Java server
                    await websocket.send(json.dumps([3, message_id, {"status": "Accepted"}]))

                elif command_name == "RemoteStopTransaction":
                    print("🛑 Stop Command Received!")
                    is_charging = False
                    # Acknowledge the command back to the Java server
                    await websocket.send(json.dumps([3, message_id, {"status": "Accepted"}]))

                    #stop receipt
                    stop_req = [
                        2, f"stop_{int(time.time())}", "StopTransaction",
                        {
                            "meterStop": int(POWER_KW * 1000),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "transactionId": 0
                        }
                    ]
                    await websocket.send(json.dumps(stop_req))
                    

    except Exception as e:
        print(f"Listener error: {e}")

# 2. The Main Charger Loop
async def start_charger():
    uri = SERVER_URL + CHARGER_ID
    print(f"Connecting to: {uri}")

    async with websockets.connect(uri, subprotocols=['ocpp1.6'], ping_interval=None) as websocket:
        print("Connected to Central System")

        # BootNotification (Fixed the JSON keys to match OCPP 1.6 Spec)
        boot_req = [2, "boot1", "BootNotification", {
            "chargePointVendor": "ABB", 
            "chargePointModel": "Terra"
        }]
        await websocket.send(json.dumps(boot_req))

        # Start listening for incoming commands at the same time
        asyncio.create_task(listen_for_commands(websocket))

        print("Standby Mode. Waiting for WhatsApp command...")

        while True:
            global is_charging
            if is_charging:
                kwh = POWER_KW * (5/3600)
                timestamp = datetime.now(timezone.utc).isoformat()
                # MeterValues payload required by Java
                meter_req = [
                    2, f"mv_{int(time.time())}", "MeterValues",
                    {
                        "connectorId": 1,
                        "meterValue": [{
                            "timestamp": timestamp,
                            "sampledValue": [{"value": f"{kwh:.5f}"}]}]
                    }
                ]
                await websocket.send(json.dumps(meter_req))
                print(f"Charging... Sent {kwh:.5f} kWh")
            else:
                # Heartbeat payload
                hb = [2, f"hb_{int(time.time())}", "Heartbeat", {}]
                await websocket.send(json.dumps(hb))
                print("Heartbeat")

            await asyncio.sleep(5)

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(start_charger())
        except Exception as e:
            print(f"Connection Dropped ({e}). Reconnecting in 5s")
            time.sleep(5)