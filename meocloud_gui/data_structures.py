import gc

try:
    from _ordereddict import ordereddict as OrderedDict
    have_fast_odict = True
except ImportError:
    have_fast_odic = False
    from collections import OrderedDict


class BoundedOrderedDict(OrderedDict):
    __slots__ = ('_pop', 'maxsize')

    def __init__(self, *args, **kwargs):
        self.maxsize = kwargs.pop('maxsize', None)
        OrderedDict.__init__(self, *args, **kwargs)
        self._trim_cache()
        if have_fast_odict:
            self._pop = lambda: self.popitem(0)
        else:
            self._pop = lambda: self.popitem(last=False)

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._trim_cache()

    def _trim_cache(self):
        if self.maxsize:
            while len(self) > self.maxsize:
                self._pop()
            gc.collect()
