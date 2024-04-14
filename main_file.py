import network
import socket
import machine
import time
import _thread
import requests
from TMP36class import TMP36
from machine import RTC

sensor_lock=_thread.allocate_lock()
currentDay_lock = _thread.allocate_lock()

def second_thread():
    global tmp36
    while True:
        sensor_lock.acquire()
        measuredTemp=tmp36.read_temperature()
        sensor_lock.release()
        currentDay_lock.acquire()
        tmp36.temperature_logging(measuredTemp)
        currentDay_lock.release()
        time.sleep(180)

html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pico W Temperature Server</title>
            <meta http-equiv="refresh" content="60"/>
        </head>
        <body>
            <p>Latest Page Refresh: %s</p>
            <hr>
            <h1>Raspberry Pi Pico W Web Server for Temperature Measurement</h1>
            <p>Sensor Used: TMP36</p>
            <p>Current Temperature: <span id="current-temperature">%s</span> &deg;C</p>
            <p>Maximum Temperature Measured Today: <span id="max-temperature">%s</span> &deg;C</p>
            <p>Average Temperature Today: <span id="average-temperature">%s</span> &deg;C</p>
            <img src="%s">
            <form action="/download" method="get"><button type="submit">Download Last 10 Days Log</button></form>
            <form action="/downloadCurrentDay" method="get"><button type="submit">Download Current Day Log</button></form>
        </body>
        </html>
        """

    
ssid = 'your_ssid'
password = 'your_password'

sta_if = network.WLAN(network.STA_IF)

sta_if.active(True)
sta_if.config(pm = 0xa11140) # Disable power-saving for WiFi 
sta_if.connect(ssid, password)

max_wait = 10
while max_wait > 0:
    if sta_if.status() < 0 or sta_if.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

if sta_if.isconnected():
    print("Connected")
else:
    print("Not Connected")

status = sta_if.ifconfig()
print('IP Address:', status[0])

api_url = "https://api.api-ninjas.com/v1/worldtime?city=Athens"
api_response = requests.get(api_url, headers={'X-Api-Key': 'F7CVphnc0ReUJWvw2qJ1ew==6vRW9Pb0IVEbIu35'})

api_response=api_response.json()

days_mapping = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6
    }


year = api_response['year']
month = api_response['month']
day = api_response['day']
hour = api_response['hour']
minutes = api_response['minute']
seconds = api_response['second']
weekDay=days_mapping[api_response['day_of_week']]

currentDay=[int(day), int(month), int(year)]

rtc = machine.RTC()
rtc.datetime((int(year), int(month), int(day), weekDay, int(hour), int(minutes), int(seconds), 0))
prevMeasurement=rtc.datetime()
prevMeasurementDay=[prevMeasurement[2], prevMeasurement[1], prevMeasurement[0]]
tmp36=TMP36(26, prevMeasurementDay, rtc)

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

_thread.start_new_thread(second_thread, ())
        
while True:
    try:
        cl, addr = s.accept()
        print('client connected from', addr)
        request = cl.recv(1024)
        
        if "/download?" in request:
            with open("temperature_log.txt", "r") as file:
                data = file.read()
            response = "HTTP/1.1 200 OK\n"
            response += "Content-Type: text/plain\n"
            response += f"Content-Length: {len(data)}\n"
            response += "Content-Disposition: attachment; filename=temperature_log.txt\n\n"
            response += data
            cl.sendall(response.encode('utf-8'))
            cl.close()
            continue
        
        if "/downloadCurrentDay?" in request:
            with open("daily_temperature_log.txt", "r") as file:
                data = file.read()
            response = "HTTP/1.1 200 OK\n"
            response += "Content-Type: text/plain\n"
            response += f"Content-Length: {len(data)}\n"
            response += "Content-Disposition: attachment; filename=daily_temperature_log.txt\n\n"
            response += data
            cl.sendall(response.encode('utf-8'))
            cl.close()
            continue
            
        currentDayTime =rtc.datetime()

        sensor_lock.acquire()
        currentTemp = tmp36.read_temperature()
        sensor_lock.release()
        
        currentDay=[currentDayTime[2], currentDayTime[1], currentDayTime[0]]
        
        Day = "{:02d}-{:02d}-{:04d} {:02d}:{:02d}:{:02d}".format(currentDayTime[2], currentDayTime[1], currentDayTime[0], currentDayTime[4], currentDayTime[5], currentDayTime[6])
        
        currentDay_lock.acquire()
        averageDaily = tmp36.GetAvgTemp()
        currentDay_lock.release()
        lastDays=tmp36.getLastDaysLog()
        if len(lastDays)!=0:
            labels = [day[0] for day in lastDays]
            data = [temp[1] for temp in lastDays]
            
            chart_data = "{type:'line',data:{labels:['" + "','".join(labels) + "'],datasets:[{label:'Temperature',data:[" + ",".join(map(str, data)) + "],fill:false}]},options:{title:{display:true,text:'Average Daily Temperature for the Last 10 Days'}}}"
            
            chart_url = "https://quickchart.io/chart?c=" + chart_data
            
            response = html % (Day, str(currentTemp), str(tmp36.GetMaxTemp()), str(averageDaily), chart_url)
        
        else:
            response = html % (Day, str(currentTemp), str(tmp36.GetMaxTemp()), str(averageDaily), "")

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(response)
        cl.close()
    
    except Exception as e:
            print("Error in main loop:", e)







