
import logging
logging.basicConfig(level=logging.WARNING)
from .tools.jobhandler import JobHandler
from .tools.defs import Theme
from .tools import options

def test_mode(mode = True):
    options.Main.test_mode = mode
