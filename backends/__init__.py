
import logging
from .slurm import Slurm

log = logging.getLogger('slurmy')


backend_list = set([Slurm.bid])

def get_backend(bid):
  if bid == Slurm.bid: return Slurm()
  else:
    log.error('Unknown backend "{}"'.format(bid))
    return None
