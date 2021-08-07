DEBUG = False
DEMO = False

from exceptions import LoquorQuit, NoFaceDetected
from tree import get_data
from utils import eye_aspect_ratio, get_gesture, get_screen_sector, simplify, prediction_to_circle
from imutils import face_utils
from styles import BG_COLOR, HIGHLIGHTED_COLOR, DARKER_THAN_BG_COLOR
import numpy as np
import subprocess
import cv2
import dlib
import pygame
import tensorflow as tf

SCREEN_BG_COLOR = BG_COLOR
TEXTBOX_COLOR = DARKER_THAN_BG_COLOR
TEXT_COLOR = (255, 255, 255)
TYPED_TEXT_COLOR = (255, 255, 255)

if DEMO:
    BG_COLOR = (0, 0, 0)
    DARKER_THAN_BG_COLOR = (0, 0, 0)
    SCREEN_BG_COLOR = (255, 255, 255)
    TEXTBOX_COLOR = (0, 0, 0)
    TYPED_TEXT_COLOR = (255, 255, 255)
    TEXT_COLOR = (0, 0, 0)

FACE_LANDMARK_MODEL = "./shape_predictor_68_face_landmarks.dat"

# SOUNDS = {
#     'monitor': pygame.mixer.Sound(file='./monitor.wav')
# }
# SOUNDS['monitor'].play()

