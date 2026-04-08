import sqlite3

def migrate():
    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()
    
    # Check if join_date column exists in employee table
    cursor.execute("PRAGMA table_info(employee)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'join_date' not in columns:
        print("Adding 'join_date' column to 'employee' table...")
        cursor.execute("ALTER TABLE employee ADD COLUMN join_date TEXT DEFAULT CURRENT_DATE")
        conn.commit()
    else:
        print("'join_date' already exists.")
        
    conn.close()

if __name__ == "__main__":
    migrate()
