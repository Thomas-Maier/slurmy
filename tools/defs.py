
from enum import Enum


class Status(Enum):
    CONFIGURED = 0
    RUNNING = 1
    FINISHED = 2
    SUCCESS = 3
    FAILED = 4
    CANCELLED = 5

class Type(Enum):
    BATCH = 0
    LOCAL = 1

class Mode(Enum):
    ACTIVE = 0
    PASSIVE = 1

class Theme(Enum):
    Boring = 0
    Lovecraft = 1
    Nordic = 2
    ImperiumOfMan = 3
    Chaos = 4

def adjectives():
    return ['Angry', 'Happy', 'Moist', 'Posh', 'Dainty', 'Peculiar', 'Stinky', 'Crazy', 'Handsome', 'Magnificent', 'Grumpy']
