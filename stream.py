# Author: Luke Charbonneau, 2019
# Released under the GPL-3.0 license

import sys
import argparse
import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server

PAGE="""\
<html>
<head>
<title>Raspberry Pi Camera</title>
</head>
<body>
<center><h1>Raspberry Pi Camera</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

DEFAULT_PORT = 8000

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        logging.info("Client connected from IP address {}".format(self.client_address))
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = streamServer.page.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    #with streamServer.ouput.condition:
                    streamServer.output.condition.acquire()
                    streamServer.output.condition.wait()
                    streamServer.output.condition.release()
                    frame = streamServer.output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.info(
                    'Removed streaming client {}: {}'.format(
                    self.client_address, e))
        else:
            logging.warning("Unrecognized request from client @ {}: {}".format(self.client_address, self.path))
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    
class PiCameraStreamServer(object):
    
    def __init__(self, resolution='640x480'):
        self.output = StreamingOutput()
        self.server = None
        # Default resolution
        self.resolution = '640x480'
        # See if user provided a valid resolution string
        try:
            hori = int(resolution[:resolution.index('x')])
            vert = int(resolution[resolution.index('x') + 1:])
            # Generate new page file for /index.html requests based on user-entered resolution
            self.page = PAGE.replace('640', str(hori)).replace('480', str(vert))
            self.resolution = '{}x{}'.format(hori, vert)
        except ValueError:
            logging.warning("Resolution argument must have string format: '[Vertical Resolution]x[Horizontal Resolution]'. Defaulting to 640x480.")
            hori = 640
            vert = 480
        except Exception:
            logging.warning("Failed to set user-entered resolution. Defaulting to 640x480.")
            hori = 640
            vert = 480
            
if __name__ == "__main__":
    userResolution = None
    userFramerate = None
    userRotation = None
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='Port number to listen for incoming connections on (default: 8000)')
    parser.add_argument('-res', '--resolution', help='Pi Camera stream resolution')
    parser.add_argument('-f', '--framerate', help='Pi Camera stream framerate')
    parser.add_argument('-rot', '--rotation', help='Angle to rotate Pi Camera stream')
    args = parser.parse_args()
    try:
        if args.port:
            userPort = int(args.port)
        else:
            userPort = DEFAULT_PORT
        if args.resolution:
            userResolution = args.resolution
        else:
            userResolution = '640x480'
        if args.framerate:
            userFramerate = int(args.framerate)
        else:
            userFramerate = 30
        if args.rotation:
            userRotation = int(args.rotation)
        else:
            userRotation = 0
    except ValueError as e:
        logging.exception("Value error occurred while parsing command line args: {}".format(e))
        print("Value error occurred while parsing command line args: {}".format(e))
        sys.exit(2)
    try:
        streamServer = PiCameraStreamServer()
        with picamera.PiCamera(resolution=userResolution, framerate=userFramerate) as camera:
            camera.rotation = userRotation
            camera.start_recording(streamServer.output, format='mjpeg')
            print("Camera has started recording: port={}, resolution={}, framerate={}, rotation={}".format(userPort, userResolution, userFramerate, userRotation))
            try:
                print("Serving video stream...")
                streamServer.server = StreamingServer(('', userPort), StreamingHandler)
                streamServer.server.serve_forever()
                print("Closing video stream.")
            finally:
                camera.stop_recording()
    except KeyboardInterrupt:
        sys.exit(0)