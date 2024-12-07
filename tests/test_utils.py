"""Test utilities for NADOO Framework tests."""

class TestElement:
    def __init__(self, id_str, value):
        self._id = id_str
        self._value = value
        self._completed = False
        self._hidden = False
        
    def get_id(self):
        return self._id
        
    def get_card(self):
        return {
            "id": self._id,
            "value": self._value,
            "completed": self._completed,
            "hidden": self._hidden
        }
        
    def complete(self):
        self._completed = True
        
    def hide(self):
        self._hidden = True
