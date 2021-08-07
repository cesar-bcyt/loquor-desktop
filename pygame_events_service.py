import pygame
from service import Service

class PygameEventsService(Service):
    def consume(self):
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        self.send_message_to_listeners({
            'type': 'PYGAME_EVENT',
            'payload': events,
        })

        self.send_message_to_listeners({
            'type': 'PYGAME_MOUSE_POS',
            'payload': mouse_pos,
        })
