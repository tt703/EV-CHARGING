import pg8000.native

# --- CONFIGURATION ---
DB_HOST = "ev-charging-db.postgres.database.azure.com"
DB_NAME = "postgres"
DB_USER = "evadmin"
DB_PASS = "Tlotlo22tt#"

def fix_database():
    print("🔧 Starting Database Repair...")
    
    try:
        conn = pg8000.native.Connection(
            user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME, ssl_context=True
        )

        # 1. FIX COLUMN TYPE (Integer -> Float)
        # We use ALTER TABLE to change the data structure permanently
        print("... Converting 'power_kw' from Integer to Float")
        conn.run("ALTER TABLE chargers ALTER COLUMN power_kw TYPE FLOAT")
        
        # 2. CORRECT THE DATA (ZA-ABB-001)
        # Now that it can hold decimals, we set it back to 7.5 (it was rounded to 8)
        print("... Correcting ZA-ABB-001 Power Rating")
        conn.run("UPDATE chargers SET power_kw = 7.5 WHERE charger_id = 'ZA-ABB-001'")
        # We use ALTER TABLE to change the data structure permanently
        print("... Converting 'cost_per_kwh' from Integer to Float")
        conn.run("ALTER TABLE chargers ALTER COLUMN cost_per_kwh TYPE FLOAT")

        # 3. FIX THE STATUS (active -> AVAILABLE)
        # This fixes the lowercase issue for the second charger
        print("... Fixing Status Typo for ZA-ABB-002")
        conn.run("UPDATE chargers SET status = 'AVAILABLE' WHERE charger_id = 'ZA-ABB-002'")

        print("✅ REPAIR COMPLETE.")
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_database()