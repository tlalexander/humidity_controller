'''
Humidity Controller web app

'''
from flask import Flask, render_template, request
import json
import time


def get_rows(queue):
    rows = queue.get()
    return rows

def create_app(queue):
    app = Flask(__name__, template_folder="/home/pi/webpage/")
    app.config['QUEUE'] = queue
    return app

def launch_app(queue):
    app = create_app(queue)

    @app.route("/")
    def main():
        queue = app.config['QUEUE']
        rows = get_rows(queue)
        rows = rows[-1000:]
        tick = 1
        temps = []
        humidity = []
        for row in rows:
            #print(row)
            temps.append([tick, row[1]])
            humidity.append([tick, row[2]])
            tick +=1

        data = ("[ { label: \'Temp\', data: " + str(temps) + " }," +
                "  { label: \'Humidity\', data: " + str(humidity) + " }]")
        options = "{ }"
        return render_template("main.html", data=data, options=options)

    @app.route("/data")
    def data():

        queue = app.config['QUEUE']
        rows = get_rows(queue)
        rows = rows[-1000:]
        tick = 1
        temps = []
        humidity = []
        for row in rows:
            #print(row)
            temps.append([tick, row[1]])
            humidity.append([tick, row[2]])
            tick +=1

        json_string = json.dumps([temps, humidity])
        return json_string

    app.run(host='0.0.0.0', port=80)

if __name__ == "__main__":
    launch_app()
