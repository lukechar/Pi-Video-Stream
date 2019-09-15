# Author: Luke Charbonneau, 2019
# Released under the GPL-3.0 license
# Github Repo: https://github.com/lukechar/Pi-Video-Stream

import cv2
import time
import sys
import os

from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.Qt import QApplication, QThread, QPixmap, QIcon

from resources.ui_mainWindow import Ui_MainWindow

RESOURCES_FOLDER_NAME = "resources"

DEFAULT_PORT = 8000
CONNECT_MAX_WAIT_SECONDS = 3

class VideoWorker(QtCore.QObject):

    newImage = QtCore.pyqtSignal(QtGui.QPixmap)
    finished = QtCore.pyqtSignal()

    def __init__(self, address, port):
        super(VideoWorker, self).__init__()
        self.ip = address
        if not port:
            self.port = DEFAULT_PORT
        else:
            self.port = port
        self.stop = False
        self.connectionSuccess = None

    @QtCore.pyqtSlot()
    def run(self):
        try:
            cap = cv2.VideoCapture('http://{}:{}/stream.mjpg'.format(self.ip, self.port))
            if not cap.isOpened():
                raise Exception("Unable to open stream.")
            while cap.isOpened() and not self.stop:
                res, frame = cap.read()
                if res:
                    self.connectionSuccess = True
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = QtGui.QImage(rgb_image.data, rgb_image.shape[1], rgb_image.shape[0], QtGui.QImage.Format_RGB888)
                    pixmap = QtGui.QPixmap()
                    pixmap.convertFromImage(img)
                    self.newImage.emit(pixmap)
                if not res:
                    raise Exception("Error getting frame from stream.")
        except Exception as e:
            print(e)
            self.connectionSuccess = False
        finally:
            cap.release()
            self.finished.emit()
    def stopStream(self):
        self.stop = True
            
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(os.path.join(RESOURCES_FOLDER_NAME, "camera.ico")))
        self.assignWidgets()
        self.video = None
        self.videoThread = None
        self.pixmap = None
        
    def assignWidgets(self):
        self.actionInfo.triggered.connect(self.showInfo)
        self.snapImage_button.clicked.connect(self.saveImage)
        self.connect_button.clicked.connect(self.connectToStream)
        self.disconnect_button.clicked.connect(self.disconnectPressed)
        self.videoLabel.setVisible(False)
        
    def showMessage(self, message, title, rich=False):
        msg = QtWidgets.QMessageBox()
        msg.setWindowIcon(QtGui.QIcon(os.path.join(RESOURCES_FOLDER_NAME, 'camera.ico')))
        if rich:
            msg.setTextFormat(QtCore.Qt.RichText)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def showInfo(self):
        self.showMessage("Luke Charbonneau, 2019<br><br>Released under the GPL-3.0 license<br>Github Repo: {}".format('''<a href=https://github.com/lukechar/Pi-Video-Stream>https://github.com/lukechar/Pi-Video-Stream</a>'''), "Pi Camera Viewer Info", True)

    @QtCore.pyqtSlot(QtGui.QPixmap)
    def setFrame(self, frame):
        self.videoLabel.setPixmap(frame)
        self.pixmap = frame
        QApplication.processEvents()
        
    def connectToStream(self):
        self.videoLabel.setText("  Stream Loading...  ")
        self.videoLabel.setVisible(True)
        # Disable resolution combobox, ip lineEdit and connect button
        self.updateControls(True)
        # Get ip address from line edit
        ip = self.ip_lineEdit.text().strip()
        port = None
        # If a port was provided, set as port attribute and remove it from the ip string
        if ':' in ip:
            try:
                port = int(ip[ip.find(':') + 1:])
            except ValueError:
                self.showMessage("Cannot read port entered. Enter as format: [IP address]:[Port Number].", "Port Read Error")
                self.disconnectPressed()
                return
            ip = ip[:ip.find(':')]
        # Video stream
        try:
            self.video = VideoWorker(ip, port)
            self.videoThread = QtCore.QThread()
            #self.videoThread.started.connect(self.video.run)
            self.video.moveToThread(self.videoThread)
            self.video.newImage.connect(self.setFrame)
            self.videoThread.finished.connect(self.video.deleteLater)
            self.videoThread.start()
            QtCore.QTimer.singleShot(1, self.video.run)
            # Wait for video stream to connect
            startWait = time.time()
            while self.video.connectionSuccess is None:
                if time.time() - startWait > CONNECT_MAX_WAIT_SECONDS:
                    raise Exception("Timeout while waiting for connection to camera stream server.")
                QApplication.processEvents()
        except Exception as e:
            pass
        finally:
            if self.video and not self.video.connectionSuccess:
                if not port:
                    port = DEFAULT_PORT
                self.showMessage("Unable to connect to Pi camera stream server at {}:{}.".format(ip, port), "Connection Error")
                self.disconnectPressed()
        
    def disconnectPressed(self):
        self.videoLabel.setVisible(False)
        self.disconnectFromStream()
        if self.videoThread:
            self.videoThread.terminate()
            self.videoThread.wait()
        self.video = None
        self.videoThread = None
        
    def disconnectFromStream(self):
        if self.video:
            self.video.stopStream()
        self.updateControls(False)
        
    def updateControls(self, streamRunning):
        # Disable disconnect button and snap image button
        self.disconnect_button.setEnabled(streamRunning)
        self.snapImage_button.setEnabled(streamRunning)
        # Enable resolution combobox, ip lineEdit and connect button
        self.connect_button.setEnabled(not streamRunning)
        self.ip_lineEdit.setEnabled(not streamRunning)
        
    def saveImage(self):
        if not os.path.exists('snaps'):
            os.mkdir('snaps')
        # Increment image names in sequence
        i = 1
        while os.path.exists(os.path.join('snaps', 'snap{}.png'.format(i))):
            i += 1 
        filename = os.path.join('snaps', 'snap{}.png'.format(i))
        self.pixmap.save(filename, 'png')
        
if __name__ == '__main__':
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
