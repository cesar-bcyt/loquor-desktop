import random
import mediapipe as mp
import tensorflow as tf
import time
import numpy as np
import pygame
import cv2

DEBUG = False

CALIBRATION_SAMPLES = 100

THRESHOLDS = {
    'LEFT': 0.5035862952836636,
    'RIGHT': 0.5713325928457507,
}

CALIBRATION = {
    'LEFT': [],
    'CENTER': [],
    'RIGHT': [],
}

POSITIONING_SAMPLES = 4

POINT_DRAW_POSITIONS = {
    (-1,-1): (1920*1/10, 1080*1/10),
    ( 0,-1): (1920*5/10, 1080*1/10),
    ( 1,-1): (1920*9/10, 1080*1/10),

    (-1, 0): (1920*1/10, 1080*5/10),
    ( 0, 0): (1920*5/10, 1080*5/10),
    ( 1, 0): (1920*9/10, 1080*5/10),

    (-1, 1): (1920*1/10, 1080*9/10),
    ( 0, 1): (1920*5/10, 1080*9/10),
    ( 1, 1): (1920*9/10, 1080*9/10),
}

POINT_DRAW_POSITIONS = {pos: (int(p[0]), int(p[1])) for pos, p in POINT_DRAW_POSITIONS.items()}

pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((1920, 1080))
clock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 20)
colors = {i: (random.randint(1, 255), random.randint(1, 255), random.randint(1, 255)) for i in range(100)}
pygame.mixer.init()
beep_sound = pygame.mixer.Sound('./beep.wav')

def create_intermediate_representation(input_size, iris_landmarks, eye_landmarks):
    result = pygame.Surface((64, 64))
    _result = pygame.Surface(input_size)
    _result.fill((255, 255, 255))
    center = iris_landmarks[0]
    radius_x = iris_landmarks[1][0] - iris_landmarks[0][0]
    radius_y = iris_landmarks[0][1] - iris_landmarks[2][1]
    ellipse_rect = (center[0] - radius_x,
                    center[1] - radius_y,
                    radius_x*2,
                    radius_y*2)
    pygame.draw.ellipse(_result, (0, 0, 0), ellipse_rect)
    pygame.draw.circle(_result, (255, 255, 0), center, 2)
    eye_size_x = eye_landmarks[30][0] - eye_landmarks[0][0]
    eye_size_y = eye_landmarks[8][1] - eye_landmarks[24][1]
    eye_aspect_ratio = eye_size_y/eye_size_x
    relative_center_position = (
            (center[0] - eye_landmarks[0][0])/eye_size_x,
            (center[1] - eye_landmarks[0][1])) # elevation from center line
    for index in range(0, len(eye_landmarks), 2):
        pygame.draw.line(_result,
                (0, 0, 0),
                eye_landmarks[index],
                eye_landmarks[index+1], 1)
    result.blit(_result, (0, 0), (eye_landmarks[0][0], eye_landmarks[0][1]-32, 64, 64))
    imgdata = pygame.surfarray.array3d(result)
    imgdata = imgdata.swapaxes(0,1)
    imgdata = cv2.cvtColor(imgdata, cv2.COLOR_RGB2GRAY)
    imgdata = imgdata/255
    imgdata = np.logical_not(imgdata).astype(float)
    return result, imgdata, relative_center_position, eye_aspect_ratio

latest_center_positions = []

EYE_CONTOUR_INDICES = [
    33, 7,
    7, 163,
    163, 144,
    144, 145,
    145, 153,
    153, 154,
    154, 155,
    155, 133,
    33, 246,
    246, 161,
    161, 160,
    160, 159,
    159, 158,
    158, 157,
    157, 173,
    173, 133,
]

mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh()
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

mp_iris = mp.solutions.iris
iris = mp_iris.Iris()

cap = cv2.VideoCapture(0)

paused = False
done = False
calibrating = False

current_area = (0, 0)

