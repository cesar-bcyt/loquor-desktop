import pygame
from styles import TEXT_COLOR

class MenuItem():
    def __init__(self, icon, parent, on_select=lambda: None, text=None, icon_selected=None, extra=(0, 0)):
        extra_x, extra_y = extra
        surface_selected = pygame.Surface((250+extra_x, 260+extra_y), pygame.SRCALPHA, 32)
        surface = pygame.Surface((250+extra_x, 260+extra_y), pygame.SRCALPHA, 32)
        icon = pygame.transform.scale(pygame.image.load(icon), (230, 230))
        if icon_selected:
            icon_selected = pygame.transform.scale(pygame.image.load(icon_selected), (230, 230))
            surface_selected.blit(icon_selected, (0, 0))
        surface.blit(icon, (0, 0))
        if text:
            text = parent.font.render(text, 1, TEXT_COLOR)
            surface.blit(text, ((250-text.get_width())//2-10, 235))
            surface_selected.blit(text, ((250-text.get_width())//2-10, 235))
        self.icon = surface
        self.icon_selected = surface_selected
        self.on_select = on_select

    def select(self):
        self.on_select()
