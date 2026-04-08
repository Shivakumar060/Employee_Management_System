from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import csv
import io
from datetime import datetime, date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "apexcorp_production_secret_key"

# Database configuration
DATABASE = 'employees.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(action):
    """Log an activity with current user and timestamp."""
    user_id = session.get('user_id')
    username = session.get('username', 'System')
    conn = get_db_connection()
    conn.execute('INSERT INTO activity_logs (user_id, username, action) VALUES (?, ?, ?)',
                 (user_id, username, action))
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    
    # Employee table (Updated with join_date)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS employee (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            salary REAL NOT NULL,
            join_date TEXT DEFAULT CURRENT_DATE
        )
    ''')
    
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    
    # Attendance table (id, emp_id, date, status)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(user_id, date)
        )
    ''')
    
    # Leaves table (id, emp_id, reason, start_date, end_date, status)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    
    # Activity Logs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Default admin
    admin_exists = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin_exists:
        hashed_pw = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     ('admin', hashed_pw, 'admin'))
    
    conn.commit()
    conn.close()

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            log_activity(f"Logged in as {user['role']}")
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            hashed_pw = generate_password_hash(password)
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                         (username, hashed_pw, 'user'))
            conn.commit()
            log_activity(f"New user registered: {username}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Username already exists!', 'danger')
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/logout')
def logout():
    log_activity("Logged out")
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            hashed_pw = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_pw, username))
            conn.commit()
            log_activity(f"Password reset for {username}")
            flash('Password updated successfully!', 'success')
            return redirect(url_for('login'))
        flash('User not found!', 'danger')
        conn.close()
    return render_template('reset_password.html')

# --- DASHBOARD & ANALYTICS ---

@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employee').fetchall()
    total_employees = len(employees)
    
    # Summary stats
    depts = set(e['department'] for e in employees)
    total_depts = len(depts)
    avg_salary = sum(e['salary'] for e in employees) / total_employees if total_employees > 0 else 0
    
    # Recent logs for admin
    logs = []
    if session.get('role') == 'admin':
        logs = conn.execute('SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 5').fetchall()
    
    # User specific attendance check
    today_marked = False
    if session.get('role') == 'user':
        attendance = conn.execute('SELECT * FROM attendance WHERE user_id = ? AND date = ?',
                                   (session['user_id'], date.today().isoformat())).fetchone()
        if attendance: today_marked = True

    conn.close()
    return render_template('dashboard.html', 
                          total_employees=total_employees, 
                          total_depts=total_depts, 
                          avg_salary=avg_salary,
                          logs=logs, today_marked=today_marked)

# --- API FOR CHARTS ---

@app.route('/api/stats')
@login_required
def get_stats():
    conn = get_db_connection()
    
    # Dept distribution
    dept_data = conn.execute('SELECT department, COUNT(*) as count FROM employee GROUP BY department').fetchall()
    
    # Salary brackets
    salary_data = conn.execute('SELECT salary FROM employee').fetchall()
    
    # Hiring trends (mock or actual)
    hiring_data = conn.execute('SELECT join_date, COUNT(*) as count FROM employee GROUP BY join_date ORDER BY join_date').fetchall()
    
    conn.close()
    return jsonify({
        'depts': {row['department']: row['count'] for row in dept_data},
        'salaries': [r['salary'] for r in salary_data],
        'hiring': {row['join_date']: row['count'] for row in hiring_data}
    })

