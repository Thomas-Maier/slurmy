
import subprocess
import shlex
import logging

log = logging.getLogger('slurmy')


class Base:
  bid = 'Base'
  _commands = []
  def __getitem__(self, key):
    return self.__dict__[key]
    
  def __setitem__(self, key, val):
    self.__dict__[key] = val

  def __contains__(self, key):
    return (key in self.__dict__)

  def __repr__(self):
    print_string = ''
    for key, val in self.__dict__.items():
      print_string += '{}: {}\n'.format(key, val)
    print_string = print_string.rstrip('\n')

    return print_string

  def sync(self, config):
    if config is None: return
    if not isinstance(config, self.__class__):
      log.error('({})Backend class "{}" does not match class "{}" of sync object'.format(self.name, self.__class__, config.__class__))
      return
    for key in self.__dict__.keys():
      if key.startswith('_'): continue
      log.debug('({})Synchronising option "{}"'.format(self.name, key))
      self[key] = self[key] or config[key]

  def _check_commands(self):
    for command in self._commands:
      if Base._check_command(command): continue
      log.error('{} command not found: "{}"'.format(self.bid, command))
      raise Exception

  @staticmethod
  def _check_command(command):
    proc = subprocess.Popen(shlex.split('which {}'.format(command)), stdout = subprocess.PIPE, stderr = subprocess.STDOUT, universal_newlines = True)
    ret_code = proc.wait()
    if ret_code != 0:
      return False

    return True
