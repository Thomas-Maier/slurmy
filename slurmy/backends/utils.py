
import logging
from .defs import bids

log = logging.getLogger('slurmy')


backend_list = set([l[1] for l in bids.items() if l[0] != 'BASE'])

def get_backend_class(bid):
    from .slurm import Slurm
    from .htcondor import HTCondor
    if bid == bids['SLURM']: return Slurm
    elif bid == bids['HTCONDOR']: return HTCondor
    else:
        log.error('Unknown backend bid "{}"'.format(bid))
        return None

def get_backend(bid):
    backend_class = get_backend_class(bid)
    if backend_class is None:
        return None
    else:
        return backend_class()
