class Scene():
    def __init__(self, screen):
        self.next_scene = None
        self.screen = screen

    def update(self):
        pass

    def draw(self):
        pass

    def get_next_scene(self):
        return self.next_scene
