# user_event_router.py

class UserEventRouter:
    def __init__(self):
        self.listeners = []

    def register(self, callback):
        self.listeners.append(callback)

    def on_user_message(self, text):
        for fn in self.listeners:
            try:
                fn(text)
            except:
                pass
