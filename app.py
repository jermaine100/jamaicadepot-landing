from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow requests from your domain

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST'),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            port=os.environ.get('PGPORT', 5432)
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

# Initialize database - create table if it doesn't exist
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS waitlist_entries (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                whatsapp VARCHAR(20),
                notification_preference VARCHAR(20) DEFAULT 'email',
                interest_type VARCHAR(20) DEFAULT 'both',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

# Waitlist submission endpoint
@app.route('/api/waitlist', methods=['POST'])
def add_to_waitlist():
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        email = data.get('email').strip().lower()
        name = data.get('name', '').strip() if data.get('name') else ''
        whatsapp = data.get('whatsapp', '').strip() if data.get('whatsapp') else ''
        notification_preference = data.get('notification_preference', 'email')
        interest_type = data.get('interest_type', 'both')
        
        # Validate notification preference
        if notification_preference not in ['email', 'whatsapp', 'both']:
            notification_preference = 'email'
        
        # Validate interest type
        if interest_type not in ['vendor', 'buyer', 'both']:
            interest_type = 'both'
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if email already exists
        cur.execute('SELECT id FROM waitlist_entries WHERE email = %s', (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'This email is already registered'}), 409
        
        # Insert new entry
        cur.execute('''
            INSERT INTO waitlist_entries (email, name, whatsapp, notification_preference, interest_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (email, name, whatsapp, notification_preference, interest_type))
        
        entry_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'message': 'Successfully added to waitlist!',
            'id': entry_id
        }), 201
        
    except psycopg2.IntegrityError:
        return jsonify({'error': 'This email is already registered'}), 409
    except Exception as e:
        print(f"Error adding to waitlist: {e}")
        return jsonify({'error': 'Server error. Please try again later.'}), 500

if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
