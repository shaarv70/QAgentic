from typing import Generic, TypeVar

T = TypeVar("T")



class BaseRegistry(Generic[T]):
    """
    ==========================================================
    Class : BaseRegistry

    Purpose:
        Generic registry for storing named objects.

    Responsibilities:
        • Register objects.
        • Return registered objects.
        • Enumerate registered objects.

    This class NEVER:
        ❌ Creates objects.
        ❌ Owns business logic.
    ==========================================================
    """
    def __init__(self):

        self._items: dict[str, T] = {}



    def register(self,name: str,item: T) -> None:

        if name in self._items:
            raise ValueError(f"{name} already registered.")

        self._items[name] = item




    def get(self, name:str)-> T:

        if name not in self._items:
             raise ValueError( f"Registry entry '{name}' not found.")

        return self._items[name]



    def items(self):
        """
        Iterate over all registered items.
        """

        return self._items.items()

    def values(self):
        """
        Return registered objects.
        """

        return self._items.values()

    def keys(self):
        """
        Return registered names.
        """

        return self._items.keys()


    def get_registered_names(self):

        return list(self.keys())