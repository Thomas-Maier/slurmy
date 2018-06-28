
from . import options


class Tracker:
    def __init__(self):
        self._info = {}
        
    def add(self, func_name):
        if func_name not in self._info:
            self._info[func_name] = 0
        self._info[func_name] += 1

    def print(self):
        print('--- Tracking ---')
        for func_name, val in self._info.items():
            print('{}: {}'.format(func_name, val))

## Main Tracker singleton
Main = Tracker()

def track(func):
    def new_func(self, *args, **kwargs):
        if options.Main.track_mode:
            func_name = '{}.{}'.format(self.__class__.__name__, func.__name__)
            Main.add(func_name)
        result = func(self, *args, **kwargs)

        return result

    return new_func
