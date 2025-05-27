from flask import Flask, request, jsonify
from flask_cors import CORS
import bcrypt
import mysql.connector

app = Flask(__name__)
CORS(app, supports_credentials=True)

# ---- DATABASE CONNECTION ----
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",               
        password="12345678",       
        database="iot_dashboard"   
    )

# ---- USER REGISTRATION ----
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'error': 'All fields are required.'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return jsonify({'error': 'Username already exists.'}), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
        (username, password_hash.decode(), email)
    )
    db.commit()
    user_id = cursor.lastrowid

    # Create a default MCU for new user
    mcu_name = f"{username}'s MCU"
    place = "Not specified"
    cursor.execute(
        "INSERT INTO microcontrollers (mcu_name, place, owner_id) VALUES (%s, %s, %s)",
        (mcu_name, place, user_id)
    )
    db.commit()
    cursor.close()
    db.close()
    return jsonify({'message': 'Registration successful! MCU assigned.'})

# ---- USER LOGIN ----
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    db.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404
    if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return jsonify({'error': 'Incorrect password'}), 401

    return jsonify({'message': 'Login successful', 'user_id': user['user_id']})

# ---- GET MCU (DEVICE) FOR A USER ----
@app.route('/api/devices', methods=['GET'])
def get_devices():
    user_id = request.args.get('user_id')
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM microcontrollers WHERE owner_id=%s", (user_id,)
    )
    devices = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(devices)

# ---- GET SENSORS FOR MCU ----
@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    mcu_id = request.args.get('mcu_id')
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM sensors WHERE mcu_id=%s", (mcu_id,)
    )
    sensors = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(sensors)

# ---- GET SENSOR READINGS ----
@app.route('/api/sensor_readings', methods=['GET'])
def get_sensor_readings():
    sensor_id = request.args.get('sensor_id')
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM sensor_readings WHERE sensor_id=%s ORDER BY reading_time DESC LIMIT 1", (sensor_id,)
    )
    readings = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(readings)

# ---- POST SET POINTS ----
@app.route('/api/set_point', methods=['POST'])
def set_point():
    try:
        data = request.get_json()
        mcu_id = data.get('mcu_id')
        user_id = data.get('user_id')
        setpoints = data.get('setpoints', [])

        db = get_db()
        cursor = db.cursor()

        for sp in setpoints:
            sensor_id = sp.get('sensor_id')
            name = sp.get('name')
            value = sp.get('value')
            cursor.execute(
                "INSERT INTO setpoints (mcu_id, sensor_id, user_id, name, value) VALUES (%s, %s, %s, %s, %s)",
                (mcu_id, sensor_id, user_id, name, value)
            )
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'message': 'Set points saved successfully!'})
    except Exception as e:
        print("Error in /api/set_point:", str(e))
        return jsonify({'error': str(e)}), 500

# ---- GET SETPOINT HISTORY ----
@app.route('/api/setpoints', methods=['GET'])
def get_setpoints():
    mcu_id = request.args.get('mcu_id')
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM setpoints WHERE mcu_id = %s ORDER BY set_time DESC LIMIT 100", (mcu_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(result)

# ---- MAIN ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)