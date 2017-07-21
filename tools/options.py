
import logging
import json
import os
import datetime

log = logging.getLogger('slurmy')

## TODO: any function call should trigger reading the options file and just store all of the options (in a dictionary), top layer is like ['General', 'Backend1', 'Backend2'...] and the options for the backends can then easily be set using __dict__ if the names between the options file and the member vars of the backends match properly

class Options:
  _options_file = '{}/.slurmy'.format(os.environ['HOME'])

  def __init__(self):
    ## General options (as defined in _options_file)
    self.bookkeeping = None
    self.workdir = None
    self.backend = None
    ## Backend options
    self._backend_options = {}
    ## Internal vars
    self._bookkeeping = None
    ## Read options from _options_file
    self._read_options()

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

  # def get_backend_name(self):
  #   self._read_options()
    
  #   return self.backend

  def get_bookkeeping(self):
    ## If bookkeeping was already retrieved, do nothing
    if self._bookkeeping: return self._bookkeeping
    # self._read_options()
    if self.bookkeeping is None:
      log.error('No bookkeeping file defined')
      return
    self.bookkeeping = Options._parse_file_name(self.bookkeeping)
    ## Set empty dictionary as default
    self._bookkeeping = {}
    if os.path.isfile(self.bookkeeping):
      with open(self.bookkeeping, 'r') as in_file:
        self._bookkeeping = json.load(in_file)

    return self._bookkeeping

  def add_bookkeeping(self, name, work_dir):
    path = '{}/{}'.format(work_dir.rstrip('/'), name)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    self.get_bookkeeping()
    self._bookkeeping[path] = {'timestamp': timestamp, 'name': name, 'work_dir': work_dir}
    self._update_bookkeeping()

  def _update_bookkeeping(self):
    with open(self.bookkeeping, 'w') as out_file:
      json.dump(self._bookkeeping, out_file)

  ## TODO: only checking if the backend_options are already set is not really robust
  def _read_options(self, force = False):
    ## If options were already filled, do nothing
    if self._backend_options and not force: return
    lines = None
    with open(Options._options_file, 'r') as in_file:
      lines = filter(None, [line.strip() for line in in_file if not line.startswith('#')])
    for line in lines:
      if not Options._check_line(line): continue
      line_list = line.split('=', 1)
      domain = None
      option = line_list[0]
      if '.' in line_list[0]:
        domain, option = line_list[0].split('.', 1)
        ## Remove stray whitespaces
        domain = domain.strip()
      option = option.strip()
      ## Remove potential comment at end of the line
      val = line_list[-1].split('#', 1)[0].strip()
      if domain is None:
        ## Set general options
        if option not in self:
          log.warning('Unknown general option "{}"'.format(option))
          continue
        if self[option] is not None:
          log.warning('You are trying to set a general option twice, ignoring duplicate')
          continue
        self[option] = val
      else:
        ## Fill options dict with backend options
        if domain not in self._backend_options: self._backend_options[domain] = {}
        if option in self._backend_options[domain]:
          log.warning('You are trying to set a backend option twice, ignoring duplicate')
          continue
        self._backend_options[domain][option] = val

  @staticmethod
  def _parse_file_name(file_name):
    name_return = file_name
    if file_name.startswith('~/'): name_return = '{}{}'.format(os.environ['HOME'], file_name.replace('~', '', 1))

    return name_return
    

  @staticmethod
  def get_backend_options(backend):
    lines = None
    with open(Options._options_file, 'r') as in_file:
      lines = filter(None, [line.strip() for line in in_file if not line.startswith('#') and line.startswith('{}.'.format(backend.bid))])
    for line in lines:
      if not Options._check_line(line): continue
      line_list = line.split('=', 1)
      option = line_list[0].split('.', 1)[-1].strip()
      ## Remove potential comment at end of the line
      val = line_list[-1].split('#', 1)[0].strip()
      if not option in backend:
        log.warning('Option "{}" not in backend "{}"'.format(option, backend.bid))
        continue
      backend[option] = val

  @staticmethod
  def _check_line(line):
    if line.count('.') > 1:
      log.warning('Bad line in options file (too many . delimiter): {}'.format(line))
      return False
    if line.count('=') > 1:
      log.warning('Bad line in options file (too many = delimiter): {}'.format(line))
      return False
    if line.count('=') == 0:
      log.warning('Bad line in options file (missing = delimiter): {}'.format(line))

    return True

## Main options singleton
Main = Options()

if __name__ == '__main__':
  print (Main)
  print (Main.backend, Main.workdir)
  Main.get_bookkeeping()
  print (Main)
