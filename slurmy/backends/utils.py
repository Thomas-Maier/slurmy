
from .defs import bids


backend_list = set([l[1] for l in bids.items() if l[0] != 'BASE'])

def get_backend(bid):
    import logging
    from .slurm import Slurm
    from .htcondor import HTCondor
    log = logging.getLogger('slurmy')
    if bid == bids['SLURM']: return Slurm()
    elif bid == bids['HTCONDOR']: return HTCondor()
    else:
        log.error('Unknown backend "{}"'.format(bid))
        return None
