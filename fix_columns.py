import sqlite3

DB_PATH = "mimikly.db"  # Make sure this is the correct path to your DB file

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Add 'data' column to 'photos' if not exists
c.execute("PRAGMA table_info(photos)")
columns = [col[1] for col in c.fetchall()]
if 'data' not in columns:
    print("Adding 'data' column to photos table...")
    c.execute("ALTER TABLE photos ADD COLUMN data BLOB")

# Add 'file' column to 'voices' if not exists
c.execute("PRAGMA table_info(voices)")
columns = [col[1] for col in c.fetchall()]
if 'file' not in columns:
    print("Adding 'file' column to voices table...")
    c.execute("ALTER TABLE voices ADD COLUMN file BLOB")

conn.commit()
conn.close()

print("✅ Columns updated successfully.")
