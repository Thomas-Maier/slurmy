
from enum import Enum
import random


class Status(Enum):
  Configured = 0
  Running = 1
  Finished = 2
  Success = 3
  Failed = 4
  Cancelled = 5

class NameGenerator:
  def __init__(self):
    self._name_list = ['Cthulhu', 'Azathoth', 'Ghatanothoa', 'Hastur', 'Nyarlathotep', 'Rhan-Tegoth', 'Shub-Niggurath', 'Tsathoggua', 'Yig', 'Yog-Sothoth', 'Shoggoth', 'Yith']
    
  def get_name(self):
    return self._name_list[random.randint(0, len(self._name_list)-1)]
