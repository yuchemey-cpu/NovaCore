# Core/base_module.py

class NovaModule:
    def __init__(self, name: str):
        self.name = name
        self.core = None

    def attach_core(self, core):
        self.core = core

    def on_event(self, event_type: str, data: dict):
        pass
