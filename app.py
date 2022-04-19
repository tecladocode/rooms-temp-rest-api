from flask import Flask,jsonify,request,render_template
from datetime import datetime,timezone
#from psycopg2 import connect
import psycopg2
import pytz
import time
import os

url = os.environ.get('DATABASE_URL')
connection = psycopg2.connect(url)
app = Flask(__name__)


CREATE_ROOMS_TABLE = "CREATE TABLE IF NOT EXISTS rooms (id SERIAL PRIMARY KEY, name TEXT);"
CREATE_TEMPS_TABLE = """CREATE TABLE IF NOT EXISTS temperatures (room_id INTEGER, temperature REAL, 
                        date TIMESTAMP, FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);"""

INSERT_ROOM_RETURN_ID = "INSERT INTO rooms (name) VALUES (%s) RETURNING id;"
INSERT_TEMP = "INSERT INTO temperatures (room_id, temperature, date) VALUES (%s, %s, %s);"

ROOM_AVG = """SELECT rooms.name, COUNT(temperatures.date), AVG(temperatures.temperature)
                       FROM rooms JOIN temperatures ON rooms.id = temperatures.room_id WHERE rooms.id = (%s) GROUP BY DATE(temperatures.date), rooms.id;"""
                       
ROOM_ALL_TIME_AVG = """SELECT name, COUNT(date) as number_of_days, AVG(average) as average_temp FROM 
                       (SELECT DATE(temperatures.date), rooms.name, COUNT(temperatures.date), AVG(temperatures.temperature) as average
                       FROM rooms JOIN temperatures ON rooms.id = temperatures.room_id WHERE rooms.id = (%s) 
                       GROUP BY DATE(temperatures.date), rooms.name) as days GROUP BY name;"""

"""
{
	"name": "Room name",
	"temperatures": [
		{"date": "2022-03-10", "temperature": 13.4},
		{"date": "2022-03-09", "temperature": 14.4},
		{"date": "2022-03-08", "temperature": 17.4},
		{"date": "2022-03-07", "temperature": 13.4},
		{"date": "2022-03-06", "temperature": 13.4},
		{"date": "2022-03-05", "temperature": 16.4},
		{"date": "2022-03-04", "temperature": 13.4},
	],
	"average": 15.7
}
"""

@app.route("/")
def home_view():
	return "<h1>Welcome to rooms temp control</h1>"
	

# POST /api/room {'name':room_name}			
@app.route('/api/room',methods=['POST'])
def create_room():
    data = request.get_json()
    name = data['name']
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_ROOMS_TABLE)
            cursor.execute(INSERT_ROOM_RETURN_ID, (name,))
            room_id = cursor.fetchone()[0]
    return {"id": room_id, "message": f"Room {name} created."}
            


#{"temperature": 15.9, "room": 2}
#OPTIONAL: {"temperature": 15.9, "room": 2, "date": "%d-%m-%Y %H:%M:%S"}
@app.route('/api/temperature',methods=['POST'])
def add_temp():
    data = request.get_json()
    temperature = data['temperature']
    room_id = data['room']
    try:
        date = datetime.strptime(data['date'],"%d-%m-%Y %H:%M:%S")
    except:
        date = datetime.now(timezone.utc)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TEMPS_TABLE)
            cursor.execute(INSERT_TEMP, (room_id, temperature, date))
    return {"message": "Temperature added."}



#GET /api/room/2
@app.route('/api/room/<string:id>')
def get_room(id):
    room_id = int(id)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(ROOM_ALL_TIME_AVG, (room_id,))
            row = cursor.fetchone()
    return {"name": row[0], "average": round(row[2], 2), "days": row[1]}



@app.route('/api/room/<string:id>?term=week')
def get_room(id):
    room_id = int(id)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(ROOM_ALL_TIME_AVG, (room_id,))
            row = cursor.fetchone()
    return {"name": row[0], "average": round(row[2], 2), "days": row[1]}
    

if __name__ == "__main__":
  	app.run()