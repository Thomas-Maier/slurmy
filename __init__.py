
import logging
logging.basicConfig(level=logging.WARNING)
from .tools.jobhandler import JobHandler
from .tools.defs import Status, Type, Theme
from .tools import options
from .tools.wrapper import SingularityWrapper
from .backends.slurm import Slurm
from .tools.utils import SuccessOutputFile, SuccessTrigger, FinishedTrigger, LogMover

def test_mode(mode = True):
    options.Main.test_mode = mode
