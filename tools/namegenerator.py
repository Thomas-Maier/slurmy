
import random
from .defs import Theme


class NameGenerator:
  def __init__(self, name = None, theme = Theme.Lovecraft):
    self.name = name
    self._name_list = []
    self._name_counter = {}
    if theme == Theme.Lovecraft:
      if not self.name: self.name = 'Azathoth'
      self._name_list = ['Cthulhu', 'Ghatanothoa', 'Hastur', 'Nyarlathotep', 'Rhan-Tegoth', 'Shub-Niggurath', 'Tsathoggua', 'Yig', 'Yog-Sothoth', 'Shoggoth', 'Yith']
    elif theme == Theme.Boring:
      pass
    
  def get_name(self):
    name = self._name_list[random.randint(0, len(self._name_list)-1)]
    if name not in self._name_counter: self._name_counter[name] = 0
    self._name_counter[name] += 1

    return '{}_{}'.format(name, self._name_counter[name])
