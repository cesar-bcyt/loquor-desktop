DEBUG = True

import pygame
import subprocess
from exit_scene import ExitScene
from calibration_scene import CalibrationScene
from scene import Scene
from service import ListenerMixin
from services import camera_service, eye_gaze_service, pygame_events_service
from styles import BG_COLOR, HIGHLIGHTED_COLOR, DARKER_THAN_BG_COLOR
from tree import get_data

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

SCREEN_BG_COLOR = BG_COLOR
TEXTBOX_COLOR = DARKER_THAN_BG_COLOR
TEXT_COLOR = (255, 255, 255)
TYPED_TEXT_COLOR = (255, 255, 255)

# POINT_DRAW_POSITIONS = {
#     (-1,-1): (1920*1/10, 1080*1/10),
#     ( 0,-1): (1920*5/10, 1080*1/10),
#     ( 1,-1): (1920*9/10, 1080*1/10),
#
#     (-1, 0): (1920*1/10, 1080*5/10),
#     ( 0, 0): (1920*5/10, 1080*5/10),
#     ( 1, 0): (1920*9/10, 1080*5/10),
#
#     (-1, 1): (1920*1/10, 1080*9/10),
#     ( 0, 1): (1920*5/10, 1080*9/10),
#     ( 1, 1): (1920*9/10, 1080*9/10),
# }

POINT_DRAW_POSITIONS = {
    (-1,-1): (230, 250),
    ( 0,-1): (960, 160),
    ( 1,-1): (1690, 250),

    (-1, 0): (165, 630),
    ( 0, 0): (960, 540),
    ( 1, 0): (1785, 630),

    (-1, 1): (165, 950),
    ( 0, 1): (960, 880),
    ( 1, 1): (1785, 950),
}
POINT_DRAW_POSITIONS = {pos: (int(p[0]), int(p[1])) for pos, p in POINT_DRAW_POSITIONS.items()}

