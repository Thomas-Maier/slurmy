
from enum import Enum


class Status(Enum):
  Configured = 0
  Running = 1
  Finished = 2
  Success = 3
  Failed = 4
  Cancelled = 5

class Theme(Enum):
  Lame = 0
  Lovecraft = 1
