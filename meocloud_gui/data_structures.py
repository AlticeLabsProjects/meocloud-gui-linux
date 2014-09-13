from _ordereddict import ordereddict as OrderedDict


class BoundedOrderedDict(OrderedDict):
    __slots__ = ('cache', 'maxsize')

    def __init__(self, *args, **kwargs):
        self.maxsize = kwargs.pop('maxsize', None)
        OrderedDict.__init__(self, *args, **kwargs)
        self._trim_cache()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._trim_cache()

    def _trim_cache(self):
        if self.maxsize:
            while len(self) > self.maxsize:
                self.popitem(0)
