from service import Service, ListenerMixin
import time
import cv2

class CameraService(Service, ListenerMixin):
    def setup(self, input_video=0):
        self.cap = cv2.VideoCapture(input_video)

    def capture(self):
        retval, img = self.cap.read()
        if retval:
            self.send_message_to_listeners({
                'type': 'WEBCAM_CAPTURE',
                'payload': img,
                'time': time.time(),
            })
            return img

    def process_received_message(self, message):
        if message['type'] == 'STOP_CAPTURING':
            self.cap.release()
        elif message['type'] == 'START_CAPTURING':
            input_video = message['payload']
            self.cap = cv2.VideoCapture(input_video)

    def consume(self):
        self.capture()
