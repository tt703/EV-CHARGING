from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import uvicorn
import requests
import datetime
from fastapi import Depends, HTTPException, status, FastAPI, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from pydantic import BaseModel
import time


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Database connection
DB_DSN = "postgresql://postgres:Tlotlo@db:5432/ev_charging"

#WhatsApp BOT Credentials 
WHATSAPP_TOKEN = "EAAZAaMpXPENIBQwgJS1CAHJ6HoWWhRxTsrqzn7MqZBAhqPNCEX4opBmtCnyNqLmYPTMUqOplZCdSZCxMQqB4ZB7SyFimCiWyorBLrirv46ZBoVmZB7WxPM0VO9PccBNoOSlkzWVtPe8aYQ5eXLHU9ffoMO87jsp9SemAgiwkb9t0yDFJ5m2XjHL28NfLIuwsZAnF8RSM7vr83ZBrcZCZBUNEBnD3uCJBnMfIUKjM9jSgHRYF9cIoFiZC86Vtfsjexp2bkrqkVZCqfRYjvn0as2B7NtxfIcS6P"
PHONE_NUMBER_ID = "916860318184766"
VERIFY_TOKEN = "12345"

#JWT Security COnfig
SECRET_KEY = "myCharge_Super_Secret_Key_2026!"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")
class ChargerCreate(BaseModel):
    charger_id: str

user_last_active = {}
SESSIONS_TIMEOUT_SECONDS = 300 #five minutes for now
#Reusable Main Menu
MAIN_MENU_BUTTONS = [
    {"id": "menu_charge", "title": "⚡Charge Now"},
    {"id": "menu_location", "title":"📍 Find Chargers"},
    {"id": "menu_history", "title":"📈 My History"}
]

def get_db_connection():
    return psycopg2.connect(DB_DSN)

def send_whatsapp_message(to_phone, message_text):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message_text}
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Message sent to {to_phone} successfully!")
    else:
        print(f"Failed to send message: {response.text}")
def send_interactive_buttons(to_phone, message_text, buttons):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization" : f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json" 
    }
    action_buttons = [
        {"type":"reply", "reply":{"id": b["id"], "title": b["title"]}}
        for b in buttons[:3]
    ]
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type":"button",
            "body":{"text": message_text},
            "action":{"buttons": action_buttons}
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ Interactive buttons sent to {to_phone} successfully!")
    else:
        print(f"❌ Failed to send buttons: {response.text}")
