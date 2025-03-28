from flask import Flask, request, jsonify, render_template
import sqlite3
from random import randint, choice
import atexit
from threading import Thread
import time
import requests

app = Flask(__name__)

# Максимальные значения
MAX_FUEL = 10000  # Максимальное количество топлива
MAX_FOOD = 1000   # Максимальное количество питания
MAX_BAGGAGE = 300  # Максимальное количество багажа
MAX_SEATS = 100    # Максимальное количество мест в самолете
# Список городов, куда могут лететь самолеты
DESTINATION_CITIES = [
    "Лондон", "Париж", "Берлин", "Нью-Йорк", "Токио",
    "Пекин", "Дубай", "Стамбул", "Рим", "Мадрид"
]
def get_db_connection():
    conn = sqlite3.connect('aircraft.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('DROP TABLE IF EXISTS aircrafts')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS aircrafts (
            id INTEGER NOT NULL,
            fuel INTEGER NOT NULL,
            food INTEGER NOT NULL,
            baggage INTEGER NOT NULL,
            baggage_count INTEGER NOT NULL, -- Общее кол-во багажа
            registered_passengers INTEGER NOT NULL,  -- Количество зарегистрированных пассажиров
            passengers_on_board INTEGER NOT NULL,    -- Количество пассажиров на борту
            passengers_count INTEGER NOT NULL, -- общее кол -во пассажиров
            status TEXT NOT NULL,                   -- Статус самолета
            follow_me_status TEXT,                 -- Статус follow me
            refueling_status TEXT,                 -- Статус заправки
            baggage_status TEXT,                   -- Статус багажа
            catering_status TEXT,                  -- Статус питания
            origin TEXT NOT NULL,                  -- Откуда летит самолет
            destination TEXT NOT NULL,              -- Куда летит самолет
            current_location INTEGER,      -- текущая локация
            future_location INTEGER         -- будущая локация
        )
    ''')
    conn.commit()
    conn.close()



def cleanup_db():
    conn = get_db_connection()
    conn.execute('DELETE FROM aircrafts')
    conn.commit()
    conn.close()
    print("Все данные из базы данных удалены.")

@app.route('/aircrafts', methods=['GET'])
def list_aircrafts():
    conn = get_db_connection()
    aircrafts = conn.execute('SELECT * FROM aircrafts').fetchall()
    conn.close()
    return render_template('all_planes.html', aircrafts=aircrafts)


def get_locations(plane_id):
    url = f"http://192.168.35.219:5555/dispatcher/plane/{plane_id}"  # URL для получения координат
    while True:  # Вечный цикл
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                location_data = response.json()  # Предполагаем, что это список [current_location, future_location]
                # Проверяем, что это список и содержит два элемента
                if isinstance(location_data, list) and len(location_data) == 2:
                    current_location, future_location = location_data
                    # Проверяем, что значения не равны -1
                    if current_location != -1 and future_location != -1:
                        return current_location, future_location  # Возвращаем валидные значения
                    else:
                        print(
                            f"Получены невалидные значения: current_location={current_location}, future_location={future_location}. Повторная попытка...")
                else:
                    print(f"Некорректный формат данных: ожидался список из двух элементов, получено: {location_data}")
            else:
                print(f"Ошибка при запросе локаций: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе локаций: {e}")
        time.sleep(2)  # Ждем 2 секунды перед следующей попыткой

def create_plane_to_Denis(plane_id, fuel):
    url = f"http://192.168.35.125:5555/uno/api/v1/plane/{plane_id}/{fuel}/create-plane"
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, timeout=10)
        response.raise_for_status()  # Проверяем, что ответ успешный (статус 200-299)
        print(f"Запрос на создание/обновление самолета {plane_id} успешно отправлен.")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса к серверу: {e}")
def get_takeoff_data(plane_id):
    url = f"http://192.168.35.219:5555/dispatcher/plane/takeoff/{plane_id}"
    while True:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                print(f"Ошибка: ожидался список, получено: {data}")
                return None
            if len(data) > 0 and data[0] != -1:
                print(data)
                return data
            else:
                print(f"Получен невалидный список: {data}. Повторная попытка...")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при выполнении запроса к серверу: {e}")
            return None
        time.sleep(2)
def create_aircraft():

    aircraft_id = randint(1000, 9999)
    destination = choice(DESTINATION_CITIES)
    aircraft = {
        "id": aircraft_id,
        "fuel": randint(0, MAX_FUEL),
        "food": randint(0, MAX_FOOD),
        "baggage": 0,
        "baggage_count": MAX_BAGGAGE,
        "registered_passengers": 0,
        "passengers_on_board": 0,
        "passengers_count": MAX_SEATS,
        "status": "On Stand",
        "follow_me_status": "Pending",
        "refueling_status": "Pending",
        "baggage_status": "Pending",
        "catering_status": "Pending",
        "origin": "Москва",
        "destination": destination,
        "current_location": None,
        "future_location": None
    }
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO aircrafts (id, fuel, food, baggage, baggage_count, registered_passengers, passengers_on_board, passengers_count, status, 
        follow_me_status, refueling_status, baggage_status, catering_status, origin, destination, current_location, future_location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (aircraft["id"], aircraft["fuel"], aircraft["food"], aircraft["baggage"], aircraft["baggage_count"],
          aircraft["registered_passengers"], aircraft["passengers_on_board"], aircraft["passengers_count"], aircraft["status"],
          aircraft["follow_me_status"], aircraft["refueling_status"], aircraft["baggage_status"],
          aircraft["catering_status"], aircraft["origin"], aircraft["destination"], aircraft["current_location"], aircraft["future_location"]))
    conn.commit()
    conn.close()
    print(f"Самолет {aircraft_id} создан. Направление: {destination}")
    fuell = MAX_FUEL - aircraft["fuel"]
    send_aircraft_info(aircraft)
    try:
        current_location, future_location = get_locations(aircraft_id)
        print(f"Получены координаты для самолета {aircraft_id}: current_location={current_location}, future_location={future_location}")
        conn = get_db_connection()
        conn.execute('UPDATE aircrafts SET current_location = ?, future_location = ? WHERE id = ?',
                     (current_location, future_location, aircraft_id))
        conn.commit()
        conn.close()
        create_plane_to_Denis(aircraft_id, fuell)
    except Exception as e:
        print(f"Ошибка при получении координат для самолета {aircraft_id}: {e}")

    return aircraft
# ----------------------------------------------------------------------------------------------------------------------
def send_point_request(current_point, target):
    url = f"http://192.168.35.219:5555/dispatcher/point/{current_point}/{target}"
    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            if isinstance(result, bool):
                if result:
                    return True
                else:
                    attempt += 1
                    print(f"Получен false для точек {current_point} -> {target}. Попытка {attempt}/{max_attempts}.")
            else:
                print(f"Ошибка: ожидалось булево значение, получено: {result}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при выполнении запроса к серверу: {e}")
            return False
        time.sleep(2)
    print(f"Превышено максимальное количество попыток ({max_attempts}) для перехода от {current_point} к {target}.")
    return False

def navigate_points(points, aircraft_id):
    if not points or len(points) < 2:
        print("Ошибка: массив точек должен содержать как минимум две точки.")
        return False
    conn = get_db_connection()
    aircraft = conn.execute('SELECT current_location FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    conn.close()
    if not aircraft or aircraft["current_location"] is None:
        print(f"Ошибка: не удалось получить текущую локацию для самолета {aircraft_id}.")
        return False
    current_location = aircraft["current_location"]
    first_point_minus_one = current_location
    print(f"Начальная точка уменьшена на 1: {first_point_minus_one} -> {points[0]}")
    if not send_point_request(first_point_minus_one, points[0]):
        print(f"Не удалось перейти от точки {first_point_minus_one} к точке {points[0]}.")
        return False
    for i in range(len(points) - 1):
        current_point = points[i]
        target = points[i + 1]
        print(f"Переход от точки {current_point} к точке {target}...")
        if not send_point_request(current_point, target):
            print(f"Не удалось перейти от точки {current_point} к точке {target}.")
            return False
    final_target = points[-1]
    delete_url = f"http://192.168.35.219:5555/dispatcher/plane/takeoff/{final_target}"
    try:
        response = requests.delete(delete_url, timeout=10)
        response.raise_for_status()
        print(f"DELETE-запрос на {delete_url} выполнен успешно.")
        conn = get_db_connection()
        conn.execute('UPDATE aircrafts SET status = ? WHERE id = ?', ("Улетел", aircraft_id))
        conn.commit()
        conn.close()
        print(f"Статус самолета {aircraft_id} обновлен на 'Улетел'.")

        return True
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении DELETE-запроса: {e}")
        return False

#-----------------------------------------------------------------------------------------------------------------------
def send_aircraft_info(aircraft):
    aircraft_info = {
        "Id": aircraft["id"],
        "baggage_available": MAX_BAGGAGE,
        "seats_available": MAX_SEATS
    }
    url = "http://192.168.35.244:5555/dep-board/api/v1/airplanes"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=aircraft_info, headers=headers)
    if response.status_code == 200:
        print(f"Информация о самолете {aircraft['id']} успешно отправлена.")
    else:
        print(f"Ошибка при отправке информации о самолете {aircraft['id']}: {response.status_code}")

def auto_generate_aircrafts():
    while True:
        create_aircraft()
        time.sleep(100)

def initialize_aircrafts():
    create_aircraft()

@app.route('/generate_aircraft', methods=['GET'])
def generate_aircraft():
    aircraft = create_aircraft()
    return jsonify(aircraft), 201


@app.route('/board_passengers/<aircraft_id>', methods=['POST'])
def board_passengers(aircraft_id):
    data = request.get_json()
    print("Received data:", data)
    if not data or not isinstance(data, list):
        print("Error: Data is not a list")
        return jsonify({"error": "Invalid JSON format. Expected a list of passenger IDs."}), 400
    passengers = len(data)
    print("Number of passengers:", passengers)
    if passengers > MAX_SEATS:
        print(f"Error: Cannot board more than {MAX_SEATS} passengers")
        return jsonify({"error": f"Cannot board more than {MAX_SEATS} passengers"}), 400
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if aircraft:
        print("Aircraft found:", dict(aircraft))
        if passengers > aircraft["registered_passengers"]:
            print("Error: Cannot board more passengers than registered")
            conn.close()
            return jsonify({"error": "Cannot board more passengers than registered"}), 400
        conn.execute('UPDATE aircrafts SET passengers_on_board = ? WHERE id = ?', (passengers, aircraft_id))
        conn.commit()
        updated_aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
        print("Updated aircraft data:", dict(updated_aircraft))
        conn.close()
        try:
            response = requests.post('http://192.168.35.175:5555//passenger/on-board', json=data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print("Error sending data to the other server:", e)
            return jsonify({"error": f"Failed to send data to the other server: {str(e)}"}), 500

        return jsonify({
            "message": "Passengers boarded",
            "aircraft_id": aircraft_id,
            "passengers_on_board": passengers,
            "sent_data": data
        }), 200
    else:
        print("Error: Aircraft not found")
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404

@app.route('/passengers_out/<aircraft_id>', methods=['GET'])
def passengers_delete(aircraft_id):
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if not aircraft:
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404
    conn.execute('UPDATE aircrafts SET passengers_on_board = ? WHERE id = ?',
                 (0, aircraft_id))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "delete passengers completed",
        "aircraft_id": aircraft_id,
        "current_food": 0
    }), 200

@app.route('/reg_passengers/<aircraft_id>', methods=['POST'])
def reg_passengers(aircraft_id):
    data = request.get_json()
    print("Received data:", data)
    if not data or not isinstance(data, list):
        print("Error: Data is not a list")
        return jsonify({"error": "Invalid JSON format. Expected a list of passenger IDs."}), 400
    passengers = len(data)
    print("Number of passengers:", passengers)
    if passengers > MAX_SEATS:
        print(f"Error: Cannot board more than {MAX_SEATS} passengers")
        return jsonify({"error": f"Cannot board more than {MAX_SEATS} passengers"}), 400
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if aircraft:
        print("Aircraft found:", dict(aircraft))
        if passengers > MAX_SEATS:
            print("Error: Cannot board more passengers than registered")
            conn.close()
            return jsonify({"error": "Cannot board more passengers than registered"}), 400
        conn.execute('UPDATE aircrafts SET registered_passengers = ? WHERE id = ?', (passengers, aircraft_id))
        conn.commit()
        updated_aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
        print("Updated aircraft data:", dict(updated_aircraft))
        conn.close()
        return jsonify({
            "message": "Passengers boarded",
            "aircraft_id": aircraft_id,
            "reg_pass": passengers,
            "sent_data": data
        }), 200
    else:
        print("Error: Aircraft not found")
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404


@app.route('/update_location/<aircraft_id>', methods=['POST'])
def update(aircraft_id):
    data = request.get_json()
    if not data or not isinstance(data, int):
        return jsonify({"error": "Invalid JSON format. Expected an integer for current_location."}), 400
    current_location = data
    conn = get_db_connection()
    try:
        aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
        if not aircraft:
            conn.close()
            return jsonify({"error": "Aircraft not found"}), 404
        conn.execute('UPDATE aircrafts SET current_location = ? WHERE id = ?', (current_location, aircraft_id))
        conn.commit()
        conn.close()
        return jsonify({
            "message": "Current location updated successfully",
            "aircraft_id": aircraft_id,
            "current_location": current_location
        }), 200
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Failed to update current location: {str(e)}"}), 500

@app.route('/follow-me/<aircraft_id>', methods=['GET'])
def get_point(aircraft_id):
    conn = get_db_connection()
    point = conn.execute('SELECT future_location FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    conn.close()
    if point is not None:
        future_location = point["future_location"]
        return str(future_location)
    else:
        return "Aircraft not found", 404

@app.route('/current-point/<aircraft_id>', methods=['GET'])
def get_current_point(aircraft_id):
    conn = get_db_connection()
    point = conn.execute('SELECT current_location FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    conn.close()
    if point is not None:
        current_location = point["current_location"]
        return str(current_location)
    else:
        return "Aircraft not found", 404

@app.route('/refuel/<aircraft_id>', methods=['GET'])
def refuel_complete(aircraft_id):
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if not aircraft:
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404
    conn.execute('UPDATE aircrafts SET fuel = ?, refueling_status = ? WHERE id = ?',
                 (MAX_FUEL, "Completed", aircraft_id))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "Refueling completed",
        "aircraft_id": aircraft_id,
        "current_fuel": MAX_FUEL
    }), 200

@app.route('/catering/<aircraft_id>', methods=['GET'])
def catering_complete(aircraft_id):
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if not aircraft:
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404
    conn.execute('UPDATE aircrafts SET food = ?, catering_status = ? WHERE id = ?',
                 (MAX_FOOD, "Completed", aircraft_id))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "set Catering completed",
        "aircraft_id": aircraft_id,
        "current_food": MAX_FOOD
    }), 200

@app.route('/catering_out/<aircraft_id>', methods=['GET'])
def catering_delete(aircraft_id):
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if not aircraft:
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404
    conn.execute('UPDATE aircrafts SET food = ?, catering_status = ? WHERE id = ?',
                 (0, "Completed", aircraft_id))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "delete Catering completed",
        "aircraft_id": aircraft_id,
        "current_food": 0
    }), 200

@app.route('/baggage/<aircraft_id>', methods=['GET'])
def baggage_complete(aircraft_id):
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if not aircraft:
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404
    conn.execute('UPDATE aircrafts SET baggage = ?, baggage_status = ? WHERE id = ?',
                 (MAX_BAGGAGE, "Completed", aircraft_id))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "set baggage completed",
        "aircraft_id": aircraft_id,
        "current_baggage": MAX_BAGGAGE
    }), 200

@app.route('/baggage_out/<aircraft_id>', methods=['GET'])
def baggage_delete(aircraft_id):
    conn = get_db_connection()
    aircraft = conn.execute('SELECT * FROM aircrafts WHERE id = ?', (aircraft_id,)).fetchone()
    if not aircraft:
        conn.close()
        return jsonify({"error": "Aircraft not found"}), 404
    conn.execute('UPDATE aircrafts SET baggage = ?, baggage_status = ? WHERE id = ?',
                 (0, "Completed", aircraft_id))
    conn.commit()
    conn.close()
    return jsonify({
        "message": "delete baggage completed",
        "aircraft_id": aircraft_id,
        "current_baggage": 0
    }), 200

def run_server():
    app.run(host='192.168.35.209', port=5555)

@app.route('/service_complete/<int:aircraft_id>', methods=['POST'])
def service_complete(aircraft_id):
    print(f"Уведомление: обслуживание самолета {aircraft_id} завершено.")
    takeoff_data = get_takeoff_data(aircraft_id)
    if takeoff_data is None:
        return jsonify({
            "error": f"Не удалось получить данные о взлете для самолета {aircraft_id}."
        }), 500
    print(f"Данные о взлете для самолета {aircraft_id}: {takeoff_data}")
    if navigate_points(takeoff_data,aircraft_id):
        return jsonify({
            "message": f"Обслуживание самолета {aircraft_id} завершено. Навигация по точкам выполнена.",
            "takeoff_data": takeoff_data
        }), 200
    else:
        return jsonify({
            "error": f"Ошибка при навигации по точкам для самолета {aircraft_id}."
        }), 500

if __name__ == '__main__':
    print("Starting server...")
    init_db()
    atexit.register(cleanup_db)
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    MAX_ACTIVE_AIRCRAFTS = 5
    while True:
        conn = get_db_connection()
        active_aircrafts = conn.execute(
            'SELECT COUNT(*) FROM aircrafts WHERE status != ?', ("Улетел",)
        ).fetchone()[0]
        conn.close()
        if active_aircrafts < MAX_ACTIVE_AIRCRAFTS:
            create_aircraft()
        time.sleep(30)