training_dots = {
    'top': (1920//2, 30),
    'top_left': (30, 30),
    'top_right': (1920-30, 30),
    'bottom': (1920//2, 1080-30),
    'bottom_left': (30, 1080-30),
    'bottom_right': (1920-30, 1080-30),
    'left': (30, 1080//2),
    'right': (1920-30, 1080//2),
    'center': (1920//2, 1080//2),
}

class Keyboard(object):
    FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE = 15
    DICTIONARY = [word.replace('\n', '') for word in open('./diccionario.csv').readlines()]
    def __init__(self):
        self.typed_message = ""
        self.closest_word = ""
        self.font_size = 50
        self.font = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', self.font_size)
        self.say_phrase_cooldown = 0
        self.last_eye_states = [False]*30

        self.big_font_size = 70
        self.big_font = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', self.big_font_size)

        self.offsets = {
            'LEFT': (30, 1080//3+30),
            'RIGHT': (1920-120, 1080//3+30),
            'CENTER': (1920//2, 1080//3+30),
            'BOTTOM': (1920//2, 1080-150)
        }
        self.reset_to_top_keyboard_level()

        self.blinking_cursor_timer = 1
        self.blinking_cursor_is_black = False

    def add_space(self):
        self.typed_message += ' '

    def select_closest_word(self):
        if len(self.typed_message) > 1:
            self.typed_message = ' '.join(self.typed_message.split(' ')[:-1]) + ' ' + self.closest_word + ' '
        elif self.closest_word is not None:
            self.typed_message = self.closest_word + ' '
        # self.closest_word = n_gram_most_likely_word(self.closest_word)

    def get_closest_word(self, typed_message=None):
        # typed_message = self.typed_message if typed_message is None else typed_message
        typed_message = self.typed_message.split(' ')[-1]
        # distances = [(index, Levenshtein.distance(word, typed_message)) for index, word in enumerate(self.DICTIONARY)]
        best_matching_letters = ('', 0)
        for word in self.DICTIONARY:
            current_matching_letters = 0
            for i in range(len(typed_message)):
                if len(word) > i and word[i].lower() == typed_message[i].lower():
                        current_matching_letters += 1
            if current_matching_letters > best_matching_letters[1]:
                best_matching_letters = (word, current_matching_letters)
        self.groups['BOTTOM'] = best_matching_letters[0].upper()
        return best_matching_letters[0].upper()

    def reset_to_top_keyboard_level(self):
        self.tree_path = ''
        self._last_highlighted = []
        alphabet_tree_root_data, _ = get_data('/')
        self.groups = {
            'LEFT': alphabet_tree_root_data[0],
            'CENTER': None,
            'RIGHT': alphabet_tree_root_data[1],
            'PREV': ['M1', 'M2'],
            'BOTTOM': '',
        }
        self.select_progress_bars = {
            'LEFT': 0,
            'CENTER': 0,
            'RIGHT': 0,
            'BOTTOM': 0,
        }
        self.STATE = 'SELECTING_LETTER_GROUPS' # 'SELECTING_LETTER_GROUPS' and 'SELECTING_INDIVIDUAL_LETTERS'
        self._highlighted = None

    def highlight_or_select(self, group):
        assert group in ['LEFT', 'RIGHT', 'CENTER', 'TOP', 'BOTTOM', None]
        self._highlighted = group
        self._last_highlighted.append(group)

        gazed_at = {
            'LEFT': self._last_highlighted.count('LEFT'),
            'CENTER': self._last_highlighted.count('CENTER'),
            'RIGHT': self._last_highlighted.count('RIGHT'),
            'BOTTOM': self._last_highlighted.count('BOTTOM')
        }

        for g in ['LEFT', 'RIGHT', 'CENTER', 'BOTTOM']:
            if g == group:
                self.select_progress_bars[g] = (self.select_progress_bars[g] + gazed_at[g]) / Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE
            else:
                self.select_progress_bars[g] = max(0, self.select_progress_bars[g] - 1 / Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE)

        if len(self._last_highlighted) > 60:
            self._last_highlighted.pop(0)
        if group == 'PREV':
            self._last_highlighted = []
            self._select('PREV')
        elif self._last_highlighted.count(None) > Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._last_highlighted = []
        elif gazed_at['LEFT'] > Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('LEFT')
        elif gazed_at['RIGHT'] > Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('RIGHT')
        elif gazed_at['CENTER'] > Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('CENTER')
        elif gazed_at['BOTTOM'] > Keyboard.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('BOTTOM')

    def __select_prev(self):
        pass

    def _select(self, group):
        if self.STATE == 'SELECTING_INDIVIDUAL_LETTERS':
            letter, tree = get_data(self.tree_path)
            if group == 'PREV':
                self.tree_path = '/'.join(self.tree_path.split('/')[:-1])
            elif group == 'LEFT':
                self.__add_letter_to_typed_message(letter[0])
            elif group == 'RIGHT':
                if tree.data_len() == 2:
                    self.__add_letter_to_typed_message(letter[1])
                elif tree.data_len() == 3:
                    self.__add_letter_to_typed_message(letter[2])
            elif group == 'CENTER':
                self.__add_letter_to_typed_message(letter[1])
            elif group == 'BOTTOM':
                self.select_closest_word()
            self.reset_to_top_keyboard_level()
        elif self.STATE == 'SELECTING_LETTER_GROUPS':
            if group == 'PREV':
                self.tree_path = '/'.join(self.tree_path.split('/')[:-1])
            elif group == 'LEFT':
                self.tree_path += '/left'
            elif group == 'RIGHT':
                self.tree_path += '/right'
            elif group == 'CENTER':
                self.typed_message += letter[1]
            elif group == 'BOTTOM':
                self.select_closest_word()
            data, node = get_data(self.tree_path)
            if type(data[0]) is str and type(data[1]) is str:
                self.STATE = 'SELECTING_INDIVIDUAL_LETTERS'
            if len([x for x in node.data if x is not None]) == 3:
                self.groups = {
                    'LEFT': data[0],
                    'CENTER': data[1],
                    'RIGHT': data[2],
                    'BOTTOM': self.closest_word,
                }
            else:
                self.groups = {
                    'LEFT': data[0],
                    'CENTER': None,
                    'RIGHT': data[1],
                    'BOTTOM': self.closest_word,
                }
            self._last_highlighted = []
            self.closest_word = None # signals recalc of closest word on next draw()

        def __assign_groups(self, left, right):
            self.groups = {
                'LEFT': left,
                'RIGHT': right,
                'PREV': [self.groups['LEFT'], self.groups['RIGHT']]
            }

    def say_phrase(self):
        subprocess.Popen(['/usr/bin/espeak', '-v', 'es-la', '-s', '120', '"'+self.typed_message+'"'])

    def update(self, gaze_positions, eyes_are_closed):
        self.say_phrase_cooldown = max(0, self.say_phrase_cooldown-1)
        sector = get_screen_sector(gaze_positions)
        self.last_eye_states.append(eyes_are_closed)
        if len(self.last_eye_states) > 30:
            self.last_eye_states.pop(0)
        if self.STATE == 'SELECTING_LETTER_GROUPS':
            if eyes_are_closed:
                if len(self.typed_message) > 0 and self.typed_message[-1] != ' ':
                    if DEMO and len(self.typed_message.split(' ')[-1]) == 1 and self.typed_message.split(' ')[-1] in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'Ñ', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'X', 'Z']:
                        pass
                    else:
                        self.add_space()
                elif self.say_phrase_cooldown <= 0:
                    self.say_phrase()
                    self.say_phrase_cooldown = 30
                # self.highlight_or_select('PREV')
                # self._select('PREV')
            elif 'TOP' in sector:
                self.highlight_or_select('TOP')
            elif 'LEFT' in sector:
                self.highlight_or_select('LEFT')
            elif 'RIGHT' in sector:
                self.highlight_or_select('RIGHT')
            elif 'BOTTOM' in sector:
                self.highlight_or_select('BOTTOM')
            else:
                self.highlight_or_select(None)
        elif self.STATE == 'SELECTING_INDIVIDUAL_LETTERS':
            if eyes_are_closed:
                if self.typed_message[-1] != ' ':
                    self.add_space()
                elif self.say_phrase_cooldown <= 0:
                    self.say_phrase()
                # self.highlight_or_select('PREV')
                # self._select('PREV')
            elif 'LEFT' in sector:
                self.highlight_or_select('LEFT')
            elif 'RIGHT' in sector:
                self.highlight_or_select('RIGHT')
            elif 'CENTER' in sector:
                self.highlight_or_select('CENTER')

    def __add_letter_to_typed_message(self, letter):
        if letter == '_':
            self.typed_message += ' '
        elif letter == '⬅️':
            self.typed_message = self.typed_message[:-1] if len(self.typed_message) > 0 else self.typed_message
        else:
            self.typed_message += letter[0]

    def draw_closest_word(self, screen):
        if len(self.typed_message) > 0:
            self.closest_word = self.get_closest_word()
            text = self.big_font.render(self.closest_word, 1, TEXT_COLOR)
            w, h = text.get_size()
            screen.blit(text, ((1920-w)//2, 1080-150))
            # pygame.draw.rect(screen, (255, 0, 0),  ((1920-w)//2 - 10, 1080-150 - 10, w+10, h+10), 5)

    def draw_menu_rects(self, screen):
        text = self.big_font.render('BORRAR', 1, TEXT_COLOR)
        w, h = text.get_size()
        screen.blit(text, ((1920-w)//2, 1080-150))
        pygame.draw.rect(screen, (255, 0, 0),  ((1920-w)//2 - 10, 1080-150 - 10, w+10, h+10), 5)

        text = self.big_font.render('VOLVER', 1, TEXT_COLOR)
        w, h = text.get_size()
        screen.blit(text, ((1920-w)//2, 10))
        pygame.draw.rect(screen, (255, 0, 0), ((1920-w)//2 - 10, 10, w+10, h+10), 5)

    def draw_eye_states(self, screen):
        offset = (30, 1080-30)
        x = 0
        for state in self.last_eye_states:
            if state:
                pygame.draw.rect(screen, TEXT_COLOR, (offset[0]+x, offset[1]-30, 10, 30))
            else:
                pygame.draw.rect(screen, TEXT_COLOR, (offset[0]+x, offset[1], 10, 30))
            x += 10

    def draw(self):
        self.draw_closest_word(screen)
        pygame.draw.rect(screen, TEXTBOX_COLOR, (290, 30, 1340, 250))
        text = self.big_font.render(self.typed_message, 1, TYPED_TEXT_COLOR)
        screen.blit(text, (305, 35))
        self.blinking_cursor_timer += 1
        if self.blinking_cursor_timer % 3 == 0:
            self.blinking_cursor_is_black = not self.blinking_cursor_is_black
            self.blinking_cursor_timer = 1
        if self.blinking_cursor_is_black:
            pygame.draw.rect(screen, TYPED_TEXT_COLOR, (text.get_width()+310, 55, 20, self.font_size+10))
        if self.STATE == 'SELECTING_LETTER_GROUPS':
            for group in ['LEFT', 'RIGHT']:
                x = y = 0
                if self.groups[group] is not None:
                    for letter in self.groups[group]:
                        text = self.font.render(letter, 1, TEXT_COLOR)
                        screen.blit(text, (self.offsets[group][0]+x, self.offsets[group][1]+y))
                        x += self.font_size+5
                        if x > 90:
                            y += self.font_size+25
                            x = 0
                    if self._highlighted == group:
                        pygame.draw.rect(screen, HIGHLIGHTED_COLOR, (self.offsets[group][0]-10, self.offsets[group][1]-10, 2*(self.font_size+5)+10, 10))

                    pygame.draw.rect(screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, self.select_progress_bars[group]*(2*(self.font_size+5)+10), 10))
        elif self.STATE == 'SELECTING_INDIVIDUAL_LETTERS':
            letters, tree = get_data(self.tree_path)
            if tree.data_len() == 2:
                text = self.font.render(letters[0], 1, TEXT_COLOR)
                screen.blit(text, self.offsets['LEFT'])
                text = self.font.render(letters[1], 1, TEXT_COLOR)
                screen.blit(text, self.offsets['RIGHT'])
                for group in ['LEFT', 'RIGHT']:
                    pygame.draw.rect(screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, self.select_progress_bars[group]*(2*(self.font_size+5)+10), 10))
            elif tree.data_len() == 3:
                text = self.font.render(letters[0], 1, TEXT_COLOR)
                screen.blit(text, self.offsets['LEFT'])
                text = self.font.render(letters[1], 1, TEXT_COLOR)
                screen.blit(text, self.offsets['CENTER'])
                text = self.font.render(letters[2], 1, TEXT_COLOR)
                screen.blit(text, self.offsets['RIGHT'])
                for group in ['LEFT', 'RIGHT', 'CENTER']:
                    pygame.draw.rect(screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, int(self.select_progress_bars[group]*(2*(self.font_size+5)+10)), 10))
        # self.draw_eye_states(screen)


class KeyboardScene(object):
    def __init__(self, parent):
        self.screen = parent.screen
        self.keyboard = Keyboard()
        self.model = tf.keras.models.load_model('./saved_model')
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(FACE_LANDMARK_MODEL)
        self.clock = pygame.time.Clock()

        self.last_eye_states = [False]*30
        self.cap = cv2.VideoCapture(0)
        self.webcam_surface = pygame.Surface((640, 480))
        self.csv_file = open('recorded_data/data.csv', 'r')
        self.font = pygame.font.Font('./assets/OpenSansCondensed-Light.ttf', 25)
        self.done = False
        self.face_surface = None
        self.pause = False
        self.recording = False
        self.predicting = False
        self.counter = 0
        self.latest_positions = []
        self.latest_positions_raw = []
        self.online_training = False
        self.mouse_positions = []
        self.use_shape = True
        self.last_ears = []
        self.no_face_detected_icon = pygame.transform.scale(pygame.image.load('./assets/face.png'), (256, 256))
        say_out_loud_icon = pygame.transform.scale(pygame.image.load('./assets/voice.png'), (230, 230))
        self.say_out_loud_icon = pygame.Surface((say_out_loud_icon.get_width()+20, say_out_loud_icon.get_height()+20))
        self.say_out_loud_icon.fill(DARKER_THAN_BG_COLOR)
        self.say_out_loud_icon.blit(say_out_loud_icon, (10, 10))
        backspace_icon = pygame.transform.scale(pygame.image.load('./assets/backspace.png'), (230, 230))
        self.backspace_icon = pygame.Surface((backspace_icon.get_width()+20, backspace_icon.get_height()+20))
        self.backspace_icon.fill(DARKER_THAN_BG_COLOR)
        self.backspace_icon.blit(backspace_icon, (10, 10))
        self.keyboard = Keyboard()

    def update(self, *args, **kwargs):
        global DEBUG
        try:
            if self.done:
                self.csv_file.close()
                self.cap.release()
                cv2.destroyAllWindows()
                raise LoquorQuit
            self.face_surface = None
            eyes_are_closed = False
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.done = True
                    if event.key == pygame.K_z:
                        self.keyboard.typed_message = ""
                        self.keyboard.reset_to_top_keyboard_level()
                    elif event.key == pygame.K_SPACE:
                        self.pause = not self.pause
                    elif event.key == pygame.K_d:
                        DEBUG = not DEBUG
                    elif event.key == pygame.K_r:
                        self.recording = not self.recording
                    elif event.key == pygame.K_p:
                        self.predicting = not self.predicting
                    elif event.key == pygame.K_s:
                        self.use_shape = not self.use_shape
                    elif event.key == pygame.K_t:
                        self.online_training = not self.online_training
            if not self.pause:
                self.screen.fill(SCREEN_BG_COLOR)
                self.screen.blit(self.say_out_loud_icon, (1920-20-250, 30))
                self.screen.blit(self.backspace_icon, (20, 30))
                ret, img = self.cap.read()
                img = cv2.GaussianBlur(img, (5, 5), 0)
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                mouse_pos = pygame.mouse.get_pos()
                img[0, [0, 2]] = img[0, [2, 0]]
                img = img.swapaxes(0, 1)

                pygame.surfarray.blit_array(self.webcam_surface, img)

                rects = self.detector(gray, 0)
                corner_indexes = [36, 39]
                for (i, rect) in enumerate(rects):
                    shape = self.predictor(gray, rect)
                    shape = face_utils.shape_to_np(shape)
                    dist_x = shape[corner_indexes[1]][0] - shape[corner_indexes[0]][0]

                    self.face_surface = pygame.Surface((dist_x, 128))
                    self.face_surface.blit(self.webcam_surface, (0, 0), (shape[corner_indexes[0]][0], shape[corner_indexes[0]][1]-64, dist_x, 128))
                    self.face_surface=pygame.transform.scale(self.face_surface, (128, 128))
                    break
                if 'shape' in locals():
                    ear = eye_aspect_ratio(shape)
                    self.last_ears.append(ear)
                    if len(self.last_ears) > 20:
                        self.last_ears.pop(0)
                    if len([ear for ear in self.last_ears if ear < 0.16]) > 5 and not pygame.mixer.get_busy():
                        self.last_ears = []
                        eyes_are_closed = True
                    if DEBUG:
                        text = self.font.render(str(ear), 1, TEXT_COLOR)
                        self.screen.blit(text, (1920/2-text.get_width()//2, 1080-200))
                    self.last_eye_states.append(eyes_are_closed)
                    if len(self.last_eye_states) > 30:
                        self.last_eye_states.pop(0)

                if not self.predicting:
                    # self.screen.blit(self.webcam_surface, (1920/2-640/2, 1080/2-480/2))
                    pass

                if self.recording and len(rects) == 1: # one face is present
                    text = self.font.render("SAVING DATA", 1, TEXT_COLOR)
                    screen.blit(text, (1920/2-text.get_width()//2, 1080-100))
                    photo_id = str(counter).zfill(6)
                    pygame.image.save(self.face_surface, './recorded_data/' + photo_id + '.png')
                    self.csv_file.write(photo_id + ',')
                    self.csv_file.write(str(mouse_pos[0]) + ';' + str(mouse_pos[1]))
                    for index, (x, y) in enumerate(shape):
                        self.csv_file.write(','+str(x) + ';' + str(y))
                    self.csv_file.write('\n')
                    self.counter += 1

                if self.predicting:
                    if DEBUG:
                        text = self.font.render("PREDICTING", 1, TEXT_COLOR)
                        self.screen.blit(text, (1920/2-text.get_width()//2, 1080-100))
                    try:
                        input_image = pygame.surfarray.array3d(self.face_surface)
                    except AttributeError:
                        raise NoFaceDetected

                    if not self.use_shape:
                        shape = np.zeros_like(shape)
                    try:
                        prediction = self.model.predict(
                                {
                                    'image_input': input_image.reshape(-1, 128, 128, 3),
                                    'input_features': shape.flatten().reshape(-1, 68, 2)
                                })[0]
                    except ValueError: # No face detected
                        raise NoFaceDetected

                    if self.online_training:
                        if DEBUG:
                            text = self.font.render("ONLINE TRAINING", 1, TEXT_COLOR)
                            self.screen.blit(text, (1920/2-text.get_width()//2, 1080-100))
                        pressed = pygame.mouse.get_pressed()
                        for key in training_dots.keys():
                            pygame.draw.circle(self.screen, (255, 0, 255), training_dots[key], 5)
                        if any(pressed):
                            X = {
                                'image_input': input_image.reshape(-1, 128, 128, 3),
                                'input_features': shape.flatten().reshape(-1, 68, 2)
                            }
                            y = np.array([np.array([mouse_pos[0], mouse_pos[1]])])
                            self.model.fit(X, y)

                    prediction = self.model.predict(
                            [
                                input_image.reshape(-1, 128, 128, 3),
                                shape.flatten().reshape(-1, 68, 2)
                            ])[0]
                    self.latest_positions_raw.append(prediction)
                    if len(self.latest_positions_raw) > 30:
                        self.latest_positions_raw.pop(0)
                    prediction = simplify(prediction)
                    prediction = prediction_to_circle(prediction)
                    self.latest_positions.append(prediction)
                    if len(self.latest_positions) > 30:
                        self.latest_positions.pop(0)
                    pygame.draw.circle(self.screen, (255, 0, 0), prediction, 50)
                    screen_sector = get_screen_sector(self.latest_positions)
                    if DEBUG:
                        text = self.font.render("Screen sector: " + screen_sector, 1, TEXT_COLOR)
                        self.screen.blit(text, (1920/2-text.get_width()//2, 1080-50))

                if self.face_surface:
                    if DEBUG:
                        text = self.font.render("Use shape: " + str(self.use_shape), 1, TEXT_COLOR)
                        self.screen.blit(text, (1920/2-text.get_width()//2, 30))
                        text = self.font.render("Corner pixel distance: "+str(dist_x), 1, TEXT_COLOR)
                        self.screen.blit(text, (1920/2-text.get_width()//2, 10))
                    self.face_surface = pygame.transform.scale(self.face_surface, (256, 256))
                    if not self.predicting:
                        # self.screen.blit(self.face_surface, (0, 0))
                        pass

                if not self.predicting:
                    pygame.draw.circle(self.screen, (0, 255, 0), mouse_pos, 10)
                    if self.recording:
                        self.mouse_positions.append(mouse_pos)

                if self.recording:
                    for mouse_pos in self.mouse_positions:
                        pygame.gfxdraw.filled_circle(self.screen, mouse_pos[0], mouse_pos[1], 10, (0, 255, 0, 100))

                for index, position in enumerate(self.latest_positions_raw):
                    pygame.gfxdraw.filled_circle(self.screen, position[0], position[1], max(0,index-10), (0, 255, 0, 100))
                # if len(self.latest_positions) > 0:
                #     pygame.gfxdraw.filled_circle(self.screen, self.latest_positions_raw[-1][0], self.latest_positions_raw[-1][1], 20, (0, 255, 0, 100))

                self.keyboard.update(self.latest_positions, eyes_are_closed)
                self.keyboard.draw(self.screen)
                pygame.display.flip()
        except NoFaceDetected:
            self.screen.fill(SCREEN_BG_COLOR)
            self.screen.blit(self.no_face_detected_icon, (1920//2-256//2, 1080//2-256//2))
            text = self.font.render('CARA NO DETECTADA', 1, TEXT_COLOR)
            self.screen.blit(text, (1920//2-text.get_width()//2, 1080//2+256//2+20))
