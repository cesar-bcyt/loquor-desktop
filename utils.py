import numpy as np
import pygame
import pygame.gfxdraw
import cv2

def convert_cv2_capture_to_pygame_surface(cv2Image):
    cv2Image = cv2.flip(cv2Image, 1)
    if cv2Image.dtype.name == 'uint16':
        cv2Image = (cv2Image / 256).astype('uint8')
    size = cv2Image.shape[1::-1]
    if len(cv2Image.shape) == 2:
        cv2Image = np.repeat(cv2Image.reshape(size[1], size[0], 1), 3, axis = 2)
        format = 'RGB'
    else:
        format = 'RGBA' if cv2Image.shape[2] == 4 else 'RGB'
        cv2Image[:, :, [0, 2]] = cv2Image[:, :, [2, 0]]
    surface = pygame.image.frombuffer(cv2Image.flatten(), size, format)
    return surface.convert_alpha() if format == 'RGBA' else surface.convert()

def point_is_in_rect(point, rect):
    x, y = point
    return rect[0] <= x <= rect[0]+rect[2] and rect[1] <= y <= rect[1]+rect[3]

def simplify(point):
    retval = [0, 0]
    if point[0] < 1920//3:
        retval[0] = -1
    elif 1920//3 <= point[0] < 1920//3*2:
        retval[0] = 0
    elif point[0] >= 1920//3*2:
        retval[0] = 1
    if point[1] < 1080//3:
        retval[1] = -1
    elif 1080//3 <= point[1] < 1080//3*2:
        retval[1] = 0
    elif point[1] >= 1080//3*2:
        retval[1] = 1
    return retval

def prediction_to_circle(pred):
    pred = (int(pred[0]), int(pred[1]))
    if pred[0] == -1:
        x = 100
    elif pred[0] == 0:
        x = 1920//2
    else:
        x = 1920-100
    y = 1080//2
    if pred[1] == 1 and pred[0] == 0:
        y = 1080-100
    return (x, y)

def distance(p1, p2):
    return np.sqrt( (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 )

def eye_aspect_ratio(shape):
    A = distance(shape[37], shape[41])
    B = distance(shape[38], shape[40])
    C = distance(shape[36], shape[39])
    return (A+B)/(2*C)

SCREEN_SECTORS = {
    (0,-1): 'TOP CENTER',
    (0, 0): 'CENTER CENTER',
    (0, 1): 'BOTTOM CENTER',

    (1,-1): 'TOP RIGHT',
    (1, 0): 'CENTER RIGHT',
    (1, 1): 'BOTTOM RIGHT',

    (-1,-1): 'TOP LEFT',
    (-1, 0): 'CENTER LEFT',
    (-1, 1): 'BOTTOM LEFT',
}

SCREEN_SECTORS_V2 = {
    (0,-1): 'CENTER',
    (0, 0): 'CENTER',
    (0, 1): 'CENTER',

    (1,-1): 'RIGHT',
    (1, 0): 'RIGHT',
    (1, 1): 'RIGHT',

    (-1,-1): 'LEFT',
    (-1, 0): 'LEFT',
    (-1, 1): 'LEFT',
}

screen_sector = None

def get_screen_sector(latest_positions):
    vertical = []
    horizontal = []
    length = len(latest_positions)
    for point in latest_positions:
        x, y = point
        if x < 1920//3-100:
            x = -1
        elif x > 1920/3*2+100:
            x = 1
        else:
            x = 0

        if y < 1080//3:
            y = -1
        elif y > 1080/3*2:
            y = 1
        else:
            y = 0
    if 'x' in locals():
        return SCREEN_SECTORS[(x, y)]
    else:
        return SCREEN_SECTORS[(0, 0)]

def get_screen_sector_v2(latest_positions):
    vertical = []
    horizontal = []
    length = len(latest_positions)
    for point in latest_positions:
        x, y = point
        if x < 1920//3:
            x = -1
        elif x > 1920/3*2:
            x = 1
        else:
            x = 0

        if y < 1080//3:
            y = -1
        elif y > 1080/3*2:
            y = 1
        else:
            y = 0
    return SCREEN_SECTORS_V2[(x, y)]

def draw_sectors(screen, focused=None):
    rects = [
        [        0, 0, 1920//3, 1080//3],
        [  1920//3, 0, 1920//3, 1080//3],
        [1920//3*2, 0, 1920//3, 1080//3],

        [        0, 1080//3, 1920//3, 1080//3],
        [  1920//3, 1080//3, 1920//3, 1080//3],
        [1920//3*2, 1080//3, 1920//3, 1080//3],

        [        0,2*1080//3, 1920//3, 1080//3],
        [  1920//3,2*1080//3, 1920//3, 1080//3],
        [1920//3*2,2*1080//3, 1920//3, 1080//3],
    ]
    rect_names = [
        'TOP LEFT',
        'TOP CENTER',
        'TOP RIGHT',

        'CENTER LEFT',
        'CENTER CENTER',
        'CENTER RIGHT',

        'BOTTOM LEFT',
        'BOTTOM CENTER',
        'BOTTOM RIGHT',
    ]
    colors = [
        [0, 0, 0],
        [255, 0, 0],
        [0, 255, 0],

        [0, 255, 0],
        [255, 255, 0],
        [0, 255, 255],

        [0, 0, 255],
        [255, 0, 255],
        [255, 255, 255],
    ]
    for rect, color, rect_name in zip(rects, colors, rect_names):
        if focused == rect_name:
            pygame.gfxdraw.box(screen, rect, (color[0], color[1], color[2], 255))
        else:
            pygame.gfxdraw.box(screen, rect, (color[0], color[1], color[2], 100))

def draw_sectors_v2(screen, focused=None):
    rects = [
        [        0, 0, 1920//3, 1080],
        [  1920//3, 0, 1920//3, 1080],
        [1920//3*2, 0, 1920//3, 1080],
    ]
    rect_names = [
        'LEFT',
        'CENTER',
        'RIGHT',
    ]
    colors = [
        [255, 0, 0],
        [0, 255, 0],
        [0, 0, 255],
    ]
    for rect, color, rect_name in zip(rects, colors, rect_names):
        if focused == rect_name:
            pygame.gfxdraw.box(screen, rect, (color[0], color[1], color[2], 255))
        else:
            pygame.gfxdraw.box(screen, rect, (color[0], color[1], color[2], 100))

def get_gaze_movement_direction(latest_positions):
    vertical = []
    horizontal = []
    length = len(latest_positions)
    for index in range(len(latest_positions)-1):
        vertical.append(latest_positions[index+1][1] - latest_positions[index][1] > 0)
        horizontal.append(latest_positions[index+1][0] - latest_positions[index][0] > 0)
    if horizontal.count(True) > length//2:
        return 'RIGHT'
    elif horizontal.count(False) > length//2:
        return 'LEFT'
    elif vertical.count(True) > length//2:
        return 'DOWN'
    elif vertical.count(False) > length//2:
        return 'UP'
    return '·'

def get_gesture(latest_positions, last_eye_states):
    # does not work
    pos = [simplify(point) for point in latest_positions]
    left_gazes = pos.count([-1, -1]) + pos.count([-1, 0]) + pos.count([-1, 1])
    right_gazes = pos.count([1, -1]) + pos.count([1, 0]) + pos.count([1, 1])
    up_gaze = pos.count([-1, -1]) + pos.count([0, -1]) + pos.count([1, -1])
    if last_eye_states[10:].count(True) >= 3:
        return 'BLINKING_RAPIDLY'
    return ''
