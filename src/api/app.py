from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sqlite3
import os
from uuid import uuid4

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'database.db')
DB_PATH = os.path.abspath(DB_PATH)

PHOTO_DIR = "photos"

latest_uuid = None

def init_db() :
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users_reg (
                       id INTEGER PRIMARY KEY,
                       uuid TEXT NOT NULL,
                       user_id TEXT NOT NULL,
                       first_name TEXT NOT NULL,
                       last_name TEXT NOT NULL,
                       email TEXT NOT NULL,
                       role TEXT NOT NULL DEFAULT 'student'
                   )
                   ''')
    conn.commit()
    conn.close()
    
def get_users() :
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * from users_reg')
    users = cursor.fetchall()
    cursor.close()
    return users

def get_user_by_uuid(uuid) :
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT uuid, user_id, first_name, last_name, email, role FROM users_reg WHERE uuid = ?', (uuid,))
    row = cursor.fetchone()
    conn.close()
    if row :
        return {"uuid": row[0], 'user_id': row[1], 'first_name': row[2], 'last_name': row[3], 'email' : row[4], 'role' : row[5]}
    else :
        return None

def add_user(uuid , user_id, first_name, last_name, email) :
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users_reg (uuid, user_id, first_name, last_name, email) VALUES (?, ?, ?, ?, ?)', (uuid, user_id, first_name, last_name, email))
    conn.commit()
    cursor.close()
    conn.close()

def delete_user(id) :
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users_reg WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    
@app.route('/')
def index() :
    users = get_users()
    return render_template('index.html', users=users)

@app.route('/api/send_uuid', methods=['POST'])
def get_uuid() :
    global latest_uuid
    data = request.get_json()
    uuid = data.get('uuid')
    latest_uuid = uuid
    
    user = get_user_by_uuid(latest_uuid)
    user_id = user['user_id'] if user else ''
    first_name = user['first_name'] if user else ''
    last_name = user['last_name'] if user else ''
    email = user['email'] if user else ''
    
    socketio.emit('uuid_update', {'uuid': latest_uuid, 'user_id': user_id, 'first_name' : first_name, 'last_name' : last_name, 'email': email})
    if (uuid) :
        return jsonify({ "message" : f" This is your {uuid}"})
    else : 
        return jsonify({"error" : "Please scan rfid to get your uuid"}), 400

@app.route('/api/latest_uuid', methods=['GET'])
def get_latest_uid():
    print(user)
    user = get_user_by_uuid(latest_uuid)
    if user :
        return jsonify({'uuid': user['uuid'], 'user_id' : user['user_id'], 'first_name' : user['first_name'], 'last_name' : user['last_name'], 'email': user['email']})
    else :
        return jsonify({'uuid': latest_uuid})

@app.route('/api/reset_uuid', methods=['POST'])
def reset_uuid():
    global latest_uuid
    latest_uuid = None
    return jsonify({ 'success' : True})

# @app.route('/api/upload', methods=['POST'])
# def upload():
#     img_data = request.data
#     if not os.path.exists(PHOTO_DIR):
#         os.makedirs(PHOTO_DIR)
#     image_name = str(uuid4()) + '.jpg'
#     fileName = os.path.join(PHOTO_DIR, image_name)
#     with open(fileName, "wb") as f:
#         f.write(img_data)
        
#     rel_path = f"{PHOTO_DIR}/{image_name}"
#     return jsonify({"success": True, "path_file": rel_path})
   
# @app.route('/photos/<file_name>')
# def serve_photo(file_name):
#     return send_from_directory(PHOTO_DIR, file_name)
    
@app.route('/api/add_user', methods=['POST']) 
def add_user_route():
    global latest_uuid
    uuid = request.form['uuid']
    user_id = request.form['user_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT uuid FROM users_reg WHERE uuid = ?', (uuid,)) 
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({'message': 'Have this uuid already'}), 409

    add_user(uuid, user_id, first_name, last_name, email)
    latest_uuid = ""
    return jsonify({'message': 'User added successfully'})

@app.route('/api/delete_user/<int:id>', methods=['GET'])
def delete_user_route(id) :
    delete_user(id)
    return redirect(url_for('index'))

@app.route('/api/edit_user/<int:id>', methods=['GET'])
def edit_user_route(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, uuid, user_id, first_name, last_name, email FROM users_reg WHERE id = ?', (id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return render_template('edit_user.html', user=user)
    return redirect(url_for('index'))

@app.route('/api/update_user/<int:id>', methods=['POST'])
def update_user_route(id):
    uuid = request.form['uuid']
    email = request.form['email']
    path_file = request.form['path_file']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users_reg SET uuid = ?, email = ?, path_file = ? WHERE id = ?',
        (uuid, email, path_file, id)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/api/table', methods=['GET'])
def table_route():
    users = get_users()
    return render_template('table.html', users=users)
    
if __name__ == '__main__' :
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)