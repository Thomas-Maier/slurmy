
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
  bk_keys, bk_sessions = ops.Main.get_bookkeeping()
  if bk_sessions is None:
    log.error('No bookeeping found')
    return
  for key, path in bk_keys.items():
    name = bk_sessions[path]['name']
    timestamp = bk_sessions[path]['timestamp']
    description = bk_sessions[path]['description']
    print_string = ('{}:\n  path: {}\n  timestamp: {}'.format(key, path, timestamp))
    if description: print_string += '\n  description: {}'.format(description)
    print (print_string)

def load(key):
  from slurmy.tools import options as ops
  from slurmy import JobHandler
  import logging
  log = logging.getLogger('slurmy')
  ## Synchronise bookkeeping with entries on disk
  ops.Main.sync_bookkeeping()
  bk_keys, bk_sessions = ops.Main.get_bookkeeping()
  if bk_sessions is None:
    log.error('No bookeeping found')
    return None
  session = bk_sessions[bk_keys[key]]
  name = session['name']
  work_dir = session['work_dir']
  jh = JobHandler(name = name, work_dir = work_dir, use_snapshot = True)

  return jh
