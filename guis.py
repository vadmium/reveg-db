from types import MethodType

def pick():
    try:
        from wingui import Win
    except ImportError:
        from tkgui import Ttk
        return Ttk()
    return Win()

def label_key(label, key=None):
    if key:
        label = "{label} (&{key})".format_map(locals())
    return label

class MethodClass(type):
    def __get__(self, obj, cls):
        if obj is None:
            return self
        return MethodType(self, obj)
