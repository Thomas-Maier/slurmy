
import cProfile, pstats


class Profiler(object):
    def __init__(self, print_restrictions = [], sortby = 'cumulative'):
        self._profile = cProfile.Profile()
        self._print_restrictions = print_restrictions
        self._sortby = sortby

    def start(self):
        self._profile.enable()

    def stop(self):
        self._profile.disable()
        ps = pstats.Stats(self._profile).sort_stats(self._sortby)
        ps.print_stats(*self._print_restrictions)