class KeyboardScene(Scene, ListenerMixin):
    STATES = ['SELECTING_LETTER_GROUPS', 'SELECTING_INDIVIDUAL_LETTERS']
    FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE = 15
    DICTIONARY = [word.replace('\n', '') for word in open('./diccionario.csv').readlines()]
    def __init__(self, screen):
        super().__init__(screen)
        self.selecting_symbols = False
        self.STATE = 'SELECTING_LETTER_GROUPS'

        self._hand_icons = {
            'hand': pygame.transform.scale(pygame.image.load('./assets/hand.png'), (200, 200)),
            'hand_down': pygame.transform.scale(pygame.image.load('./assets/hand_down.png'), (150, 150)),
            'hand_right': pygame.transform.scale(pygame.image.load('./assets/hand_right.png'), (200, 200)),
            'hand_left': pygame.transform.scale(pygame.image.load('./assets/hand_left.png'), (200, 200)),
            'hand_left_up': pygame.transform.scale(pygame.image.load('./assets/hand_left_up.png'), (200, 200)),
            'hand_right_up': pygame.transform.scale(pygame.image.load('./assets/hand_right_up.png'), (200, 200)),
            'hand_left_down': pygame.transform.scale(pygame.image.load('./assets/hand_left_down.png'), (150, 150)),
            'hand_right_down': pygame.transform.scale(pygame.image.load('./assets/hand_right_down.png'), (150, 150)),
        }

        self.hand_icons = {
            (-1,-1): self._hand_icons['hand_left_up'],
            ( 0,-1): self._hand_icons['hand'],
            ( 1,-1): self._hand_icons['hand_right_up'],

            (-1, 0): self._hand_icons['hand_left_up'],
            ( 0, 0): self._hand_icons['hand'],
            ( 1, 0): self._hand_icons['hand_right_up'],

            (-1, 1): self._hand_icons['hand_left_down'],
            ( 0, 1): self._hand_icons['hand_down'],
            ( 1, 1): self._hand_icons['hand_right_down'],
        }

        self._delete_word_icon = pygame.transform.scale(
                pygame.image.load('./assets/delete_word_icon.png'), (100, 100))

        self._hamburger_menu_icon = pygame.transform.scale(
                pygame.image.load('./assets/hamburger_menu.png'), (100, 100))

        self._backspace_icon = pygame.transform.scale(
                pygame.image.load('./assets/backspace.png'), (230, 230))

        self._say_out_loud_icon = pygame.transform.scale(
                pygame.image.load('./assets/voice.png'), (230, 230))

        self.symbols_group = ['[ESPACIO]', ',', '.']
        self._symbols_group = ['_', ',', '.']
        self.say_phrase_cooldown = 0
        self.last_eye_states = [False]*30
        self.current_area = (0, 0)
        pygame_events_service.register_listener(self)
        eye_gaze_service.register_listener(self)
        self.tree_path = ''
        self.current_area = (-1, -1)

        self.closest_word = ""
        self.typed_message = ""

        self.font_size = 50
        self.font = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', self.font_size)
        # self.font = pygame.font.Font('./assets/LiberationSans-Regular.ttf', self.font_size)

        self.big_font_size = 70
        self.big_font = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', self.big_font_size)
        # self.big_font = pygame.font.Font('./assets/LiberationSans-Regular.ttf', self.big_font_size)

        self.offsets = {
            'CENTER LEFT': (30, 1080//3),
            'CENTER RIGHT': (1920-120, 1080//3),
            'CENTER CENTER': (1920//2, 1080//3),
            'BOTTOM CENTER': (1920//2, 1080-150),
            'BOTTOM LEFT': (30, 1080-150),
            'BOTTOM RIGHT': (1920-130, 1080-130),
        }

        self.reset_to_top_keyboard_level()

        self.blinking_cursor_timer = 1
        self.blinking_cursor_is_black = False

    def reset_typed_message(self):
        self.reset_to_top_keyboard_level()
        self.typed_message = ""

    def reset_to_top_keyboard_level(self):
        self.tree_path = ''
        self.selecting_symbols = False
        self._last_highlighted = []
        alphabet_tree_root_data, _ = get_data('/')
        self.groups = {
            'CENTER LEFT': alphabet_tree_root_data[0],
            'CENTER CENTER': None,
            'CENTER RIGHT': alphabet_tree_root_data[1],
            'PREV': ['M1', 'M2'],
            'BOTTOM CENTER': '',
        }
        self.select_progress_bars = {
            'TOP RIGHT': 0,
            'TOP LEFT': 0,
            'CENTER LEFT': 0,
            'CENTER CENTER': 0,
            'CENTER RIGHT': 0,
            'BOTTOM CENTER': 0,
            'BOTTOM LEFT': 0,
            'BOTTOM RIGHT': 0,
        }
        self.STATE = 'SELECTING_LETTER_GROUPS'
        self._highlighted = None

    def highlight_or_select(self, group):
        assert group in ['CENTER LEFT', 'CENTER RIGHT', 'CENTER CENTER', 'TOP LEFT', 'TOP RIGHT', 'BOTTOM CENTER', 'BOTTOM LEFT', 'BOTTOM RIGHT', None]
        self._highlighted = group
        self._last_highlighted.append(group)

        gazed_at = {
            'TOP LEFT': self._last_highlighted.count('TOP LEFT'),
            'TOP RIGHT': self._last_highlighted.count('TOP RIGHT'),
            'CENTER LEFT': self._last_highlighted.count('CENTER LEFT'),
            'CENTER CENTER': self._last_highlighted.count('CENTER CENTER'),
            'CENTER RIGHT': self._last_highlighted.count('CENTER RIGHT'),
            'BOTTOM CENTER': self._last_highlighted.count('BOTTOM CENTER'),
            'BOTTOM LEFT': self._last_highlighted.count('BOTTOM LEFT'),
            'BOTTOM RIGHT': self._last_highlighted.count('BOTTOM RIGHT'),
        }

        for g in ['TOP LEFT', 'CENTER LEFT', 'CENTER RIGHT', 'CENTER CENTER', 'BOTTOM CENTER', 'TOP RIGHT', 'BOTTOM LEFT', 'BOTTOM RIGHT']:
            if g == group:
                self.select_progress_bars[g] = (self.select_progress_bars[g] + gazed_at[g]) / KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE
            else:
                self.select_progress_bars[g] = max(0, self.select_progress_bars[g] - 1 / KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE)

        if len(self._last_highlighted) > 60:
            self._last_highlighted.pop(0)
        if group == 'PREV':
            self._last_highlighted = []
            self._select('PREV')
        elif self._last_highlighted.count(None) > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._last_highlighted = []
        elif gazed_at['TOP LEFT'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('TOP LEFT')
        elif gazed_at['TOP RIGHT'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('TOP RIGHT')
        elif gazed_at['CENTER LEFT'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('CENTER LEFT')
        elif gazed_at['CENTER RIGHT'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('CENTER RIGHT')
        elif gazed_at['CENTER CENTER'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('CENTER CENTER')
        elif gazed_at['BOTTOM CENTER'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('BOTTOM CENTER')
        elif gazed_at['BOTTOM LEFT'] > 2*KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('BOTTOM LEFT')
        elif gazed_at['BOTTOM RIGHT'] > KeyboardScene.FRAMES_NEEDED_TO_SELECT_THROUGH_GAZE:
            self._select('BOTTOM RIGHT')

    def add_space(self):
        self.typed_message += ' '

    def say_phrase(self):
        subprocess.Popen(['/usr/bin/espeak', '-v', 'es-la', '-s', '120', '"'+self.typed_message+'"'])

    def update(self):
        eyes_are_closed = False
        self.say_phrase_cooldown = max(0, self.say_phrase_cooldown-1)
        sector = SCREEN_SECTORS[self.current_area]
        self.last_eye_states.append(eyes_are_closed)
        if len(self.last_eye_states) > 30:
            self.last_eye_states.pop(0)
        if self.STATE == 'SELECTING_LETTER_GROUPS':
            if eyes_are_closed:
                if len(self.typed_message) > 0 and self.typed_message[-1] != ' ':
                    self.add_space()
                elif self.say_phrase_cooldown <= 0:
                    self.say_phrase()
                    self.say_phrase_cooldown = 30
                # self.highlight_or_select('PREV')
                # self._select('PREV')
            elif sector in ['TOP LEFT', 'TOP RIGHT', 'CENTER LEFT', 'CENTER RIGHT', 'BOTTOM CENTER', 'BOTTOM LEFT', 'BOTTOM RIGHT']:
                self.highlight_or_select(sector)
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
            elif 'CENTER LEFT' in sector:
                self.highlight_or_select('CENTER LEFT')
            elif 'CENTER RIGHT' in sector:
                self.highlight_or_select('CENTER RIGHT')
            elif 'CENTER CENTER' in sector:
                self.highlight_or_select('CENTER CENTER')
            elif 'BOTTOM LEFT' in sector:
                self.highlight_or_select('BOTTOM LEFT')
            elif self.selecting_symbols and 'BOTTOM RIGHT' in sector:
                self.highlight_or_select('BOTTOM RIGHT')

    def __remove_last_letter(self):
        if len(self.typed_message) > 0:
            self.typed_message = self.typed_message[:-1]

    def __add_letter_to_typed_message(self, letter):
        if letter == '_':
            self.typed_message += ' '
        elif letter == '⬅️':
            self.typed_message = self.typed_message[:-1] if len(self.typed_message) > 0 else self.typed_message
        else:
            self.typed_message += letter[0]

    def draw_closest_word(self):
        if len(self.typed_message) > 0:
            self.closest_word = self.get_closest_word()
            text = self.big_font.render(self.closest_word, 1, TEXT_COLOR)
            w, h = text.get_size()
            self.offsets['BOTTOM CENTER'] = ((1920-w)//2, 1080-150)
            self.screen.blit(text, self.offsets['BOTTOM CENTER'])

    def get_closest_word(self, typed_message=None):
        typed_message = self.typed_message.split(' ')[-1]
        best_matching_letters = ('', 0)
        for word in KeyboardScene.DICTIONARY:
            current_matching_letters = 0
            for i in range(len(typed_message)):
                if len(word) > i and word[i].lower() == typed_message[i].lower():
                        current_matching_letters += 1
            if current_matching_letters > best_matching_letters[1]:
                best_matching_letters = (word, current_matching_letters)
        self.groups['BOTTOM CENTER'] = best_matching_letters[0].upper()
        return best_matching_letters[0].upper()

    def draw_menu_rects(self):
        text = self.big_font.render('BORRAR', 1, TEXT_COLOR)
        w, h = text.get_size()
        self.screen.blit(text, ((1920-w)//2, 1080-150))
        pygame.draw.rect(self.screen, (255, 0, 0),  ((1920-w)//2 - 10, 1080-150 - 10, w+10, h+10), 5)

        text = self.big_font.render('VOLVER', 1, TEXT_COLOR)
        w, h = text.get_size()
        self.screen.blit(text, ((1920-w)//2, 10))
        pygame.draw.rect(self.screen, (255, 0, 0), ((1920-w)//2 - 10, 10, w+10, h+10), 5)


    def _select(self, group):
        if self.STATE == 'SELECTING_INDIVIDUAL_LETTERS':

            if not self.selecting_symbols:
                letter, tree = get_data(self.tree_path)
            else:
                _letter, tree = self.symbols_group, None
                letter = []
                for l in _letter:
                    if l != '[ESPACIO]':
                        letter.append(l)
                    else:
                        letter.append(' ')

            if group == 'PREV' and tree is not None:
                self.tree_path = '/'.join(self.tree_path.split('/')[:-1])
            elif group == 'TOP LEFT':
                self.__remove_last_letter()
            elif group == 'TOP RIGHT':
                self.say_phrase()
            elif group == 'CENTER LEFT':
                self.__add_letter_to_typed_message(letter[0])
            elif group == 'CENTER RIGHT':
                if tree is not None and tree.data_len() == 2:
                    self.__add_letter_to_typed_message(letter[1])
                elif tree is not None and tree.data_len() == 3:
                    self.__add_letter_to_typed_message(letter[2])
                elif tree is None and len(letter) == 3:
                    self.__add_letter_to_typed_message(letter[2])
            elif group == 'CENTER CENTER':
                self.__add_letter_to_typed_message(letter[1])
            elif group == 'BOTTOM CENTER':
                self.select_closest_word()
            elif group == 'BOTTOM LEFT':
                if self.tree_path == '':
                    self.reset_typed_message()
                else:
                    self.reset_to_top_keyboard_level()
            elif group == 'BOTTOM RIGHT':
                # self.show_symbols_at_the_center()
                pass
            self.reset_to_top_keyboard_level()
        elif self.STATE == 'SELECTING_LETTER_GROUPS':
            if group == 'PREV':
                self.tree_path = '/'.join(self.tree_path.split('/')[:-1])
            elif group == 'CENTER LEFT':
                self.tree_path += '/left'
            elif group == 'TOP LEFT':
                self.__remove_last_letter()
            elif group == 'TOP RIGHT':
                self.say_phrase()
            elif group == 'CENTER RIGHT':
                self.tree_path += '/right'
            elif group == 'CENTER CENTER':
                self.typed_message += letter[1]
            elif group == 'BOTTOM CENTER':
                self.select_closest_word()
            elif group == 'BOTTOM LEFT':
                if self.tree_path == '':
                    self.reset_typed_message()
                else:
                    self.reset_to_top_keyboard_level()
            elif group == 'BOTTOM RIGHT':
                self.show_symbols_at_the_center()
            if not self.selecting_symbols:
                data, node = get_data(self.tree_path)
            else:
                data = self.symbols_group
                node = None
            if type(data[0]) is str and type(data[1]) is str:
                self.STATE = 'SELECTING_INDIVIDUAL_LETTERS'
            if node is None or len([x for x in node.data if x is not None]) == 3:
                self.groups = {
                    'CENTER LEFT': data[0],
                    'CENTER CENTER': data[1],
                    'CENTER RIGHT': data[2],
                    'BOTTOM CENTER': self.closest_word,
                }
            else:
                self.groups = {
                    'CENTER LEFT': data[0],
                    'CENTER CENTER': None,
                    'CENTER RIGHT': data[1],
                    'BOTTOM CENTER': self.closest_word,
                }
            self._last_highlighted = []
            self.closest_word = None # signals recalc of closest word on next draw()

    def select_closest_word(self):
        if len(self.typed_message) > 1:
            self.typed_message = ' '.join(self.typed_message.split(' ')[:-1]) + ' ' + self.closest_word + ' '
        elif self.closest_word is not None and len(self.closest_word) > 0:
            self.typed_message = self.closest_word + ' '

    @property
    def selector_icon(self):
        if self.current_area == (0, 1) and self.closest_word is not None and len(self.closest_word) > 0:
            surface = self.hand_icons[self.current_area]
        elif self.current_area not in [(0, 1), (0, 0), (0, -1), (-1, 1)]:
            surface = self.hand_icons[self.current_area]
        elif self.current_area == (-1, 1) and self.tree_path == '':
            surface = self.hand_icons[self.current_area]
        else:
            surface = pygame.Surface((200, 200), pygame.SRCALPHA, 32)
            surface.fill((255, 255, 255, 0))
            pygame.draw.circle(surface, (255, 255, 255), (100, 100), 100, 5)
        return surface

    def draw_gaze_position(self):
        self.screen.blit(self.selector_icon, (POINT_DRAW_POSITIONS[self.current_area][0]-100, POINT_DRAW_POSITIONS[self.current_area][1]-100))
        # pygame.draw.circle(
        #         self.screen,
        #         (255, 0, 0),
        #         POINT_DRAW_POSITIONS[self.current_area],
        #         30)

    @property
    def say_out_loud_icon(self):
        surface = pygame.Surface((250, 250), pygame.SRCALPHA, 32)
        surface.fill(DARKER_THAN_BG_COLOR)
        lighter_surface = pygame.Surface((300, 250))
        lighter_surface.fill(HIGHLIGHTED_COLOR)
        surface.blit(lighter_surface, (-300+250*self.select_progress_bars['TOP RIGHT'], 0))
        surface.blit(self._say_out_loud_icon, (0, 0))
        return surface

    @property
    def delete_word_icon(self):
        surface = pygame.Surface((100, 100), pygame.SRCALPHA, 32)
        surface.fill(DARKER_THAN_BG_COLOR)
        lighter_surface = pygame.Surface((300, 100))
        lighter_surface.fill(HIGHLIGHTED_COLOR)
        surface.blit(lighter_surface, (-300+100*self.select_progress_bars['BOTTOM LEFT']//2, 0))
        surface.blit(self._delete_word_icon, (0, 0))
        return surface

    @property
    def hamburger_menu_icon(self):
        surface = pygame.Surface((100, 100), pygame.SRCALPHA, 32)
        surface.fill(DARKER_THAN_BG_COLOR)
        lighter_surface = pygame.Surface((300, 100))
        lighter_surface.fill(HIGHLIGHTED_COLOR)
        surface.blit(lighter_surface, (-300+100*self.select_progress_bars['BOTTOM RIGHT'], 0))
        surface.blit(self._hamburger_menu_icon, (0, 0))
        return surface

    @property
    def backspace_icon(self):
        surface = pygame.Surface((250, 250), pygame.SRCALPHA, 32)
        surface.fill(DARKER_THAN_BG_COLOR)
        lighter_surface = pygame.Surface((900, 250))
        lighter_surface.fill(HIGHLIGHTED_COLOR)
        surface.blit(lighter_surface, (-900+250*self.select_progress_bars['TOP LEFT'], 0))
        surface.blit(self._backspace_icon, (0, 0))
        return surface

    def show_symbols_at_the_center(self):
        self.STATE = 'SELECTING_INDIVIDUAL_LETTERS'
        self.selecting_symbols = True

    def draw_big_background_rectangle(self):
        pygame.draw.rect(self.screen, TEXTBOX_COLOR, (290, 30, 1340, 250))

    def draw_symbols_group(self):
        text = self.font.render(" ".join(self._symbols_group), 1, TEXT_COLOR)
        pygame.draw.rect(self.screen, (0, 255, 0), (1920-130, 1080-130, self.select_progress_bars['BOTTOM RIGHT']*(2*(self.font_size+5)+10), 10))
        self.screen.blit(text, (1920-130, 1080-130))

    def draw_typed_message_anb_blinking_cursor(self):
        n = 40
        chunks = [self.typed_message[i:i+n] for i in range(0, len(self.typed_message), n)]
        for row_number, chunk in enumerate(chunks):
            if chunk[0] == ' ':
                chunk = chunk[1:]
            text = self.big_font.render(chunk, 1, TYPED_TEXT_COLOR)
            self.screen.blit(text, (305, 35+row_number*60))
        width = text.get_width() if 'text' in locals() else 0
        row_number = row_number if 'row_number' in locals() else 0
        self.blinking_cursor_timer += 1
        if self.blinking_cursor_timer % 3 == 0:
            self.blinking_cursor_is_black = not self.blinking_cursor_is_black
            self.blinking_cursor_timer = 1
        if self.blinking_cursor_is_black:
            pygame.draw.rect(self.screen, TYPED_TEXT_COLOR, (width+310, 55+row_number*60, 20, self.font_size+10))

    def draw_letter_groups_with_progress_bars(self):
        # for group in ['BOTTOM LEFT', 'BOTTOM RIGHT']:
        #     pygame.draw.rect(self.screen, HIGHLIGHTED_COLOR, (self.offsets[group][0]-10, self.offsets[group][1]-10, 2*(self.font_size+5)+10, 10))
        #     pygame.draw.rect(self.screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, self.select_progress_bars[group]*(2*(self.font_size+5)+10), 10))
        for group in ['CENTER LEFT', 'CENTER RIGHT', 'BOTTOM CENTER']:
            x = y = 0
            if self.groups[group] is not None:
                if group in ['CENTER LEFT', 'CENTER RIGHT']:
                    for letter in self.groups[group]:
                        text = self.font.render(letter, 1, TEXT_COLOR)
                        self.screen.blit(text, (self.offsets[group][0]+x, self.offsets[group][1]+y))
                        x += self.font_size+5
                        if x > 90:
                            y += self.font_size+25
                            x = 0
                if group in ['CENTER LEFT', 'CENTER RIGHT']:
                    pygame.draw.rect(self.screen, HIGHLIGHTED_COLOR, (self.offsets[group][0]-10, self.offsets[group][1]-10, 2*(self.font_size+5)+10, 10))
                    pygame.draw.rect(self.screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, self.select_progress_bars[group]*(2*(self.font_size+5)+10), 10))
                elif group == 'BOTTOM CENTER' and self.closest_word is not None and len(self.closest_word) > 0:
                    l = self.font_size*(max(1, len(self.closest_word)-1))
                    pygame.draw.rect(self.screen, HIGHLIGHTED_COLOR, (self.offsets[group][0], self.offsets[group][1]-10, l, 10))
                    pygame.draw.rect(self.screen, (0, 255, 0), (self.offsets[group][0], self.offsets[group][1]-10, self.select_progress_bars[group]*l, 10))

    def draw_individual_letters(self):
        if not self.selecting_symbols:
            letters, tree = get_data(self.tree_path)
        else:
            letters = self.symbols_group
            tree = None
        if tree and tree.data_len() == 2:
            text = self.font.render(letters[0], 1, TEXT_COLOR)
            self.screen.blit(text, self.offsets['CENTER LEFT'])
            text = self.font.render(letters[1], 1, TEXT_COLOR)
            self.screen.blit(text, self.offsets['CENTER RIGHT'])
            for group in ['CENTER LEFT', 'CENTER RIGHT']:
                pygame.draw.rect(self.screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, self.select_progress_bars[group]*(2*(self.font_size+5)+10), 10))
        elif tree is None or tree.data_len() == 3:
            text = self.font.render(letters[0], 1, TEXT_COLOR)
            self.screen.blit(text, self.offsets['CENTER LEFT'])
            text = self.font.render(letters[1], 1, TEXT_COLOR)
            self.screen.blit(text, self.offsets['CENTER CENTER'])
            text = self.font.render(letters[2], 1, TEXT_COLOR)
            self.screen.blit(text, self.offsets['CENTER RIGHT'])
            for group in ['CENTER LEFT', 'CENTER RIGHT', 'CENTER CENTER']:
                pygame.draw.rect(self.screen, (0, 255, 0), (self.offsets[group][0]-10, self.offsets[group][1]-10, int(self.select_progress_bars[group]*(2*(self.font_size+5)+10)), 10))

    def draw_icons(self):
        self.screen.blit(self.say_out_loud_icon, (1920-20-250, 30))
        self.screen.blit(self.backspace_icon, (20, 30))
        # self.screen.blit(self.hamburger_menu_icon, (1920-130, 1080-130))
        if self.tree_path == '' and not self.selecting_symbols:
            self.screen.blit(self.delete_word_icon, (30, 1080-130))

    def draw_return_to_keyboard_from_symbols_select_screen(self, position='right'):
        text = self.font.render('VOLVER', 1, TEXT_COLOR)
        if position == 'right':
            pygame.draw.rect(self.screen, (0, 255, 0), (1920-180, 1080-130, self.select_progress_bars['BOTTOM RIGHT']*(2*(self.font_size+5)+10), 10))
            self.screen.blit(text, (1920-180, 1080-130))
        elif position == 'left':
            pygame.draw.rect(self.screen, (0, 255, 0), (30, 1080-130, text.get_width()*self.select_progress_bars['BOTTOM LEFT']//2, 10))
            self.screen.blit(text, (30, 1080-130))

    def draw(self):
        self.screen.fill(SCREEN_BG_COLOR)
        self.draw_icons()
        self.draw_big_background_rectangle()
        self.draw_typed_message_anb_blinking_cursor()

        if not self.selecting_symbols:
            self.draw_symbols_group()
        else:
            self.draw_return_to_keyboard_from_symbols_select_screen()

        if self.tree_path != '':
            self.draw_return_to_keyboard_from_symbols_select_screen(position='left')

        self.draw_closest_word()

        if self.STATE == 'SELECTING_LETTER_GROUPS':
            self.draw_letter_groups_with_progress_bars()
        elif self.STATE == 'SELECTING_INDIVIDUAL_LETTERS':
            self.draw_individual_letters()

        self.draw_gaze_position()

    def process_received_message(self, message):
        if message['type'] == 'PYGAME_EVENT':
            for event in message['payload']:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.next_scene = ExitScene()
                    elif event.key == pygame.K_w:
                        self.next_scene = CalibrationScene()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    print(event)

        elif message['type'] == 'EYE_GAZE':
            self.current_area = message['payload']['current_area']

    def get_next_scene(self):
        return self.next_scene
