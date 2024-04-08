import requests
import sqlite3
import socket
import pytest


BASE_URL = 'http://127.0.0.1:5000'

def signup(username, password):
    url = f'{BASE_URL}/signup'
    data = {'username': username, 'password': password}
    response = requests.post(url, data=data)
    response = response.json()
    return response

def login(username, password):
    url = f'{BASE_URL}/login'
    data = {'username': username, 'password': password}
    response = requests.post(url, data=data)
    response = response.json()
    return response

def chat(sender_id, receiver_id, message):
    url = f'{BASE_URL}/chat'
    data = {'sender_id': sender_id, 'receiver_id': receiver_id, 'message': message}
    response = requests.post(url, data=data)
    response = response.json()
    return response

def search_online_users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE is_online = 1")
    online_users = [row[0] for row in c.fetchall()]
    conn.close()
    print('Online users:', online_users)

def logout(username):
    url = f'{BASE_URL}/logout'
    data = {'username': username}
    response = requests.post(url, data=data)
    response = response.json()
    return response

def ping(ip_address):
    # Implement ping functionality here
    # Example: Use socket to check if the IP address is reachable
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Timeout for connection attempt
        result = sock.connect_ex((ip_address, 80))
        return result == 0
    except:
        return False
    finally:
        sock.close()

# Unit tests
@pytest.mark.parametrize("username, password", [
    ('khang', 'password'),  
    ('adam', 'khang123'),  
])
def test_signup(username, password):

    response = signup(username, password)
    assert response['message'] == 'User signed up successfully'
    assert response['status_code'] == 200


# Unit tests
@pytest.mark.parametrize("username, password", [
    ('khang', 'password'),  
    ('adam', 'khang123'),  
])
def test_login(username, password):

    response = login(username, password)
    assert response['message'] == 'User signed in successfully'
    assert response['status_code'] == 200


@pytest.mark.parametrize("sender_id, receiver_id, message", [
    ('khang', 'adam', 'hello, this is a test message from user: khang'),  
    ('adam', 'khang', 'hello khang, my username is adam'),  
])
def test_chat(sender_id, receiver_id, message):
    response = chat(sender_id, receiver_id, message)
    assert response['message'] == 'Chat sent successfully'
    assert response['status_code'] == 200

@pytest.mark.parametrize("username", [
    ('khang'),  
    ('adam'), 
])

def test_logout(username):
    response = logout(username)
    assert response['message'] == 'Successfully logged user out'
    assert response['status_code'] == 200
