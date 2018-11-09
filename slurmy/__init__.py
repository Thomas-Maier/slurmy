
name = 'slurmy'
import logging
logging.basicConfig(level = logging.INFO)
from .tools.jobhandler import JobHandler
from .tools.defs import Status, Type, Theme, Mode
from .tools import options
from .tools.wrapper import SingularityWrapper
from .backends.slurm import Slurm
from .backends.htcondor import HTCondor
from .tools.utils import SuccessTrigger, FinishedTrigger, LogMover, CmdLineExec
from .tools.profiler import Profiler

def test_mode(mode = True):
    options.Main.test_mode = mode
