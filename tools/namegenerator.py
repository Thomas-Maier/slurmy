
import random
from .defs import Theme


class NameGenerator:
  ## Default to prevent problems
  _name_default = 'Slurmy'
  def __init__(self, name = None, theme = Theme.Lovecraft):
    self.name, self._name_list = NameGenerator._get_theme(name, theme)
    self._name_counter = {}
    
  def get_name(self):
    name = self._name_list[random.randint(0, len(self._name_list)-1)]
    if name not in self._name_counter: self._name_counter[name] = 0
    self._name_counter[name] += 1

    return '{}_{}'.format(name, self._name_counter[name])

  @staticmethod
  def _get_theme(name_given, theme):
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

    return name, name_list

  @staticmethod
  def _get_lovecraft_theme():
    name = 'Azathoth'
    name_list = ['Cthulhu', 'Ghatanothoa', 'Hastur', 'Nyarlathotep', 'Rhan-Tegoth', 'Shub-Niggurath', 'Tsathoggua', 'Yig', 'Yog-Sothoth', 'Shoggoth', 'Yith']

    return name, name_list
    
  @staticmethod
  def _get_nordic_theme():
    name = 'Odin'
    name_list = ['Baldur', 'Borr', 'Bragi', 'Dagr', 'Dellingr', 'Eir', 'Elli', 'Forseti', 'Freyja', 'Freyr', 'Frigg', 'Fulla', 'Gefjun', 'Hel', 'Heimdall', 'Kvasir', 'Lofn', 'Loki', 'Magni', 'Nanna', 'Nerthus', 'Njord', 'Sif', 'Sjoefn', 'Skadi', 'Snotra', 'Thor', 'Thrud', 'Tyr', 'Ull', 'Vidar', 'Voer', 'Yggdrasil']

    return name, name_list

  @staticmethod
  def _get_imperium_theme():
    name = 'God_Emperor_Of_Mankind'
    name_list = ['Lion-ElJonson', 'Jaghatai-Khan', 'Leman-Russ', 'Rogal-Dorn', 'Sanguinius', 'Ferrus-Manus', 'Roboute-Guilliman', 'Vulkan', 'Corvus-Corax']

    return name, name_list

  @staticmethod
  def _get_chaos_theme():
    name = 'Chaos'
    name_list = ['Khorne', 'Nurgle', 'Tzeentch', 'Slaanesh', 'Fulgrim', 'Perturabo', 'Konrad-Curze', 'Angron', 'Mortarion', 'Magnus-the-Red', 'Horus-Lupercal', 'Lorgar-Aurelian', 'Alpharius-Omegon']

    return name, name_list
