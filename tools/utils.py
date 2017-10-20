
## Success classes
class SuccessOutputFile:
  def __call__(self, config):
    import os, time
    time.sleep(1)

    return os.path.isfile(config.output)

## Functions for interactive slurmy
def _get_prompt():
  try:
    from IPython import embed
    return embed
  except ImportError:
    ## Fallback if ipython not available
    import code
    shell = code.InteractiveConsole(globals())
    return shell.interact

def list_sessions():
  from slurmy.tools import options as ops
  import logging
  log = logging.getLogger('slurmy')
  ## Synchronise bookkeeping with entries on disk
  ops.Main.sync_bookkeeping()
  bk = ops.Main.get_bookkeeping()
  if bk is None:
    log.error('No bookeeping found')
    return
  for name, vals in sorted(bk.items(), key = lambda val: val[0].rsplit('_', 1)[-1]):
    path = vals['path']
    timestamp = vals['timestamp']
    description = vals['description']
    print_string = ('{}:\n  path: {}\n  timestamp: {}'.format(name, path, timestamp))
    if description: print_string += '\n  description: {}'.format(description)
    print (print_string)

def load(name):
  from slurmy.tools import options as ops
  from slurmy import JobHandler
  import logging
  log = logging.getLogger('slurmy')
  ## Synchronise bookkeeping with entries on disk
  ops.Main.sync_bookkeeping()
  bk = ops.Main.get_bookkeeping()
  if bk is None:
    log.error('No bookeeping found')
    return None
  work_dir = bk[name]['work_dir']
  jh = JobHandler(name = name, work_dir = work_dir, use_snapshot = True)

  return jh

def load_path(path):
  from slurmy import JobHandler
  jh_name = path
  jh_path = ''
  if '/' in jh_name:
    jh_path = jh_name.rsplit('/', 1)[0]
    jh_name = jh_name.rsplit('/', 1)[-1]
  jh = None
  # try:
  jh = JobHandler(name = jh_name, work_dir = jh_path, use_snapshot = True)
  # except ImportError:
  #   _log.error('Import error during pickle load, please make sure that your success class definition is in your PYTHONPATH')
  #   raise
  # except AttributeError:
  #   _log.error('')
  #   raise

  return jh
