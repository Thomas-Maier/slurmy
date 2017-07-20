
import logging
import json
import os
import datetime

log = logging.getLogger('slurmy')


class Options:
  _options_file = '{}/.slurmy'.format(os.environ['HOME'])

  def __init__(self):
    self._bookkeeping_file = None
    self._bookkeeping = None

  def get_bookkeeping(self):
    self._bookkeeping = self._bookkeeping or self._get_bookkeeping()

    return self._bookkeeping

  def add_bookkeeping(self, name, work_dir):
    path = '{}/{}'.format(work_dir.rstrip('/'), name)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    self.get_bookkeeping()
    self._bookkeeping[path] = {'timestamp': timestamp, 'name': name, 'work_dir': work_dir}
    with open(self._bookkeeping_file, 'w') as out_file:
      json.dump(self._bookkeeping, out_file)

  def _get_bookkeeping(self):
    bookkeeping_file = None
    with open(Options._options_file, 'r') as in_file:
      for line in in_file:
        if not 'bookkeeping' in line: continue
        if not Options._check_line(line): continue
        bookkeeping_file = line.split('=', 1)[-1].split('#', 1)[0].strip()
    if bookkeeping_file is None:
      log.error('No bookkeeping file defined')
      return None
    bookkeeping_file = Options._parse_file_name(bookkeeping_file)
    self._bookkeeping_file = self._bookkeeping_file or bookkeeping_file
    bookkeeping = {}
    if os.path.isfile(bookkeeping_file):
      with open(bookkeeping_file, 'r') as in_file:
        bookkeeping = json.load(in_file)

    return bookkeeping

  @staticmethod
  def _parse_file_name(file_name):
    name_return = None
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
