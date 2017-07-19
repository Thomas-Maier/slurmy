
import random
from .defs import Theme


class NameGenerator:
  def __init__(self, name = None, theme = Theme.Lovecraft):
    self._name = ''
    self._name_list = []
    if theme == Theme.Lovecraft:
      self._name = 'Azathoth'
      self._name_list = ['Cthulhu', 'Ghatanothoa', 'Hastur', 'Nyarlathotep', 'Rhan-Tegoth', 'Shub-Niggurath', 'Tsathoggua', 'Yig', 'Yog-Sothoth', 'Shoggoth', 'Yith']
    elif theme == Theme.Lame:
    
  def get_name(self):
    return self._name_list[random.randint(0, len(self._name_list)-1)]
