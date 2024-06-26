from flask import Flask, render_template, request, session, redirect, url_for, g
import sqlite3
import socket
from flask import jsonify
import logging
import bcrypt
from cryptography.fernet import Fernet
import sqlite3

 
logging.basicConfig(filename='debug.log', level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key

app.config['DATABASE'] = 'database.db'

# Generate a key for encryption
key = Fernet.generate_key()
cipher_suite = Fernet(key)

def init_db(app):
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db

def close_connection(exception=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Function to add a new user to the database
def add_user(username, password, ip_address):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO users (username, password, ip_address, is_online) VALUES (?, ?, ?, 0)", (username, password, ip_address))
    db.commit()

# Function to authenticate users that uses hashing
# Function to authenticate users
def authenticate_user(username, password):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT username, password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    if user:
        stored_encrypted_hashed_password = user[1]  # Assuming password is stored at index 1
        stored_hashed_password = decrypt_data(stored_encrypted_hashed_password)
        if isinstance(password, str):
            password = password.encode('utf-8')  # Convert string password to bytes
        if isinstance(stored_hashed_password, str):
            stored_hashed_password = stored_hashed_password.encode('utf-8')  # Convert stored hashed password to bytes
        try:
            if bcrypt.checkpw(password, stored_hashed_password):
                return user
        except ValueError:
            # Handle invalid salt error
            return None
    return None

# Function to fetch online users
def get_online_users():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT username FROM users WHERE is_online = 1")
    return [row[0] for row in c.fetchall()]

# Function to store chat messages
def upload_chat_to_db(sender, receiver, message, sender_ip):
    if len(message) == 0:
        return 'fail'
    
    encrypted_message = encrypt_data(message)
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO chats (sender, receiver, message, sender_ip) VALUES (?, ?, ?, ?)", (sender, receiver, encrypted_message, sender_ip))
    db.commit()
    return 'success'

def update_user_online_status(username, is_online):
    try:
        db = get_db()
        c = db.cursor()

        # Update the 'is_online' field for the specified user
        c.execute("UPDATE users SET is_online = ? WHERE username = ?", (is_online, username))
        db.commit()
        logging.debug(f'Successfully changed {username} status to {is_online}')
        print("User's online status updated successfully.")
        db.close()
        
    except sqlite3.Error as e:
        print("Error updating user's online status:", e)
        db.rollback()
    finally:
        db.close()
        
# Function to periodically update online status
def update_online_status():
    while True:
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET is_online = 0")  # Set all users as offline initially
            conn.commit()
            
            # Check if users are online based on IP address
            for user in get_online_users():
                user_ip = authenticate_user(user[0], user[1])[1]
                if ping(user_ip):
                    c.execute("UPDATE users SET is_online = 1 WHERE username = ?", (user,))
                    conn.commit()
            
            conn.close()
            time.sleep(60)  # Check online status every 60 seconds
        except:
            pass

# Ping function to check if IP address is reachable
def ping(ip_address):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Timeout for connection attempt
        result = sock.connect_ex((ip_address, 80))
        return result == 0
    except:
        return False
    finally:
        sock.close()

def hash_password(password):
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

# Encrypt data
def encrypt_data(data):
    if isinstance(data, str):
        data = data.encode()  # Convert string to bytes if necessary
    return cipher_suite.encrypt(data)

# Decrypt data
def decrypt_data(encrypted_data):
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    return decrypted_data.decode()  # Decode bytes to string


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    return render_template('index.html')

# Function to check password strength
def check_password_strength(password):
    # Define minimum requirements for a strong password
    min_length = 8
    has_lowercase = any(char.islower() for char in password)
    has_uppercase = any(char.isupper() for char in password)
    has_digit = any(char.isdigit() for char in password)
    
    # Check if the password meets the minimum requirements
    if len(password) < min_length or not has_lowercase or not has_uppercase or not has_digit:
        return False
    return True

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        ip_address = request.remote_addr

        # Data sanitization
        if not check_password_strength(password):
            return jsonify({'message': 'Password is inadequate. It must be at least 8 characters long and contain at least one lowercase letter, one uppercase letter, and one digit.', 'status_code':400}), 400

        
        # Use a try-finally block to ensure the connection is properly closed
        try:
            # Open a new connection
            conn = get_db()
            c = conn.cursor()
            
            # Execute your database operations
            encrypted_hashed_password = encrypt_data(hashed_password)
            encrypted_ip_address = encrypt_data(ip_address)
            c.execute("INSERT INTO users (username, password, ip_address, is_online) VALUES (?, ?, ?, 0)", (username, encrypted_hashed_password, encrypted_ip_address))
            conn.commit()

            # Return a JSON response
            response_data = {'message': 'User signed up successfully', 'status_code': 200}
            return jsonify(response_data), 200
        
        finally:
            # Close the connection
            conn.close()

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = authenticate_user(username, password)

    if user is not None:
        session['username'] = user[0]
        session['ip_address'] = user[1]      

        update_user_online_status(username, 1)
        response_data = {'message': 'User signed in successfully', 'status_code': 200}
        return jsonify(response_data), 200
    
    else:
        response_data = {'message': 'User sign in failed', 'status_code': 400}
        return jsonify(response_data), 400


@app.route('/chat', methods=['GET', 'POST'])
def chat():        
    if request.method == 'POST':
        sender_id = request.form['sender_id']
        receiver_id = request.form['receiver_id']
        message = request.form['message']
        sender_ip = request.remote_addr
        try:
            response = upload_chat_to_db(sender_id, receiver_id, message, sender_ip)
            if response == 'success':
                response_data = {'message': 'Chat sent successfully', 'status_code': 200}
                return jsonify(response_data), 200
            else:
                response_data = {'message': 'Content of message is inadequate', 'status_code': 400}
                return jsonify(response_data), 400


        except:
            response_data = {'message': 'Chat sent unsuccessfully', 'status_code': 401}
            return jsonify(response_data), 401

@app.route('/logout', methods=['POST'])
def logout():
    username = request.form['username']
    try:
        logging.debug(f'About to log user out')
        update_user_online_status(username, 0)
        response_data = {'message': 'Successfully logged user out', 'status_code': 200}
        return jsonify(response_data), 200
    
    except:
        logging.debug(f'Could not log user out')
        response_data = {'message': 'User logged out unsuccessfully', 'status_code': 400}
        return jsonify(response_data), 400

if __name__ == '__main__':
    import threading
    import time
    import os
    
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        init_db(app)

    # Start a background thread to update online status
    update_thread = threading.Thread(target=update_online_status)
    update_thread.daemon = True
    update_thread.start()
    
    app.run(debug=True)
