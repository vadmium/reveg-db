from lib import Function

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

class InnerClass(type):
    def __get__(self, outer, outer_class):
        if outer is None:
            return self
        vars = dict(__init__=BoundInit(self, outer))
        return type(self.__name__, (self,), vars)
class BoundInit(Function):
    def __init__(self, type, outer):
        self.type = type
        self.outer = outer
    def __call__(self, inner, *args, **kw):
        return self.type.__init__(inner, self.outer, *args, **kw)
