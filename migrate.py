import sqlite3

def migrate():
    conn = sqlite3.connect('shots.db')
    try:
        # This adds the placement column to your existing table
        conn.execute('ALTER TABLE shots ADD COLUMN image_url TEXT DEFAULT ""')
        conn.execute('ALTER TABLE shots ADD COLUMN placement TEXT DEFAULT ""')
        conn.commit()
        print("Migration successful: 'placement' column added.")
    except sqlite3.OperationalError:
        print("Column 'placement' likely already exists.")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()