import sqlite3

DATABASE = 'employees.db'

def add_sample_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    sample_employees = [
        ('Alice Johnson', 'Engineering', 75000.0),
        ('Bob Smith', 'Human Resources', 45000.0),
        ('Charlie Brown', 'Marketing', 38000.0),
        ('Diana Prince', 'Engineering', 82000.0),
        ('Edward Norton', 'Sales', 52000.0),
        ('Fiona Gallagher', 'Finance', 61000.0),
        ('George Miller', 'IT Support', 42000.0),
        ('Hannah Abbott', 'Customer Success', 39000.0)
    ]
    
    cursor.executemany("INSERT INTO employee (name, department, salary) VALUES (?, ?, ?)", sample_employees)
    conn.commit()
    print(f"Added {len(sample_employees)} sample employees.")
    conn.close()

if __name__ == "__main__":
    add_sample_data()