#dependecy function
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username  is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired! Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token authentication")
@app.post("/api/chargers", dependencies=[Depends(get_current_user)])
def add_charger(charger: ChargerCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # THE FIX: Notice the magical trailing comma right after charger.charger_id !
        cursor.execute("INSERT INTO charger(charger_id, status) VALUES (%s, 'AVAILABLE')", (charger.charger_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Database Insert Error: {e}") # Our new X-Ray log
        raise HTTPException(status_code=400, detail="Charger ID already exists or invalid.")
    finally:
        conn.close()
        
    return {"status":"success", "message": f"Charger {charger.charger_id} added successfully!"} 
@app.get("/api/chargers", dependencies=[Depends(get_current_user)])
def get_chargers():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM charger ORDER by charger_id")
    chargers = cursor.fetchall()
    
    cursor.execute("SELECT SUM(kwh_delivered) as total_energy FROM charging_sessions")
    result = cursor.fetchone()
    total_energy = result['total_energy'] if result and result['total_energy'] else 0.0

    conn.close()
    return{
        "chargers": chargers,
        "revenue": round(total_energy, 2),
        "energy": round(total_energy, 2)
    }

@app.delete("/api/chargers/{charger_id}", dependencies=[Depends(get_current_user)])
def delete_charger(charger_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM charger WHERE charger_id = %s", (charger_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete charger.")
    finally:
        conn.close()
    return {"status" : "success"}

@app.get("/api/chargers/{charger_id}/history", dependencies=[Depends(get_current_user)])
def get_charger_history(charger_id: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
           SELECT session_id, user_phone, start_time, end_time, kwh_delivered, status
           FROM charging_sessions
           WHERE charger_id = %s
           ORDER BY start_time DESC LIMIT 10
        """, (charger_id,))
    history = cursor.fetchall()
    conn.close()
    return{"history":history}
        
def control_charger(charger_id: str, action: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    if action == "start":
        cursor.execute("UPDATE charger SET status = 'CHARGING' WHERE charger_id = %s", (charger_id,))
        cursor.execute("INSERT INTO charging_sessions (charger_id, status, start_time) VALUES (%s, 'ACTIVE', NOW())", (charger_id,))
        requests.get(f"http://ocpp-server:8889/api/command?charger={charger_id}&action=start")
    elif action == "stop":
        cursor.execute("UPDATE charger SET status = 'AVAILABLE' WHERE charger_id = %s", (charger_id,))
        cursor.execute("UPDATE charging_sessions SET status = 'COMPLETED', end_time = NOW() WHERE charger_id = %s AND status = 'ACTIVE'", (charger_id,))
        requests.get(f"http://ocpp-server:8889/api/command?charger={charger_id}&action=stop")
    conn.commit()
    conn.close()
    return {"status" : "success"}

@app.get("/WhatsAppWebhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return "Forbidden"

@app.post("/WhatsAppWebhook")
async def webhook(request: Request):
    data = await request.json()
    try:
        entry = data['entry'][0]['changes'][0]['value']
        
        
        if 'statuses' in entry:
            return "OK"
            
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            
            if 'text' in msg:
                text = msg['text']['body'].lower().strip()
                payload = None
                print(f"📩 Received TEXT from {phone}: {text}") 
            elif 'interactive' in msg:
                text = ""
                payload = msg['interactive']['button_reply']['id']
                print(f"👆 Received BUTTON CLICK from {phone}: {payload}") 
            else:
                return "OK"
        
            process_message(phone, text, payload)
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return "OK"
#Java and python communication
@app.post("/api/internal/notify-stop/{charger_id}")
def notify_stop(charger_id: str):
    conn = get_db_connection()
    cursor= conn.cursor()

    cursor.execute("""
          SELECT user_phone FROM charging_sessions
          WHERE charger_id = %s
          ORDER BY start_time DESC LIMIT 1
    """, (charger_id,))

    result = cursor.fetchone()
    if result and result[0]:
        phone = result[0]
        message = f"Good news! Your vehicle at {charger_id} has finished charging and the session is closed. Safe travels!"
        send_whatsapp_message(phone, message)
        print(f"Weebhook recevied: Notified {phone} that {charger_id} stopped.")
    else:
        print(f"Webhook received, but no active phone number found for {charger_id}.")

    conn.close()
    return {"status":"success"}    

def process_message(phone, text, payload):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT charger_id FROM charging_sessions WHERE user_phone = %s AND status = 'ACTIVE'", (phone,))
    active_session = cursor.fetchone()

    #sesssion timeout
    current_time = time.time()
    last_active = user_last_active.get(phone, 0)
    
    #if user presses expired button
    if payload and not active_session and (current_time - last_active > SESSIONS_TIMEOUT_SECONDS):
        user_last_active[phone] = current_time
        send_interactive_buttons(phone, "⏳ Your previous session expired. Let's start a fresh! How can I assist you today? ", MAIN_MENU_BUTTONS)
        conn.close()
        return
    
    #update user activity clock
    user_last_active[phone] = current_time


    if payload:
        if payload.startswith("start_"):
            charger_id = payload.replace("start_","")

            send_whatsapp_message(phone, "🇬🇧 English selected.\n\n🔌 Please plug the connector securely into your vehicle now.")

            cursor.execute("UPDATE charger SET status = 'CHARGING' WHERE charger_id = %s", (charger_id,))
            cursor.execute("INSERT INTO charging_sessions (charger_id, user_phone, status, start_time) VALUES (%s,%s, 'ACTIVE', NOW())", (charger_id, phone))
            requests.get(f"http://ocpp-server:8889/api/command?charger={charger_id}&action=start")

            buttons = [
                {"id": "status_check", "title":"Check Status"},
                {"id": f"stop_{charger_id}", "title":"Stop Charging"}
            ]
            send_interactive_buttons(phone, f"⚡ Charging started at {charger_id}! Your session is active. What would you like to do?", buttons)
            
        elif payload == "cancel_start":
            send_interactive_buttons(phone, "❌ Session cancelled. When you are ready, please scan a charger QR code to begin.")
            
        elif payload.startswith("stop_"):
            charger_id = payload.replace("stop_","")
            cursor.execute("UPDATE charger SET status = 'AVAILABLE' WHERE charger_id = %s", (charger_id,))
            cursor.execute("UPDATE charging_sessions SET status = 'COMPLETED', end_time = NOW() WHERE charger_id = %s AND status = 'ACTIVE'", (charger_id,))
            requests.get(f"http://ocpp-server:8889/api/command?charger={charger_id}&action=stop")
            
            send_interactive_buttons(phone, f"Charging stopped for {charger_id}. Safe travels! Need Anything else?", MAIN_MENU_BUTTONS)

        elif payload == "status_check":
            if active_session:
                buttons = [{"id":"status_check","title":"🔄Refresh"},{"id": f"stop_{active_session['charger_id']}", "title":"Stop Charging"}]
                send_interactive_buttons(phone, f"Your vehicle is currently charging at {active_session['charger_id']}. Everything looks good!", buttons)
            else:
                send_interactive_buttons(phone, "You don't have any active charging sessions right now.", MAIN_MENU_BUTTONS)

        elif payload == "menu_history":
            cursor.execute("SELECT COUNT(*) as sessions, SUM(kwh_delivered) as total_energy FROM charging_sessions WHERE user_phone= %s AND status = 'COMPLETED'", (phone,))
            history = cursor.fetchone()
            s_count = history['sessions'] if history and history['sessions'] else 0
            e_sum = history['total_energy'] if history and history['total_energy'] else 0
            send_interactive_buttons(phone, f"📈 *Your History*\nYou have completed {s_count} past sessions, using {round(e_sum, 2)} kWh total.\nWhat's next?", MAIN_MENU_BUTTONS)
        elif payload == "menu_location":
            send_interactive_buttons(phone, f"📍 *Standard Bank Rosebank*\n12 Fast Charger Chargers available.\nOpen 24/7.", MAIN_MENU_BUTTONS)
        elif payload == "menu_charge":
            nav_buttons = [{"id":"menu_location","title": "📍Find Chargers"},{"id":"menu_history","title":"📈My Hitory"}]
            send_interactive_buttons(phone, "📷 *Ready to Charger!\nPlease open your phone's camera to scan QR code on charger to start?",nav_buttons)


    elif text:
        if text.startswith("qr_scan_"):
            if active_session:
                buttons = [{"id":"status_check","title":"📊 Status"},{"id": f"stop_{active_session['charger_id']}","title":"🛑 Stop"}]
                send_interactive_buttons(phone, f"⚠️ You are already charging at {active_session['charger_id']}.Please stop that session first.",buttons)
                return 
                
            scanned_charger = text.replace("qr_scan_", "").upper()
            cursor.execute("SELECT status FROM charger WHERE charger_id = %s", (scanned_charger, ))
            charger_data = cursor.fetchone()

            if not charger_data:
                send_interactive_buttons(phone, "❌ Invalid QR Code. This charger does not exist in our system.", MAIN_MENU_BUTTONS)
            elif charger_data['status'] != 'AVAILABLE':
                cursor.execute("SELECT charger_id FROM charger WHERE status = 'AVAILABLE' LIMIT 1")
                free_charger = cursor.fetchone()
                if free_charger:
                    send_interactive_buttons(phone, f"⚠️ Sorry, {scanned_charger} is currently in use!\n\n✅ Good news: Charger {free_charger['charger_id']} is available at this location. Please park there and scan its QR code instead.", MAIN_MENU_BUTTONS)
                else:
                    send_interactive_buttons(phone, "⚠️ Sorry, all chargers at this location are currently in use. Please check back later.", MAIN_MENU_BUTTONS)
            else:
                buttons = [
                    {"id": f"start_{scanned_charger}", "title":"⚡ Start Charging"},
                    {"id":"cancel_start","title":"❌ Cancel"}
                ]  
                send_interactive_buttons(phone, f"📍 Location: Standard Bank Midrand\n🔌 Charger: {scanned_charger}\n\nWould you like to start a session?", buttons)
            
        elif active_session:
            buttons = [{"id":"status_check","title":"📊 Status"},{"id": f"stop_{active_session['charger_id']}","title":"🛑 Stop"}]
            send_interactive_buttons(phone, f"⚠️ You are already charging at {active_session['charger_id']}.Please stop that session first.",buttons)
        else:
            
            send_interactive_buttons(phone, "Welcomer to Standard Bank EV Chargers!\nHow can I assist you today?", MAIN_MENU_BUTTONS)
    conn.commit()
    conn.close()
#login
@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    #update this later
    if form_data.username == "admin" and form_data.password == "StandardBank2026!":
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        #payload
        to_encode = {"sub": form_data.username, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)

        return {"access_token": encoded_jwt, "token_type":"bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=5000, reload=True)