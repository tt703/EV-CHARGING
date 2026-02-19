import pg8000.native
import pandas as pd

# --- CONFIGURATION ---
DB_HOST = "ev-charging-db.postgres.database.azure.com"
DB_NAME = "postgres"
DB_USER = "evadmin"
DB_PASS = "Tlotlo22tt#"

def verify_database():
    print("🔎 Connecting to Database for Audit...")
    
    try:
        conn = pg8000.native.Connection(
            user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME, ssl_context=True
        )

        # --- TEST 1: VERIFY DATA TYPES ---
        print("\n📋 TEST 1: TABLE SCHEMA (Data Types)")
        # This query asks the database itself "What types are these columns?"
        schema_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'chargers'
        ORDER BY ordinal_position;
        """
        schema_results = conn.run(schema_query)
        df_schema = pd.DataFrame(schema_results, columns=["Column Name", "Data Type"])
        print(df_schema.to_string(index=False))

        # --- TEST 2: VERIFY INSERTED DATA ---
        print("\n📊 TEST 2: ACTUAL DATA")
        data_query = "SELECT charger_id, location_name, power_kw, cost_per_kwh, status FROM chargers ORDER BY charger_id"
        data_results = conn.run(data_query)
        
        if data_results:
            df_data = pd.DataFrame(data_results, columns=["ID", "Location", "Power (kW)", "Cost (R/kWh)", "Status"])
            print(df_data.to_string(index=False))
        else:
            print("⚠️ Table is empty!")

        conn.close()
        print("\n✅ Verification Complete.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_database()