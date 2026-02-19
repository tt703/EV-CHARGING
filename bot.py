from fastapi import FastAPI, Request
import psycopg2
import uvicorn
import requests

app = FastAPI()

#Database Config
DB_HOST="jdbc:postgresql://localhost:5432/postgres"
DB_NAME="postgres"
DB_USER="postgres"
DB_PASS="Tlotlo"
VERIFY_TOKEN="12345"

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

@app.get("/WhatsAppWebhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return "Forbidden"

@app.post("/WhatsAppWenhook")
async def webhook(request: Request):
    data = await request.json()
    try:
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            text = msg['text']['body'].lower().strip()

            process_message(phone, text)
    except:
        pass
    return "OK"

def process_message(phone, text):
    conn = get_db_connection()
    cursor = conn.cursor()

    #hardcoded for now
    charger_id = "ZA-ABB-001"

    cursor.execute("SELECT status FROM charger WHERE charger_id = %s", (charger_id,))
    result = cursor.fetchone()

    if not result:
        print(f"Charger {charger_id} not found in DB")
        return
    
    status = result[0]

    print(f"Bot received '{text}' from {phone}. Charger Status: {status}")

    #Logic
    if "hello" in text:
        print(f"REPLY: Hi! CHarger {charger_id} is {status}. /n Reply '1' to Start, /n'2' to Cancel.")
    
    elif text == "1":
        if status == "AVAILABLE":
            cursor.execute("UPDATE charger SET status = 'CHARGING' WHERE charger_id = %s", (charger_id,))
            cursor.execute("INSERT INTO charging_sessions (charger_id, user_phone, status, start_time) " \
            "VALUES (%s,%s, 'ACTIVE', NOW())", (charger_id, phone))
            print("Bot started charging via DB.")
        else:
            print("Cannot start. Already busy.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=5000, reload=True)
    
