import pg8000.native 

#configuration
DB_HOST ="ev-charging-db.postgres.database.azure.com"
DB_NAME ="postgres"
DB_USER ="evadmin"
DB_PASS ="Tlotlo22tt#"

def upgrade_database():
    """Connects to Azure Database for PostgreSQL and performs setup operations."""
    conn = pg8000.native.Connection(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        database=DB_NAME,
        port=5432,
        ssl_context=True
    )
    print("Upgrading Database Schema..")
    try:
        # Add. power_kw
        try:
            conn.run("""ALTER TABLE chargers ADD COLUMN power_kw FLOAT DEFAULT 7.5;""")
            print("Added 'power_kw' column.")
        except Exception:
            print("column 'power_kw' already exists.")
        
        # Add 'cost_per_kwh'
        try:
            conn.run("""ALTER TABLE chargers ADD COLUMN cost_per_kwh FLOAT DEFAULT 1.00;""")
        except Exception:
            print("column 'cost_per_kwh' already exists.")
        
        conn.run("""UPDATE chargers SET power_kw = 7.5, cost_per_kwh = 2.56 WHERE charger_id = 'ZA-ABB-001';""")
        conn.run("""UPDATE chargers SET location_name = 'HQ(Rosebank) - Basement Level 1 Charger 1' WHERE charger_id = 'ZA-ABB-001';""")
        conn.run("""INSERT INTO chargers (charger_id, location_name,connector_type, power_kw, cost_per_kwh, status) VALUES ('ZA-ABB-002', 'HQ(Rosebank) - Basement Level 1 Charger 2','Type 2', 25, 2.56, 'active');""")

        print("Database upgrade completed successfully.")
    except Exception as e:
        print(f"Error: {e}")

    conn.close()

if __name__ == "__main__":
    upgrade_database()