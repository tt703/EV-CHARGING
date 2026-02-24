import psycopg2

print("Connecting to Docker Database...")

# Connects to the Postgres container exposed on your computer's port 5432
# Change your DB_DSN line to look exactly like this:
DB_DSN = "postgresql://postgres:Tlotlo@127.0.0.1:5433/ev_charging"

try:
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # 1. Create the Charger Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS charger (
        charger_id VARCHAR(50) PRIMARY KEY,
        status VARCHAR(20) NOT NULL
    )
    ''')

    # 2. Create the Sessions Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS charging_sessions (
        session_id SERIAL PRIMARY KEY,
        charger_id VARCHAR(50),
        user_phone VARCHAR(20),
        status VARCHAR(20),
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        kwh_delivered FLOAT DEFAULT 0.0
    )
    ''')

    # 3. Insert your first charger
    cur.execute("INSERT INTO charger (charger_id, status) VALUES ('ZA-ABB-001', 'AVAILABLE') ON CONFLICT DO NOTHING")

    conn.commit()
    conn.close()
    print("✅ Database successfully populated with tables and ZA-ABB-001!")

except Exception as e:
    print(f"❌ Database error: {e}")