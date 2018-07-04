
import logging
from .defs import Status

log = logging.getLogger('slurmy')


class Parser(object):
    _prefix = '@SLURMY.'
    def __init__(self, config):
        ## The job/jobhandler config of the parent
        self.config = config

    def replace(self, string):
        ## Replace config variables
        for key, val in self.config.__dict__.items():
            if key.startswith('_'): continue
            string = string.replace('{}{}'.format(self._prefix, key), '{}'.format(val))
        ## Make sanity check and print warning if prefix string still exists in script
        if self._prefix in string: log.warning('Unknown {} variable in input string'.format(self._prefix))

        return string

    def set_status_label(self, string, identifier, status):
        label = '{}{}'.format(self._prefix, status.name)
        if label in string:
            label_file = '{}.{}.{}'.format(self.config.tmp_dir, identifier, status.name)
            string = string.replace(label, 'touch {}'.format(label_file))
            return string, label_file
        else:
            return string, None
