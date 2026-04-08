import sqlite3

DATABASE = 'employees.db'

def check_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Employees ---")
    employees = cursor.execute("SELECT * FROM employee").fetchall()
    for row in employees:
        print(dict(row))
        
    print("\n--- Users ---")
    users = cursor.execute("SELECT * FROM users").fetchall()
    for row in users:
        print(dict(row))
        
    conn.close()

if __name__ == "__main__":
    check_db()
