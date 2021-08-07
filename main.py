import pygame
from calibration_scene import CalibrationScene
from keyboard import KeyboardScene
from exit_scene import ExitScene
from yes_no_scene import YesNoScene
from menu import MenuScene
from settings import SettingsScene
from services import camera_service, eye_gaze_service, pygame_events_service
import time
import logging

pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((1920, 1080))
clock = pygame.time.Clock()
done = False

services = [camera_service, eye_gaze_service, pygame_events_service]

# current_scene = YesNoScene(screen)
# current_scene = KeyboardScene(screen)
# current_scene = CalibrationScene(screen)
current_scene = MenuScene(screen)
# current_scene = SettingsScene(screen)

scene_stack = [current_scene]
next_scene = None

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
while not done:
    clock.tick(60)
    screen.fill((255, 255, 255))

    current_scene.update()
    current_scene.draw()
    next_scene = current_scene.get_next_scene()

    for service in services:
        service.consume()

    # This is a mess
    if next_scene is not None:
        if type(next_scene) is ExitScene and len(scene_stack) > 0:
            current_scene = scene_stack.pop()
        elif type(next_scene) is ExitScene and len(scene_stack) == 0:
            current_scene = ExitScene()
        else:
            current_scene = next_scene
            scene_stack.append(current_scene)
        current_scene.next_scene = None

    if type(current_scene) is ExitScene:
        done = True

    pygame.display.flip()

pygame.quit()
