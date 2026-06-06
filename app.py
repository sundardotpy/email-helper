import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Secure fallback secret key for production environments
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_ops_key_production_9981')

NEON_DB_URL = os.environ.get(
    'DATABASE_URL',
)

def get_db_connection():
    # Connects to your cloud Neon DB using DictCursor to match the dictionary style formatting
    conn = psycopg2.connect(NEON_DB_URL, cursor_factory=DictCursor)
    return conn

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'error')
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (%s, %s, 0)', 
                       (username, generate_password_hash(password)))
        conn.commit()
        flash('Registration successful! Please log in.', 'success')
    except psycopg2.IntegrityError:
        flash('Username already taken.', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    uid = session['user_id']
    is_admin = session['is_admin']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if is_admin:
        cursor.execute('SELECT * FROM links ORDER BY id DESC')
        links = cursor.fetchall()
        cursor.execute('SELECT * FROM templates ORDER BY id DESC')
        templates = cursor.fetchall()
        cursor.execute('SELECT * FROM tickets ORDER BY id DESC')
        tickets = cursor.fetchall()
        cursor.execute('SELECT * FROM prompts ORDER BY id DESC')
        prompts = cursor.fetchall()
        cursor.execute('SELECT * FROM sops ORDER BY id DESC')
        sops = cursor.fetchall()
        cursor.execute('SELECT id, username, is_admin FROM users WHERE id != %s ORDER BY id DESC', (uid,))
        all_users = cursor.fetchall()
    else:
        cursor.execute('SELECT * FROM links WHERE user_id = %s OR is_universal = 1 ORDER BY id DESC', (uid,))
        links = cursor.fetchall()
        cursor.execute('SELECT * FROM templates WHERE user_id = %s OR is_universal = 1 ORDER BY id DESC', (uid,))
        templates = cursor.fetchall()
        cursor.execute('SELECT * FROM tickets WHERE user_id = %s ORDER BY id DESC', (uid,))
        tickets = cursor.fetchall()
        cursor.execute('SELECT * FROM prompts WHERE user_id = %s OR is_universal = 1 ORDER BY id DESC', (uid,))
        prompts = cursor.fetchall()
        cursor.execute('SELECT * FROM sops WHERE user_id = %s OR is_universal = 1 ORDER BY id DESC', (uid,))
        sops = cursor.fetchall()
        all_users = []

    cursor.close()
    conn.close()
    return render_template('dashboard.html', links=links, templates=templates, tickets=tickets, prompts=prompts, sops=sops, all_users=all_users)

@app.route('/add/<item_type>', methods=['POST'])
def add_item(item_type):
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    is_universal = 1 if (session['is_admin'] and request.form.get('is_universal')) else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if item_type == 'link':
        cursor.execute('INSERT INTO links (user_id, name, url, is_universal) VALUES (%s, %s, %s, %s)', (uid, request.form['name'], request.form['url'], is_universal))
    elif item_type == 'template':
        cursor.execute('INSERT INTO templates (user_id, title, content, is_universal) VALUES (%s, %s, %s, %s)', (uid, request.form['title'], request.form['content'], is_universal))
    elif item_type == 'ticket':
        cursor.execute('INSERT INTO tickets (user_id, ticket_link, slack_link, status) VALUES (%s, %s, %s, %s)', (uid, request.form['ticket_link'], request.form['slack_link'], request.form['status']))
    elif item_type == 'prompt':
        cursor.execute('INSERT INTO prompts (user_id, title, content, is_universal) VALUES (%s, %s, %s, %s)', (uid, request.form['title'], request.form['content'], is_universal))
    elif item_type == 'sop':
        cursor.execute('INSERT INTO sops (user_id, name, url, is_universal) VALUES (%s, %s, %s, %s)', (uid, request.form['name'], request.form['url'], is_universal))
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/edit_sop/<int:id>', methods=['POST'])
def edit_sop(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sops WHERE id = %s', (id,))
    sop = cursor.fetchone()
    
    if sop:
        if session['is_admin'] or sop['user_id'] == uid:
            cursor.execute('UPDATE sops SET name = %s, url = %s WHERE id = %s', (request.form['name'], request.form['url'], id))
            conn.commit()
            
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete/<item_type>/<int:id>')
def delete_item(item_type, id):
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    
    table_map = {'link': 'links', 'template': 'templates', 'ticket': 'tickets', 'prompt': 'prompts', 'sop': 'sops'}
    if item_type not in table_map: return redirect(url_for('dashboard'))
    
    table = table_map[item_type]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {table} WHERE id = %s', (id,))
    item = cursor.fetchone()
    
    if item:
        if session['is_admin'] or (item['user_id'] == uid and item.get('is_universal', 0) == 0):
            cursor.execute(f'DELETE FROM {table} WHERE id = %s', (id,))
            conn.commit()
            
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/admin/delete_user/<int:id>')
def delete_user(id):
    if not session.get('is_admin'): return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Dynamic port extraction specifically for Render environment managers
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port,debug=True)