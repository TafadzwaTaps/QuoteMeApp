import sqlite3

DB_FILE = "database.db"  # make sure this is the correct path

def fix_quotes_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check current columns
    cursor.execute("PRAGMA table_info(quotes)")
    columns = [col[1] for col in cursor.fetchall()]
    print("Existing columns:", columns)

    # If table already has the correct columns, nothing to do
    required_columns = {"id", "text", "author", "image_url"}
    if required_columns.issubset(set(columns)):
        print("Table 'quotes' already has all required columns. No changes needed.")
        conn.close()
        return

    print("Fixing 'quotes' table...")

    # Rename old table
    cursor.execute("ALTER TABLE quotes RENAME TO old_quotes")

    # Create new table with correct schema
    cursor.execute("""
        CREATE TABLE quotes (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            author TEXT,
            image_url TEXT
        )
    """)

    # Copy data from old table
    # Only copy columns that exist in old table
    copy_columns = [col for col in ["id", "text", "author", "image_url"] if col in columns]
    columns_str = ", ".join(copy_columns)
    cursor.execute(f"""
        INSERT INTO quotes ({columns_str})
        SELECT {columns_str} FROM old_quotes
    """)

    # Drop old table
    cursor.execute("DROP TABLE old_quotes")

    conn.commit()
    conn.close()
    print("Quotes table fixed successfully!")

if __name__ == "__main__":
    fix_quotes_table()
