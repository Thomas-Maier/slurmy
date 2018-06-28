
import cProfile, pstats


class Profiler:
    def __init__(self):
        self._profile = cProfile.Profile()

    def start(self):
        self._profile.enable()

    def stop(self, sortby = 'cumulative'):
        self._profile.disable()
        ps = pstats.Stats(self._profile).sort_stats(sortby)
        ps.print_stats(.1)
