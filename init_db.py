import os
import psycopg2
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash

# Fallback string provided by you if the environment variable isn't set yet
NEON_DB_URL = os.environ.get(
    'DATABASE_URL', 
    'postgresql://neondb_owner:npg_UmcTfkaWHL39@ep-round-shape-ao30m667-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)

def init_db():
    print("Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(NEON_DB_URL)
    cursor = conn.cursor()

    # Drop existing tables cleanly if resetting
    cursor.execute('DROP TABLE IF EXISTS links CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS templates CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS tickets CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS prompts CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS sops CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS users CASCADE;')

    # Create Tables using Postgres Syntax (SERIAL instead of AUTOINCREMENT)
    cursor.execute('''
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    );''')

    cursor.execute('''
    CREATE TABLE links (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        is_universal INTEGER DEFAULT 0
    );''')

    cursor.execute('''
    CREATE TABLE templates (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        is_universal INTEGER DEFAULT 0
    );''')

    cursor.execute('''
    CREATE TABLE tickets (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        ticket_link TEXT NOT NULL,
        slack_link TEXT NOT NULL,
        status VARCHAR(100) DEFAULT 'Resolution Pending'
    );''')

    cursor.execute('''
    CREATE TABLE prompts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        is_universal INTEGER DEFAULT 0
    );''')

    cursor.execute('''
    CREATE TABLE sops (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        is_universal INTEGER DEFAULT 0
    );''')

    # Insert custom admin user: kitten / 1707
    hashed_pw = generate_password_hash('1707')
    cursor.execute(
        "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, 1) RETURNING id;", 
        ('kitten', hashed_pw)
    )
    admin_id = cursor.fetchone()[0]
    
    # Seed default universal workspace links assigned to admin account
    default_links = [
        (admin_id, "Google Sheet", "https://docs.google.com/spreadsheets/d/1mnfKgyBVN8d8ikm1trWpmyo1sAKk_SOXh3yZRbl9dgA/edit?gid=245013635#gid=245013635", 1),
        (admin_id, "Appsmith Finder", "https://app.appsmith.com/app/finder/", 1),
        (admin_id, "ChatGPT", "https://chatgpt.com/", 1),
        (admin_id, "Wint IR Portal", "https://wint-ir-portal.vercel.app/", 1),
        (admin_id, "Google Drive", "https://drive.google.com/drive/my-drive", 1)
    ]
    
    for link in default_links:
        cursor.execute("INSERT INTO links (user_id, name, url, is_universal) VALUES (%s, %s, %s, %s);", link)

    conn.commit()
    cursor.close()
    conn.close()
    print("Neon cloud database initialized successfully with user account 'kitten'!")

if __name__ == '__main__':
    init_db()