
import logging

log = logging.getLogger('slurmy')


class Parser:
  _prefix = '@SLURMY.'
  def __init__(self, config):
    ## The job/jobhandler config of the parent
    self.config = config

  def replace(self, string):
    for key, val in self.config.__dict__.items():
      if key.startswith('_'): continue
      string = string.replace('{}{}'.format(self._prefix, key), '{}'.format(val))
    if self._prefix in string: log.warning('Unknown {} variable in input string'.format(self._prefix))

    return string