@app.route('/api/stats/dept')
@login_required
def get_dept_stats():
    try:
        conn = get_db_connection()
        dept_data = conn.execute('SELECT department, COUNT(*) as count FROM employee GROUP BY department').fetchall()
        conn.close()
        data = {row['department']: row['count'] for row in dept_data}
        print(f"DEBUG: Dept stats requested - {data}")
        return jsonify(data)
    except Exception as e:
        print(f"ERROR in /api/stats/dept: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats/salary')
@login_required
def get_salary_stats():
    try:
        conn = get_db_connection()
        salary_data = conn.execute('SELECT salary FROM employee').fetchall()
        conn.close()
        salaries = [r['salary'] for r in salary_data]
        # Basic grouping for charts
        brackets = {
            'Economic (<40k)': len([s for s in salaries if s < 40000]),
            'Standard (40k-80k)': len([s for s in salaries if 40000 <= s < 80000]),
            'Premium (80k+)': len([s for s in salaries if s >= 80000])
        }
        print(f"DEBUG: Salary stats requested - {brackets}")
        return jsonify(brackets)
    except Exception as e:
        print(f"ERROR in /api/stats/salary: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# --- EMPLOYEE MANAGEMENT ---

@app.route('/view')
@login_required
def view_employees():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employee').fetchall()
    conn.close()
    return render_template('view_employees.html', employees=employees)

@app.route('/employee/<int:id>')
@login_required
def employee_profile(id):
    conn = get_db_connection()
    emp = conn.execute('SELECT * FROM employee WHERE id = ?', (id,)).fetchone()
    if not emp:
        flash('Employee not found!', 'danger')
        return redirect(url_for('view_employees'))
    
    # Fetch attendance summary (if linked via name/username matching, or just stats)
    # Since 'employee' and 'users' are separate, we match by Name for simple version
    # Realistic version would link by ID
    attendance = conn.execute('SELECT COUNT(*) as count FROM attendance WHERE user_id = (SELECT id FROM users WHERE username = ?)', (emp['name'],)).fetchone()
    leaves = conn.execute('SELECT * FROM leaves WHERE user_id = (SELECT id FROM users WHERE username = ?)', (emp['name'],)).fetchall()
    
    conn.close()
    return render_template('profile_view.html', emp=emp, attendance_count=attendance['count'], leaves=leaves)

@app.route('/add', methods=['GET', 'POST'])
@admin_required
def add_employee():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            dept = request.form.get('department')
            sal = request.form.get('salary')
            
            if not name or not dept or not sal:
                flash('All fields are required!', 'danger')
                return redirect(url_for('add_employee'))

            conn = get_db_connection()
            conn.execute('INSERT INTO employee (name, department, salary) VALUES (?, ?, ?)', (name, dept, sal))
            conn.commit()
            conn.close()
            
            print(f"DEBUG: Successfully added employee - {name}")
            log_activity(f"Added employee: {name}")
            flash('Employee added!', 'success')
            return redirect(url_for('view_employees'))
        except Exception as e:
            print(f"ERROR in add_employee: {str(e)}")
            flash(f'Error adding employee: {str(e)}', 'danger')
            return redirect(url_for('add_employee'))
    return render_template('add_employee.html')


@app.route('/update/<int:id>', methods=['GET', 'POST'])
@admin_required
def update_employee(id):
    conn = get_db_connection()
    emp = conn.execute('SELECT * FROM employee WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            dept = request.form.get('department')
            sal = request.form.get('salary')
            
            conn.execute('UPDATE employee SET name = ?, department = ?, salary = ? WHERE id = ?', (name, dept, sal, id))
            conn.commit()
            conn.close()
            
            print(f"DEBUG: Successfully updated employee ID - {id}")
            log_activity(f"Updated employee ID: {id}")
            flash('Employee updated!', 'success')
            return redirect(url_for('view_employees'))
        except Exception as e:
            print(f"ERROR in update_employee: {str(e)}")
            flash(f'Error updating employee: {str(e)}', 'danger')
            return redirect(url_for('view_employees'))

    conn.close()
    return render_template('edit_employee.html', employee=emp)

@app.route('/delete/<int:id>', methods=['POST'])
@admin_required
def delete_employee(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM employee WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        print(f"DEBUG: Successfully deleted employee ID - {id}")
        log_activity(f"Deleted employee ID: {id}")
        flash('Employee removed.', 'success')
    except Exception as e:
        print(f"ERROR in delete_employee: {str(e)}")
        flash(f'Error removing employee: {str(e)}', 'danger')
    return redirect(url_for('view_employees'))


# --- ATTENDANCE & LEAVES ---

@app.route('/mark-attendance', methods=['POST'])
@login_required
def mark_attendance():
    today = date.today().isoformat()
    user_id = session['user_id']
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO attendance (user_id, date, status) VALUES (?, ?, ?)', (user_id, today, 'Present'))
        conn.commit()
        log_activity("Marked attendance")
        flash('Attendance marked for today!', 'success')
    except:
        flash('Attendance already marked for today!', 'warning')
    finally:
        conn.close()
    return redirect(url_for('dashboard'))

@app.route('/leaves', methods=['GET', 'POST'])
@login_required
def manage_leaves():
    conn = get_db_connection()
    if request.method == 'POST':
        user_id, reason = session['user_id'], request.form['reason']
        start, end = request.form['start_date'], request.form['end_date']
        conn.execute('INSERT INTO leaves (user_id, reason, start_date, end_date) VALUES (?, ?, ?, ?)',
                     (user_id, reason, start, end))
        conn.commit()
        log_activity("Applied for leave")
        flash('Leave application submitted!', 'success')
        return redirect(url_for('manage_leaves'))
    
    if session['role'] == 'admin':
        # Join with users to see usernames
        leaves = conn.execute('SELECT l.*, u.username FROM leaves l JOIN users u ON l.user_id = u.id ORDER BY l.id DESC').fetchall()
    else:
        leaves = conn.execute('SELECT * FROM leaves WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('leaves.html', leaves=leaves)

@app.route('/leave/<string:action>/<int:id>')
@admin_required
def process_leave(action, id):
    status = 'Approved' if action == 'approve' else 'Rejected'
    conn = get_db_connection()
    conn.execute('UPDATE leaves SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    log_activity(f"Leave ID {id} {status}")
    flash(f'Leave {status}!', 'success')
    conn.close()
    return redirect(url_for('manage_leaves'))

@app.route('/admin/logs')
@admin_required
def view_logs():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM activity_logs ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template('admin_logs.html', logs=logs)

# --- EXPORT ---

@app.route('/export/csv')
@admin_required
def export_csv():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employee').fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Department', 'Salary', 'Join Date'])
    for emp in employees:
        writer.writerow([emp['id'], emp['name'], emp['department'], emp['salary'], emp['join_date']])
    
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='employees.csv')

@app.route('/export/pdf')
@admin_required
def export_pdf():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employee').fetchall()
    conn.close()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("ApexCorp Employee Directory", styles['Title']))
    
    data = [['ID', 'Name', 'Department', 'Salary']]
    for emp in employees:
        data.append([emp['id'], emp['name'], emp['department'], f"INR {emp['salary']:,.2f}"])
    
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='employees.pdf', mimetype='application/pdf')

# --- PROFILE (Updated) ---

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    attendance_count = conn.execute('SELECT COUNT(*) as count FROM attendance WHERE user_id = ?', (session['user_id'],)).fetchone()
    leave_status = conn.execute('SELECT status, COUNT(*) as count FROM leaves WHERE user_id = ? GROUP BY status', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('profile.html', attendance_count=attendance_count['count'], leave_status=leave_status)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
