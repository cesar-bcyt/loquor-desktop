class Service():
    def __init__(self):
        self.listeners = []
        self.setup()

    def setup(self):
        pass

    def consume(self):
        pass

    def register_listener(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unregister_listener(self, listener):
        self.listeners.remove(listener)

    def send_message_to_listeners(self, message):
        assert type(message) is dict
        for listener in self.listeners:
            listener.process_received_message(message)

class ListenerMixin():
    def process_received_message(self, message):
        pass
