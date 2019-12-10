from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, Response
import cv2
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
import datetime
import threading
import time
from imagezmq.imagezmq import ImageHub
app = Flask(__name__)
app.secret_key='secret123'
import zmq
import base64
import numpy as np
#Config MySQL

image_hub = ImageHub()
outputFrame = None
lock = threading.Lock()
#init MySQL

#context = zmq.Context()
#footage_socket = context.socket(zmq.SUB)
#footage_socket.bind('tcp://*:5555')
#footage_socket.setsockopt_string(zmq.SUBSCRIBE, np.unicode(''))
time.sleep(2.0)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] !='admin':
            error = 'Wrong Username or Password'
        else:
            return redirect(url_for('streamvid'))
    return render_template('login.html', error=error)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(), validators.EqualTo('confirm', message='Password do not match')])
    confirm = PasswordField('Confirm Password')


def writeimg():
    global vs, outputFrame, lock
    # loop over frames from the video stream
    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        name,frame = image_hub.recv_image()
        image_hub.send_reply(b'OK')

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime(
            "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame

        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = frame.copy()

def gen():
    """Video streaming generator function."""
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encodedImage) + b'\r\n')

@app.route('/streamvid')
def streamvid():
    return render_template('streamvid.html')

@app.route('/video_feed')
def video_feed():
    t = threading.Thread(target=writeimg, )
    t.daemon = True
    t.start()
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),mimetype='multipart/x-mixed-replace; boundary=frame')



if __name__ == "__main__":

    # start the flask app
    app.run(host='0.0.0.0')

