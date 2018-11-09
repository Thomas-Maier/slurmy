
import random
import time
import calendar
import logging
from .defs import Theme, adjectives

log = logging.getLogger('slurmy')


class NameGenerator(object):
    ## Default to prevent problems
    _name_default = 'Slurmy'
    def __init__(self, name = None, theme = Theme.Lovecraft, max_names = None, n_adjectives = None):
        self._theme = theme
        self._adjectives = adjectives()
        if n_adjectives is not None:
            while len(self._adjectives) > n_adjectives:
                self._adjectives.pop(random.randint(0, len(self._adjectives)-1))
        self.name, self._name_list = self._get_theme(name, self._theme)
        self._counter = 0
        self._cycle = 0
        self._max = max_names
        self._custom_names = {}

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self, custom_name = None):
        if custom_name is not None:
            name, self._counter = self._get_custom_name(custom_name), self._counter+1
        elif self._name_list:
            name, self._counter = self._name_list.pop(random.randint(0, len(self._name_list)-1)), self._counter+1
        elif (self._max is not None) and (self._counter >= self._max):
            raise StopIteration()
        else:
            self._cycle += 1
            tmp, self._name_list = self._get_theme(self.name, self._theme, suffix = '_{}'.format(self._cycle))
            name = self.next()
        ## Check if name works as class property
        self._check_name(name)

        return name

    def _get_custom_name(self, name):
        if name in self._custom_names:
            n_name = self._custom_names[name]
            self._custom_names[name] += 1
            return '{}_{}'.format(name, n_name)
        else:
            self._custom_names[name] = 1
            return name

    def _check_name(self, name):
        if '.' in name or '-' in name or ' ' in name or '/' in name:
            log.error('Found ".", "-", "/" or whitespace in job name, please treat as if it was a python variable')
            raise Exception

    def _get_theme(self, name_given, theme, suffix = ''):
        name = None
        name_list = None
        if theme == Theme.Lovecraft:
            name, name_list = NameGenerator._get_lovecraft_theme()
        elif theme == Theme.Nordic:
            name, name_list = NameGenerator._get_nordic_theme()
        elif theme == Theme.ImperiumOfMan:
            name, name_list = NameGenerator._get_imperium_theme()
        elif theme == Theme.Chaos:
            name, name_list = NameGenerator._get_chaos_theme()
        elif theme == Theme.Boring:
            name_list = [name_given]
        ## If a name was set in the constructor use this instead
        name = name_given or name
        ## Make sure that at least the default is used
        name = name or NameGenerator._name_default
        ## Add current unix time as suffix to name
        name = '{}_{}'.format(name, calendar.timegm(time.gmtime()))
        ## Make the full list of name combinations
        full_name_list = []
        if self._adjectives:
            for adj in self._adjectives:
                for entry in name_list:
                    full_name_list.append('{}_{}{}'.format(adj, entry, suffix))
        else:
            for entry in name_list:
                full_name_list.append('{}{}'.format(entry, suffix))

        return name, full_name_list

    @staticmethod
    def _get_lovecraft_theme():
        name = 'Azathoth'
        name_list = ['Cthulhu', 'Ghatanothoa', 'Hastur', 'Nyarlathotep', 'Rhan_Tegoth', 'Shub_Niggurath', 'Tsathoggua', 'Yig', 'Yog_Sothoth', 'Shoggoth', 'Yith']

        return name, name_list

    @staticmethod
    def _get_nordic_theme():
        name = 'Odin'
        name_list = ['Baldur', 'Borr', 'Bragi', 'Dagr', 'Dellingr', 'Eir', 'Elli', 'Forseti', 'Freyja', 'Freyr', 'Frigg', 'Fulla', 'Gefjun', 'Hel', 'Heimdall', 'Kvasir', 'Lofn', 'Loki', 'Magni', 'Nanna', 'Nerthus', 'Njord', 'Sif', 'Sjoefn', 'Skadi', 'Snotra', 'Thor', 'Thrud', 'Tyr', 'Ull', 'Vidar', 'Voer', 'Yggdrasil']

        return name, name_list

    @staticmethod
    def _get_imperium_theme():
        name = 'God_Emperor_Of_Mankind'
        name_list = ['Lion_ElJonson', 'Jaghatai_Khan', 'Leman_Russ', 'Rogal_Dorn', 'Sanguinius', 'Ferrus_Manus', 'Roboute_Guilliman', 'Vulkan', 'Corvus_Corax']

        return name, name_list

    @staticmethod
    def _get_chaos_theme():
        name = 'Chaos'
        name_list = ['Khorne', 'Nurgle', 'Tzeentch', 'Slaanesh', 'Fulgrim', 'Perturabo', 'Konrad_Curze', 'Angron', 'Mortarion', 'Magnus_the_Red', 'Horus_Lupercal', 'Lorgar_Aurelian', 'Alpharius_Omegon']

        return name, name_list
