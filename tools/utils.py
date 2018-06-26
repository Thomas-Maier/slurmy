
import logging
log = logging.getLogger('slurmy')


## Success classes
class SuccessOutputFile:
    """@SLURMY
    Callable class which can be used as success_func of a slurmy job. It checks if the output file that is associated to the job is present in the underlying file system.

    * `delay` Time (in seconds) that the job should wait before making the success evaluation.
    """
    def __init__(self, delay = 1):
        self._delay = delay
        
    def __call__(self, config):
        import os, time
        time.sleep(self._delay)

        return os.path.isfile(config.output)

class SuccessTrigger:
    """@SLURMY
    Callable class which can be used as success_func of a slurmy job. It continuously checks if either the success_file or the failure_file is present in the underlying file system.

    * `success_file` The file which is created if the job is successful.
    * `failure_file` The file which is created if the job failed.
    """
    def __init__(self, success_file, failure_file):
        self._success_file = success_file
        self._failure_file = failure_file

    def __call__(self, config):
        import os, time
        while True:
            if not (os.path.isfile(self._success_file) or os.path.isfile(self._failure_file)):
                time.sleep(0.5)
                continue
            if os.path.isfile(self._success_file):
                os.remove(self._success_file)
                return True
            else:
                os.remove(self._failure_file)
                return False

## Finished classes
class FinishedTrigger:
    """@SLURMY
    Callable class which can be used as finished_func of a slurmy job. It checks if finished_file is present in the underlying file system.

    * `finished_file` The file which is created if the job is finished.
    """
    def __init__(self, finished_file):
        self._finished_file = finished_file

    def __call__(self, config):
        import os
        finished = os.path.isfile(self._finished_file)
        if finished: os.remove(self._finished_file)

        return finished

## Post-function classes
class LogMover:
    """@SLURMY
    Callable class which can be used as post_func of a slurmy job. It moves the slurm log file to the new destination target_path.

    * `target_path` New destination of the log file.
    """
    def __init__(self, target_path):
        self._target_path = target_path

    def __call__(self, config):
        import os
        os.system('cp {} {}'.format(config.backend.log, self._target_path))

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

def get_sessions():
    """@SLURMY
    Get all available slurmy session according to the central bookkeeping.

    Returns list of bookkeeping items ([str, dict]).
    """
    from slurmy.tools import options as ops
    ## Synchronise bookkeeping with entries on disk
    ops.Main.sync_bookkeeping()
    bk = ops.Main.get_bookkeeping()
    if bk is None:
        log.debug('No bookeeping found')
        return []

    return sorted(bk.items(), key = lambda val: val[0].rsplit('_', 1)[-1])

def list_sessions():
    """@SLURMY
    List all available slurmy session according to the central bookkeeping.
    """
    sessions = get_sessions()
    for name, vals in sessions:
        path = vals['path']
        timestamp = vals['timestamp']
        description = vals['description']
        print_string = ('{}:\n  path: {}\n  timestamp: {}'.format(name, path, timestamp))
        if description: print_string += '\n  description: {}'.format(description)
        print (print_string)

def load(name):
    """@SLURMY
    Load a slurmy session by name.

    * `name` Name of the slurmy session, as listed by list_sessions().

    Returns jobhandler associated to the session (JobHandler).
    """
    from slurmy.tools import options as ops
    from slurmy import JobHandler
    import sys
    ## Synchronise bookkeeping with entries on disk
    ops.Main.sync_bookkeeping()
    bk = ops.Main.get_bookkeeping()
    if bk is None:
        log.error('No bookeeping found')
        return None
    python_version = sys.version_info.major
    if bk[name]['python_version'] != python_version:
        log.error('Python version "{}" of the snapshot not compatible with current version "{}"'.format(bk[name]['python_version'], python_version))
        return None
    work_dir = bk[name]['work_dir']
    jh = JobHandler(name = name, work_dir = work_dir, use_snapshot = True)

    return jh

def load_path(path):
    """@SLURMY
    Load a slurmy session by full path.

    * `path` Full folder path of the slurmy session, as listed by list_sessions().

    Returns jobhandler associated to the session (JobHandler).
    """
    from slurmy import JobHandler
    jh_name = path
    jh_path = ''
    if '/' in jh_name:
        jh_path = jh_name.rsplit('/', 1)[0]
        jh_name = jh_name.rsplit('/', 1)[-1]
    jh = JobHandler(name = jh_name, work_dir = jh_path, use_snapshot = True)

    return jh

def load_latest():
    """@SLURMY
    Load the latest slurmy session according to central bookkeeping.

    Returns jobhandler associated to the session (JobHandler).
    """
    sessions = get_sessions()
    if not sessions:
        log.debug('No recorded sessions found')
        return None
    latest_session_name = sessions[-1][0]

    return load(latest_session_name)

## Prompt utils
def get_input_func():
    from sys import version_info
    input_func = None
    if version_info.major == 3:
        input_func = input
    else:
        input_func = raw_input

    return input_func

def _prompt_decision(message):
    while True:
        string = get_input_func()('{} (y/n): '.format(message))
        if string == 'y':
            return True
        elif string == 'n':
            return False
        else:
            print ('Please answer with "y" or "n"')

## Properties utils
def _get_update_property(name):
    def getter(self):
        return getattr(self, name)
    
    def setter(self, val):
        log.debug('Set attribute "{}" of class "{}" to value "{}"'.format(name, self, val))
        if getattr(self, name) != val:
            log.debug('Value changed, tag for update')
            self.update = True
        setattr(self, name, val)
        
    return property(fget = getter, fset = setter)

def set_update_properties(class_obj):
    for prop_name in class_obj._properties:
        setattr(class_obj, prop_name.strip('_'), _get_update_property(prop_name))
    setattr(class_obj, 'update', True)

## Update decorator
def update_decorator(func):
    def new_func(self, *args, **kwargs):
        self.update = True
        
        return func(self, *args, **kwargs)

    return new_func

## Folder utils
def make_dir(folder):
    import os
    if not os.path.isdir(folder):
        os.makedirs(folder)

def remove_content(folder):
    import os, glob
    for file_name in glob.glob(os.path.join(folder, '*')):
        os.remove(file_name)
