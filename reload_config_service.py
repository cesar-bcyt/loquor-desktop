from service import Service

class ReloadConfigService(Service):
    def setup(self):
        self.reload_config = False

    def reload(self):
        self.reload_config = True

    def reloaded(self):
        self.reload_config = False

    def consume(self):
        self.send_message_to_listeners({
            'type': 'CONFIG',
            'payload': {
                'reload_config': self.reload_config
            }
        })

reload_config_service = ReloadConfigService()
