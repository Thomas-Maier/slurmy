
from enum import Enum


class Status(Enum):
  Configured = 0
  Running = 1
  Finished = 2
  Success = 3
  Failed = 4
  Cancelled = 5

class Theme(Enum):
  Boring = 0
  Lovecraft = 1
  Nordic = 2
  ImperiumOfMan = 3
  Chaos = 4

def adjectives():
  return ['Angry', 'Happy', 'Moist', 'Posh', 'Dainty', 'Peculiar', 'Stinky', 'Crazy', 'Handsome', 'Magnificent', 'Grumpy']
