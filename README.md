# Pi-Video-Stream

Pi-Video-Stream is a PiCamera tool that consists of a server (stream.py), which provides live video frames taken by any PiCamera (https://readthedocs.org/projects/picamera/) via a http server running on a Raspberry Pi (of any flavor), and a client (streamView.py), 
which provides a simple GUI for connecting to and viewing the stream retrieved from the http server.
## Setup
1. Plug in and enable your PiCamera on your Raspberry Pi flavor of choice.
2. Ensure that your RaspberryPi is connected to your home network.
3. Run the stream.py module by entering the following command in a terminal: 'python3 stream.py'
4. On the client computer, run the streamView.py module.
5. Enter the IP address of your RaspberryPi video server and click 'Connect'.

Alternatively, you can simply open a browser after launching the http server on your Pi and type: http://[Pi IP address]:[Pi http server port]/ into the navbar.

## Dependencies
### Server (stream.py)
- PiCamera
### Client/Viewer (streamView.py)
- PyQt5
- OpenCV
## Problems?
Create an issue. Additionally, pull requests are welcome.