while not done:
    iris_landmarks = []
    eye_landmarks = []
    clock.tick(60)
    screen.fill((255, 255, 255))

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                done = True
            elif event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_w:
                calibrating = not calibrating

    if not paused:
        retval, img = cap.read()
        img = cv2.flip(img, 1)

        try:
            face_mesh_results = face_mesh.process(img)
        except AttributeError:
            print('['+str(time.time())+'] No face found')
            continue

        results = iris.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if results.face_landmarks_with_iris:
            for eye_contour_index in EYE_CONTOUR_INDICES:
                landmark = results.face_landmarks_with_iris.landmark[eye_contour_index]
                eye_landmarks.append(
                    (int(landmark.x*img.shape[1]),
                     int(landmark.y*img.shape[0])))
            for index, landmark in enumerate(results.face_landmarks_with_iris.landmark):
                if 467 < index:
                    iris_landmarks.append(
                        (int(landmark.x*img.shape[1]),
                         int(landmark.y*img.shape[0])))
        if len(iris_landmarks) > 0:
            intermediate_representation, intermediate_representation_array, relative_center_position, eye_aspect_ratio = create_intermediate_representation((640, 480), iris_landmarks, eye_landmarks)
            if DEBUG:
                intermediate_representation = pygame.transform.scale(intermediate_representation,
                        (10*intermediate_representation.get_width(),
                         10*intermediate_representation.get_height(),
                        ))
                screen.blit(intermediate_representation, (0, 0))
            latest_center_positions.append(relative_center_position)
            if len(latest_center_positions) > POSITIONING_SAMPLES:
                latest_center_positions.pop(0)
            sum_x = sum([p[0] for p in latest_center_positions])
            sum_y = sum([p[1] for p in latest_center_positions])
            average_center_position = (sum_x/len(latest_center_positions), sum_y/len(latest_center_positions))

            if calibrating:
                f = font.render('LOOK HERE', True, (0, 0, 0))
                if len(CALIBRATION['LEFT']) < CALIBRATION_SAMPLES:
                    calibration_progress = len(CALIBRATION['LEFT'])/CALIBRATION_SAMPLES
                    pygame.draw.circle(screen, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*1/10), int(1080*1/2)), 50-int(30*calibration_progress))
                    screen.blit(f, (int(1920*1/10), int(1080*1/2)))
                    CALIBRATION['LEFT'].append(relative_center_position[0])

                elif len(CALIBRATION['CENTER']) < CALIBRATION_SAMPLES:
                    calibration_progress = len(CALIBRATION['CENTER'])/CALIBRATION_SAMPLES
                    pygame.draw.circle(screen, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*2/4), int(1080*1/2)), 50-int(30*calibration_progress))
                    screen.blit(f, (int(1920*5/10), int(1080*1/2)))
                    CALIBRATION['CENTER'].append(relative_center_position[0])

                elif len(CALIBRATION['RIGHT']) < CALIBRATION_SAMPLES:
                    calibration_progress = len(CALIBRATION['RIGHT'])/CALIBRATION_SAMPLES
                    pygame.draw.circle(screen, (255*(1-calibration_progress), 255*calibration_progress, 0), (int(1920*9/10), int(1080*1/2)), 50-int(30*calibration_progress))
                    screen.blit(f, (int(1920*9/10), int(1080*1/2)))
                    CALIBRATION['RIGHT'].append(relative_center_position[0])

                else:
                    left = sum(CALIBRATION['LEFT'])/CALIBRATION_SAMPLES
                    center = sum(CALIBRATION['CENTER'])/CALIBRATION_SAMPLES
                    right = sum(CALIBRATION['RIGHT'])/CALIBRATION_SAMPLES
                    left += (center-left)/2
                    right -= (right-center)/2
                    if DEBUG:
                        print('OLD THRESHOLDS')
                        print(THRESHOLDS)
                        print('NEW THRESHOLDS')
                    THRESHOLDS['LEFT'] = left
                    THRESHOLDS['RIGHT'] = right
                    if DEBUG:
                        print(THRESHOLDS)
                    calibrating = not calibrating

            else:
                if average_center_position[0] < THRESHOLDS['LEFT']:
                    current_area = (-1, current_area[1])
                elif THRESHOLDS['LEFT'] <= average_center_position[0] < THRESHOLDS['RIGHT']:
                    current_area = (0, current_area[1])
                elif THRESHOLDS['RIGHT'] <= average_center_position[0]:
                    current_area = (1, current_area[1])

                if len(latest_center_positions) >= POSITIONING_SAMPLES and average_center_position[1] <= -3:
                    if current_area[1] == 0:
                        current_area = (current_area[0], -1)
                    elif current_area[1] == -1:
                        current_area = (current_area[0], 1)
                    elif current_area[1] == 1:
                        current_area = (current_area[0], 0)
                    latest_center_positions = []

                pygame.draw.circle(screen, (255, 0, 0), POINT_DRAW_POSITIONS[current_area], 30)

                if DEBUG:
                    f = font.render(str(average_center_position), True, (0, 0, 0))
                    screen.blit(f, (1920//2, 1080-80))
                    f = font.render('EAR: '+str(eye_aspect_ratio), True, (0, 0, 0))
                    screen.blit(f, (1920//2, 1080-120))

                if eye_aspect_ratio < 0.1 and not pygame.mixer.get_busy():
                    beep_sound.play()

        pygame.display.flip()
