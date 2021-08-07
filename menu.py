import pygame
from settings import SettingsScene
from calibration_scene import CalibrationScene
from exit_scene import ExitScene
from keyboard import KeyboardScene
from scene import Scene
from service import ListenerMixin
from services import eye_gaze_service, pygame_events_service
from styles import BG_COLOR, HIGHLIGHTED_COLOR, TEXT_COLOR
from yes_no_scene import YesNoScene

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


class MenuItem():
    def __init__(self, icon, parent, on_select=lambda: None, text=None):
        surface = pygame.Surface((250, 260), pygame.SRCALPHA, 32)
        icon = pygame.transform.scale(pygame.image.load(icon), (230, 230))
        surface.blit(icon, (0, 0))
        if text:
            text = parent.font.render(text, 1, TEXT_COLOR)
            surface.blit(text, ((250-text.get_width())//2-10, 230))
        self.icon = surface
        self.on_select = on_select

    def select(self):
        self.on_select()

class MenuScene(Scene, ListenerMixin):
    def __init__(self, screen):
        super().__init__(screen)
        self.current_area = 'CENTER CENTER'
        eye_gaze_service.register_listener(self)
        pygame_events_service.register_listener(self)
        self.font_size = 25
        self.font = pygame.font.SysFont('Arial', self.font_size)
        self.logo_font = pygame.font.Font('./assets/OpenSansCondensed-Bold.ttf', 60)
        self.progress_bars = {}
        keyboard_button = MenuItem('./assets/keyboard.png', self, self.set_scene(KeyboardScene), 'Comunicador')
        calibration_button = MenuItem('./assets/calibration.png', self, self.set_scene(CalibrationScene), 'Calibración')
        yes_no_button = MenuItem('./assets/yes_no.png', self, self.set_scene(YesNoScene), 'Comunicador Sí/No')
        settings_button = MenuItem('./assets/settings.png', self, self.set_scene(SettingsScene), 'Ajustes')

        self.menu_items = {
            'TOP LEFT': None,
            'TOP CENTER': calibration_button,
            'TOP RIGHT': None,
            'CENTER LEFT': keyboard_button,
            'CENTER CENTER': None,
            'CENTER RIGHT': yes_no_button,
            'BOTTOM LEFT': None,
            'BOTTOM CENTER': settings_button,
            'BOTTOM RIGHT': None,
        }
        self.used_areas = [x for x in self.menu_items.keys() if self.menu_items[x] is not None]

        self._hand_icons = {
            'hand': pygame.transform.scale(pygame.image.load('./assets/hand.png'), (150, 150)),
            'hand_down': pygame.transform.scale(pygame.image.load('./assets/hand_down.png'), (150, 150)),
            'hand_right': pygame.transform.scale(pygame.image.load('./assets/hand_right.png'), (200, 200)),
            'hand_left': pygame.transform.scale(pygame.image.load('./assets/hand_left.png'), (200, 200)),
            'hand_left_up': pygame.transform.scale(pygame.image.load('./assets/hand_left_up.png'), (200, 200)),
            'hand_right_up': pygame.transform.scale(pygame.image.load('./assets/hand_right_up.png'), (200, 200)),
            'hand_left_down': pygame.transform.scale(pygame.image.load('./assets/hand_left_down.png'), (150, 150)),
            'hand_right_down': pygame.transform.scale(pygame.image.load('./assets/hand_right_down.png'), (150, 150)),
        }

        self.hand_icons = {
            'TOP LEFT': self._hand_icons['hand_left_up'],
            'TOP CENTER': self._hand_icons['hand'],
            'TOP RIGHT': self._hand_icons['hand_right_up'],

            'CENTER LEFT': self._hand_icons['hand_left_up'],
            'CENTER CENTER': self._hand_icons['hand'],
            'CENTER RIGHT': self._hand_icons['hand_right_up'],

            'BOTTOM LEFT': self._hand_icons['hand_left_down'],
            'BOTTOM CENTER': self._hand_icons['hand_down'],
            'BOTTOM RIGHT': self._hand_icons['hand_right_down'],
        }

    def set_scene(self, scene):
        def f():
            self.progress_bars = {}
            self.next_scene = scene(self.screen)
        return f

    @property
    def selector_icon(self):
        if self.current_area in self.used_areas:
            surface = self.hand_icons[self.current_area]
        else:
            surface = pygame.Surface((200, 200), pygame.SRCALPHA, 32)
            surface.fill((255, 255, 255, 0))
            pygame.draw.circle(surface, (255, 255, 255), (100, 100), 100, 5)
        return surface

    def draw_gaze_position(self):
        self.screen.blit(self.selector_icon, (hand_positions[self.current_area][0], hand_positions[self.current_area][1]))

    def process_received_message(self, message):
        if message['type'] == 'PYGAME_EVENT':
            for event in message['payload']:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.next_scene = ExitScene()
        elif message['type'] == 'EYE_GAZE':
            self.current_area = areas[message['payload']['current_area']]
            self.progress_bars = {}
            for area_tuple, progress in message['payload']['selection_progress_bars_by_area'].items():
                self.progress_bars[areas[area_tuple]] = progress
        elif message['type'] == 'EYE_GAZE_CLICK':
            button = self.menu_items[areas[message['payload']['current_area']]]
            if button:
                button.select()

    def draw_loquor_logo(self):
        logo = self.logo_font.render('LÓQUOR', True, (255, 255, 255))
        sublogo = self.font.render('Versión AME 0.6.27', 1, (255, 255, 255))
        self.screen.blit(logo, (positions['TOP LEFT'][0]+50, positions['TOP LEFT'][1]))
        self.screen.blit(sublogo, (positions['TOP LEFT'][0]+50, positions['TOP LEFT'][1]+100))

    def draw_progress_bars(self):
        for area, progress in self.progress_bars.items():
            if self.menu_items[area] is not None and progress > 0.05:
                x, y = positions[area]
                pygame.draw.rect(self.screen, HIGHLIGHTED_COLOR, (x-10, y-10, 250, 10))
                pygame.draw.rect(self.screen, (0, 255, 0), (x-10, y-10, progress*250, 10))

    def draw_menu_items(self):
        for position, item in self.menu_items.items():
            if item is not None:
                self.screen.blit(item.icon, positions[position])

    def draw_gaze(self):
        position = (positions[self.current_area][0]+230//2-20, positions[self.current_area][1]+230//2-20)
        pygame.draw.circle(self.screen, (255, 0, 0, 0.5), position, 40)

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_menu_items()
        self.draw_gaze_position()
        self.draw_progress_bars()
        self.draw_loquor_logo()
