import pygame
from selector_scene_mixin import SelectorSceneMixin
from menu_item import MenuItem
from scene import Scene
from exit_scene import ExitScene
from services import pygame_events_service, eye_gaze_service
from styles import BG_COLOR, TEXT_COLOR, HIGHLIGHTED_COLOR
import json

positions = {
    'TOP LEFT': (30, 50),
    'TOP CENTER': (1920//2-250//2, 30),
    'TOP RIGHT': (1920-280, 50),

    'CENTER LEFT': (30, 1080//2-120),
    'CENTER CENTER': (1920//2-250//2, 1080//2-120),
    'CENTER RIGHT': (1920-280, 1080//2-120),

    'BOTTOM LEFT': (30, 1080-150),
    'BOTTOM CENTER': (1920//2-250//2, 1080-285),
    'BOTTOM RIGHT': (1920-130, 1080-150),
}

hand_positions = {
    'TOP LEFT': (30, 50),
    'TOP CENTER': (1920//2-250//2+50, 130),
    'TOP RIGHT': (1920-280, 50),

    'CENTER LEFT': (30+150, 1080//2-80),
    'CENTER CENTER': (1920//2-250//2+17, 1080//2-120),
    'CENTER RIGHT': (1920-390, 1080//2-80),

    'BOTTOM LEFT': (30, 1080-280),
    'BOTTOM CENTER': (1920//2-250//2+35, 1080-310),
    'BOTTOM RIGHT': (1920-280, 1080-280),
}

areas = {
    (-1, -1): 'TOP LEFT',
    (0, -1):  'TOP CENTER',
    (1, -1):  'TOP RIGHT',

    (-1, 0): 'CENTER LEFT',
    (0, 0):  'CENTER CENTER',
    (1, 0):  'CENTER RIGHT',

    (-1, 1): 'BOTTOM LEFT',
    (0, 1):  'BOTTOM CENTER',
    (1, 1):  'BOTTOM RIGHT',
}

settings = json.load(open('./config.json', 'r'))
default_settings = json.load(open('./default_config.json', 'r'))

settings_names = {
    'positioning_samples': [
        "Muestras para mover mirada",
        "Menos muestras significa movimientos más rápidos, pero menos precisos",
    ],
    'frames_threshold_needed_for_click': [
        "Muestras para click",
        "Menos muestras significa clicks más rápidos, pero aumenta la probabilidad de clickear sin querer",
    ]
}

class SettingsScene(Scene, SelectorSceneMixin):
    def __init__(self, screen):
        super().__init__(screen)
        eye_gaze_service.register_listener(self)
        pygame_events_service.register_listener(self)
        self.font = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', 50)
        self.font_small = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', 30)
        self.font_height = self.font.render('prueba', True, TEXT_COLOR).get_height()
        self.small_font_height = self.font_small.render('prueba', True, TEXT_COLOR).get_height()
        self.left_arrow = pygame.transform.scale(pygame.image.load('./assets/left_arrow.png'), (self.font_height, self.font_height))
        self.right_arrow = pygame.transform.scale(pygame.image.load('./assets/right_arrow.png'), (self.font_height, self.font_height))
        self.current_area = 'CENTER CENTER'
        self.progress_bars = {}
        self.left_arrow_highlighted = pygame.Surface((self.font_height, self.font_height))
        self.left_arrow_highlighted.fill(HIGHLIGHTED_COLOR)
        self.left_arrow_highlighted.blit(self.left_arrow, (0, 0))
        self.right_arrow_highlighted = pygame.Surface((self.font_height, self.font_height))
        self.right_arrow_highlighted.fill(HIGHLIGHTED_COLOR)
        self.right_arrow_highlighted.blit(self.right_arrow, (0, 0))
        self.mouse_position = (0, 0)
        self.clicked = False
        self.message = None
        self.message_timer = 0
        self.state = 'ASKING'
        self.states = ['ASKING', 'RUNNING', 'EXITING']
        _yes_button = MenuItem('./assets/yes.png', self, on_select=self.change_state('RUNNING'), text='Sí', icon_selected='./assets/yes_selected.png', extra=(0, 30))
        _no_button = MenuItem('./assets/no.png', self, on_select=self.exit, text='No', icon_selected='./assets/no_selected.png', extra=(0, 30))
        menu_items = {
            'TOP LEFT': None,
            'TOP CENTER': None,
            'TOP RIGHT': None,
            'CENTER LEFT': _no_button,
            'CENTER CENTER': None,
            'CENTER RIGHT': _yes_button,
            'BOTTOM LEFT': None,
            'BOTTOM CENTER': None,
            'BOTTOM RIGHT': None,
        }
        self.setup_selector_mixin(menu_items)

    def change_state(self, state):
        assert state in self.states
        def f():
            self.state = state
        return f

    def exit(self):
        self.state = 'EXITING'

    def draw_gaze_position(self):
        self.screen.blit(self.selector_icon, (hand_positions[self.current_area][0], hand_positions[self.current_area][1]))

    def draw_title(self):
        text1 = self.font.render('Configuración', True, TEXT_COLOR)
        self.screen.blit(text1, (15, 0))

    def hover(self, rect, offset):
        x, y = self.mouse_position
        x -= offset[0]
        y -= offset[1]
        return  (rect[0] <= x <= rect[0] + rect[2]) and (rect[1] <= y <= rect[1] + rect[3])

    def draw_slider(self, value, offset=(0, 0)):
        size = self.font_height+self.small_font_height
        text = self.font.render(str(value), True, TEXT_COLOR)
        surface = pygame.Surface((3*size, size))
        surface.fill(BG_COLOR)
        left_arrow = self.left_arrow
        right_arrow = self.right_arrow
        selected = None
        if self.hover([0, self.left_arrow.get_height()//3, size, size], offset):
            left_arrow = self.left_arrow_highlighted
            if self.clicked:
                selected = 'left'
                self.clicked = False
        if self.hover([3*size - self.right_arrow.get_width(), self.left_arrow.get_height()//3, size, size], offset):
            right_arrow = self.right_arrow_highlighted
            if self.clicked:
                selected = 'right'
                self.clicked = False
        surface.blit(left_arrow, (0, self.left_arrow.get_height()//3))
        surface.blit(right_arrow, (3*size-self.right_arrow.get_width(), self.right_arrow.get_height()//3))
        surface.blit(text, ((size*3-text.get_width())//2, self.left_arrow.get_height()//3))
        return surface, selected

    def draw_mouse_position(self):
        pygame.draw.circle(self.screen, (0, 255, 0), self.mouse_position, 40)

    def update_setting(self, key, selected):
        change = 0
        if selected == 'right':
            change = 1
        elif selected == 'left':
            change = -1
        settings[key] += change
        if settings[key] < 1:
            settings[key] = 1

    def draw_settings(self):
        global settings
        y = self.font_height
        for key, lines in settings_names.items():
            slider, selected = self.draw_slider(settings[key], (1920-500, y))
            self.screen.blit(slider, (1920-500, y))
            text1 = self.font.render(lines[0], True, TEXT_COLOR)
            text2 = self.font_small.render(lines[1], True, TEXT_COLOR)
            self.screen.blit(text1, (15, y))
            y += text1.get_height()+10
            self.screen.blit(text2, (15, y))
            y += text2.get_height()+10
            if selected:
                self.update_setting(key, selected)
        guardar, clicked = self.button('GUARDAR', (15, y))
        self.screen.blit(guardar, (15, y))
        if clicked:
            json.dump(settings, open('./config.json', 'w'))
            self.set_message('¡Configuración guardada!')
            self.clicked = False
        reset, clicked = self.button('RESET', (guardar.get_width()+30, y))
        self.screen.blit(reset, (guardar.get_width()+30, y))
        if clicked:
            settings = default_settings.copy()
            json.dump(settings, open('./config.json', 'w'))
            self.set_message('Configuración predeterminada reaplicada')
            self.clicked = False

    def set_message(self, message):
        self.message = message
        self.message_timer = 10

    def update(self):
        if self.message_timer <= 0:
            self.message_timer = 0
            self.message = None

    def draw_message(self):
        if self.message and self.message_timer > 0:
            message = self.font.render(self.message, True, TEXT_COLOR)
            self.screen.blit(message, ((1920-message.get_width())//2, (1080-200)))
            self.message_timer -= 1

    def button(self, text, offset=(0, 0)):
        text = self.font.render(text, True, TEXT_COLOR)
        surface = pygame.Surface((text.get_width()+20, text.get_height()+20))
        clicked = False
        if self.hover((0, 0, surface.get_width(), surface.get_height()), offset):
            surface.fill(HIGHLIGHTED_COLOR)
            if self.clicked:
                clicked = True
        else:
            surface.fill(BG_COLOR)
        pygame.draw.rect(surface, TEXT_COLOR, (0, 0, surface.get_width(), 5))
        pygame.draw.rect(surface, TEXT_COLOR, (0, surface.get_height()-5, surface.get_width(), 5))
        pygame.draw.rect(surface, TEXT_COLOR, (0, 0, 5, surface.get_height()))
        pygame.draw.rect(surface, TEXT_COLOR, (surface.get_width()-5, 0, 5, surface.get_height()))
        surface.blit(text, (10, 10))
        return surface, clicked

    def draw_warning(self):
        y = 100
        lines = [
            'ADVERTENCIA',
            'LÓQUOR no es configurable',
            'sólo usando la mirada',
            '¿deseas continuar?',
        ]
        y = 20
        for line in lines:
            l = self.font.render(line, True, TEXT_COLOR)
            self.screen.blit(l, ((1920 - l.get_width())//2, y))
            y += l.get_height()

    def draw(self):
        self.screen.fill(BG_COLOR)
        if self.state == 'ASKING':
            self.draw_warning()
            self.draw_menu_items()
            self.draw_gaze_position()
            self.draw_progress_bars()
        elif self.state == 'RUNNING':
            self.draw_title()
            self.draw_settings()
            self.draw_message()
        elif self.state == 'EXITING':
            self.next_scene = ExitScene()

    def process_received_message(self, message):
        self.process_received_message_for_menu_items(message)
        if message['type'] == 'PYGAME_EVENT':
            for event in message['payload']:
                if event.type == pygame.MOUSEBUTTONUP:
                    self.clicked = True
        elif message['type'] == 'PYGAME_MOUSE_POS':
            self.mouse_position = message['payload']
