import pygame
from styles import BG_COLOR
from scene import Scene
from exit_scene import ExitScene
from service import ListenerMixin
from services import camera_service, eye_gaze_service, pygame_events_service
from utils import convert_cv2_capture_to_pygame_surface
from reload_config_service import reload_config_service
import json
import logging

class CalibrationScene(Scene, ListenerMixin):
    def __init__(self, screen):
        super().__init__(screen)
        logging.debug('debug')
        pygame_events_service.register_listener(self)
        camera_service.register_listener(self)
        eye_gaze_service.register_listener(self)
        self.webcam_image = None
        self.calibration_samples = 100
        self.config = json.load(open('./config.json', 'r'))
        self.thresholds = self.config['thresholds']
        self.calibration = {
            'LEFT': [],
            'CENTER': [],
            'CENTERV': [],
            'RIGHT': [],
            'TOP': [],
            'BOTTOM': [],
        }
        self.instructions_timer = 0
        self.instructions_timer_limit = 60
        self.calibrating = 'LEFT'
        self.font = pygame.font.SysFont('Arial', 30)
        self.drawing_surface = pygame.Surface(screen.get_size())
        self.relative_center_position = [-1, -1]

    def update(self):
        relative_center_position = self.relative_center_position
        f = self.font.render('MIRA AQUÍ', True, (255, 255, 255))

        if self.webcam_image is not None:
            webcam_image_size = self.webcam_image.get_size()
            self.draw_positioning_rectangle_on_webcam_image(webcam_image_size)
            self.drawing_surface.blit(self.webcam_image, ( (1920-webcam_image_size[0])//2, (1080-webcam_image_size[1])//2))

        if self.instructions_timer >= self.instructions_timer_limit:
            if len(self.calibration['LEFT']) < self.calibration_samples:
                calibration_progress = len(self.calibration['LEFT'])/self.calibration_samples
                pygame.draw.circle(self.drawing_surface, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*1/10), int(1080*1/2)), 50-int(30*calibration_progress))
                self.drawing_surface.blit(f, (int(1920*1/10)-f.get_width()//2, int(1080*1/2)+80))
                self.calibration['LEFT'].append(relative_center_position[0])

            elif len(self.calibration['CENTER']) < self.calibration_samples:
                calibration_progress = len(self.calibration['CENTER'])/self.calibration_samples
                pygame.draw.circle(self.drawing_surface, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*2/4), int(1080*1/2)), 50-int(30*calibration_progress))
                self.drawing_surface.blit(f, (int(1920*5/10-70), int(1080*1/2+50)))
                self.calibration['CENTER'].append(relative_center_position[0])
                self.calibration['CENTERV'].append(relative_center_position[1])

            elif len(self.calibration['RIGHT']) < self.calibration_samples:
                calibration_progress = len(self.calibration['RIGHT'])/self.calibration_samples
                pygame.draw.circle(self.drawing_surface, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*9/10), int(1080*1/2)), 50-int(30*calibration_progress))
                self.drawing_surface.blit(f, (int(1920*9/10-75), int(1080*1/2+50)))
                self.calibration['RIGHT'].append(relative_center_position[0])

            elif len(self.calibration['TOP']) < self.calibration_samples:
                calibration_progress = len(self.calibration['TOP'])/self.calibration_samples
                pygame.draw.circle(self.drawing_surface, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*2/4), int(1080*1/10)), 50-int(30*calibration_progress))
                self.drawing_surface.blit(f, (int(1920*2/4-75), int(1080*1/10+50)))
                self.calibration['TOP'].append(relative_center_position[1])

            elif len(self.calibration['BOTTOM']) < self.calibration_samples:
                calibration_progress = len(self.calibration['BOTTOM'])/self.calibration_samples
                pygame.draw.circle(self.drawing_surface, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*2/4), int(1080*9/10)), 50-int(30*calibration_progress))
                self.drawing_surface.blit(f, (int(1920*2/4-75), int(1080*9/10+50)))
                self.calibration['BOTTOM'].append(relative_center_position[1])

            else:
                left = sum(self.calibration['LEFT'])/self.calibration_samples
                center = sum(self.calibration['CENTER'])/self.calibration_samples
                centerv = sum(self.calibration['CENTERV'])/self.calibration_samples
                right = sum(self.calibration['RIGHT'])/self.calibration_samples
                top = sum(self.calibration['TOP'])/self.calibration_samples
                bottom = sum(self.calibration['BOTTOM'])/self.calibration_samples

                left += (center-left)/2
                right -= (right-center)/2
                print('TOP', top)
                print('BOTTOM', bottom)
                print('centerv', centerv)
                top += (centerv-top)/4
                bottom -= (bottom-centerv)/4

                logging.debug('OLD THRESHOLDS')
                logging.debug(self.thresholds)
                logging.debug('NEW THRESHOLDS')
                self.thresholds['LEFT'] = left
                self.thresholds['RIGHT'] = right
                self.thresholds['TOP'] = top
                self.thresholds['BOTTOM'] = bottom
                logging.debug(self.thresholds)
                self.config['thresholds'] = self.thresholds
                json.dump(self.config, open('./config.json', 'w'))
                reload_config_service.reload()
                self.next_scene = ExitScene()

    def draw_positioning_rectangle_on_webcam_image(self, size):
        a = .8
        b = .2
        rect_size = (1920*b, 1080*.27)
        vertices = [
            (int(size[0]*a), int(size[1]*b)),
            (int(size[0]*b), int(size[1]*b)),
            (int(size[0]*b), int(size[1]*a)),
            (int(size[0]*a), int(size[1]*a)),
        ]
        pygame.draw.rect(self.webcam_image, (0, 128, 0), (vertices[1][0], vertices[1][1], rect_size[0]+1, rect_size[1]-2), 5)
        for vertex in vertices:
            if vertex[0] > size[0]/2 and vertex[1] < size[1]/2:
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0], vertex[1]), (vertex[0], vertex[1]+50), 5)
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0]+2, vertex[1]), (vertex[0]-52, vertex[1]), 5)
            elif vertex[0] > size[0]/2 and vertex[1] > size[1]/2:
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0], vertex[1]), (vertex[0], vertex[1]-50), 5)
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0]+2, vertex[1]), (vertex[0]-52, vertex[1]), 5)
            elif vertex[0] < size[0]/2 and vertex[1] < size[1]/2:
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0], vertex[1]), (vertex[0], vertex[1]+50), 5)
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0]-2, vertex[1]), (vertex[0]+52, vertex[1]), 5)
            elif vertex[0] < size[0]/2 and vertex[1] > size[1]/2:
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0], vertex[1]), (vertex[0], vertex[1]-50), 5)
                pygame.draw.line(self.webcam_image, (0, 255, 0), (vertex[0]-2, vertex[1]), (vertex[0]+52, vertex[1]), 5)

    def draw(self):
        self.screen.blit(self.drawing_surface, (0, 0))
        self.drawing_surface.fill(BG_COLOR)
        if self.webcam_image and self.instructions_timer < self.instructions_timer_limit:
            title = self.font.render('Coloca tu cara dentro del rectángulo'+'.'*(self.instructions_timer%4), True, (255, 255, 255))
            self.drawing_surface.blit(title, ((1920-self.webcam_image.get_width())//2, 1080*2.3/10))
            self.instructions_timer += 1

    def process_received_message(self, message):
        if message['type'] == 'PYGAME_EVENT':
            for event in message['payload']:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.next_scene = ExitScene()
        elif message['type'] == 'EYE_GAZE':
            self.relative_center_position = message['payload']['relative_center_position']
        elif message['type'] == 'WEBCAM_CAPTURE':
            self.webcam_image = convert_cv2_capture_to_pygame_surface(message['payload'])
