from bluetooth import *
from picamera import PiCamera
from gpiozero import MotionSensor
import os
import sys
import time
import datetime as dt
import wiringpi as GPIO

initGPIO()
# HELLO MESSAGES
print("Photo mode\n")

# BLUETOOTH SETUP
server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

advertise_service(server_sock, "CameraServer",
                  service_id=uuid,
                  service_classes=[uuid, SERIAL_PORT_CLASS],
                  profiles=[SERIAL_PORT_PROFILE],
                  #                   protocols = [ OBEX_UUID ]
                  )

# MAIN PROGRAM LOOP
MODE_FLAG = 0                            # [0 - photo; 1 - video; 2 - motion detector
pir = MotionSensor(18)                   # motion detector input

while True:
    print("Waiting for connection on RFCOMM channel %d" % port)

    client_sock, client_info = server_sock.accept()
    print("Accepted connection from ", client_info)

    try:
        data = client_sock.recv(1024)
        if len(data) == 0:
            break
        print("received [%s]" % data)

        if data == 'switch':
            data = 'switched!'
            MODE_FLAG = changeMode(MODE_FLAG)
        elif data == 'capture':
            data = 'capture!'
            if MODE_FLAG == 0:     # taking photo
                capturePicture()
            elif MODE_FLAG == 1:   # taking video
                captureVideo()
            elif MODE_FLAG == 2:   # taking video after motion detected
                captureWithPIR()
        elif data == 'turnOff':
            data = 'turn off!'
            cleanUp()
        else:
            data = 'WTF!'
        client_sock.send(data)
        print("sending [%s]" % data)

    except IOError:
        pass

    except KeyboardInterrupt:

        print("disconnected")

        client_sock.close()
        server_sock.close()
        print("all done")

        break


# DEFS
def initGPIO():
    GPIO.wiringPiSetupGpio()
    GPIO.pinMode(23, GPIO.INPUT)  # switching mode
    GPIO.pinMode(24, GPIO.INPUT)  # capture picture from camera
    GPIO.pinMode(25, GPIO.INPUT)  # exit from camera
    GPIO.pinMode(18, GPIO.INPUT)  # motion detector input
    GPIO.pinMode(27, GPIO.OUTPUT)  # LED indicates switching between modes
    GPIO.pinMode(22, GPIO.OUTPUT)  # LED indicates taking a photo/video
    GPIO.pullUpDnControl(23, GPIO.PUD_UP)
    GPIO.pullUpDnControl(24, GPIO.PUD_UP)
    GPIO.pullUpDnControl(25, GPIO.PUD_UP)


def getFileName(type):
    now = dt.datetime.now()
    date = str(now.date()) + "_" + str(now.time().replace(microsecond=0))
    if (type):  # photo
        filename = "photo_" + date + '.jpg'
    else:  # video
        filename = "video_" + date + '.h264'
    return filename


def changeMode(mode):
    GPIO.digitalWrite(27, GPIO.HIGH)
    time.sleep(0.3)
    mode = (mode + 1) % 3
    if (mode == 0):
        print("Photo mode\n")
    elif (mode == 1):
        print("Video mode\n")
    elif (mode == 2):
        print("Motion Detector Video mode\n")
    GPIO.digitalWrite(27, GPIO.LOW)
    return mode


def capturePicture():
    GPIO.digitalWrite(22, GPIO.HIGH)
    os.system('raspistill -o /home/pi/Desktop/Camera/Photos/' + getFileName(True))
    print("Just took a photo!\n")
    GPIO.digitalWrite(22, GPIO.LOW)


def captureVideo():
    GPIO.digitalWrite(22, GPIO.HIGH)
    cam = PiCamera()
    cam.start_recording('/home/pi/Desktop/Camera/Videos/' + getFileName(False))
    time.sleep(5)
    cam.stop_recording()
    print("Just recorded a video!\n")
    GPIO.digitalWrite(22, GPIO.LOW)


def captureWithPIR():
    GPIO.digitalWrite(22, GPIO.HIGH)
    cam = PiCamera()
    cam.start_recording('/home/pi/Desktop/Camera/Videos/' + getFileName(False))
    pir.wait_for_no_motion()
    cam.stop_recording()
    print("Just recorded a video after motion detected!\n")
    GPIO.digitalWrite(22, GPIO.LOW)


def cleanUp():
    # output pins set to 0
    GPIO.digitalWrite(27, GPIO.LOW)
    GPIO.digitalWrite(22, GPIO.LOW)
    # output pins set to input
    GPIO.pinMode(27, GPIO.INPUT)
    GPIO.pinMode(22, GPIO.INPUT)
    sys.exit("Good bye! :)")
    # clean up bluetooth connection
    client_sock.close()
    server_sock.close()
