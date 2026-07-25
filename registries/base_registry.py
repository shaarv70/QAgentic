class BaseRegistry:

    def __init__(self):
        self._items = {}

    def register(self, name, item):
        self._items[name] = item

    def get(self, name):
        if name not in self._items:
            raise ValueError(f"{name} not found")

        return self._items[name]