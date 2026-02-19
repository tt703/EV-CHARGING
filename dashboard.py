from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2.extras import RealDictCursor
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

#Database Config
DB_HOST ="localhost"
DB_NAME ="postgres"
DB_USER ="postgres"
DB_PASS ="Tlotlo"

def  get_db_connection():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER,password=DB_PASS)
    return conn
#Dashboard Ui
@app.get("/",response_class=HTMLResponse)
async def home(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    #get chargers
    cursor.execute("SELECT * FROM charger ORDER by charger_id")
    chargers = cursor.fetchall()

    #calculate totals
    cursor.execute("SELECT SUM(kwh_delivered) as total_energy FROM charging_sessions")
    result = cursor.fetchone()
    total_energy = result['total_energy'] if result['total_energy'] else 0.0
    total_cost = total_energy #should be cost from the machine

    conn.close()

    return templates.TemplateResponse("dashboard.html",{
        "request": request,
        "chargers": chargers,
        "revenue":round(total_cost, 2),
        "energy": round(total_energy, 2)
    })
#Controls
@app.get("/command/{charger_id}/{action}")
async def control_charger(charger_id: str, action: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    if action == "start":
        #updates charger status
        cursor.execute("UPDATE charger SET status = 'CHARGING' WHERE charger_id = %s", (charger_id,))
        #create session
        cursor.execute("INSERT INTO charging_sessions (charger_id, status, start_time) VALUES (%s, 'ACTIVE', NOW())", (charger_id,))

    elif action == "stop":
        #update charger status
        cursor.execute("UPDATE charger SET status = 'AVAILABLE' WHERE charger_id=%s", (charger_id,))
        #close session
        cursor.execute("UPDATE charging_sessions SET status = 'COMPLETED', end_time= NOW() WHERE charger_id = %s AND status = 'ACTIVE'", (charger_id,))
    
    conn.commit()
    conn.close()

    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=True)
