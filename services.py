from eye_gaze_service import EyeGazeService
from camera_service import CameraService
from pygame_events_service import PygameEventsService

camera_service = CameraService()
eye_gaze_service = EyeGazeService()
pygame_events_service = PygameEventsService()

camera_service.register_listener(eye_gaze_service)
pygame_events_service.register_listener(eye_gaze_service)
