import re
import logging
log = logging.getLogger('slurmy')


## Success classes/functions
class SuccessTrigger:
    """@SLURMY
    Callable class which can be used as success_func of a slurmy job. It checks if the success_file is present in the underlying file system, once a second. If the maximum number of attempts are reached without finding the file, it returns FAILED.

    * `success_file` The file which is created if the job is successful.
    * `max_attempts` Maximum number of attempts that will be tried to find the success_file.
    """
    def __init__(self, success_file, max_attempts):
        self._success_file = success_file
        self._max_attempts = max_attempts

    def __call__(self, config):
        import os, time, subprocess
        ## Make an explicit ls on the folders where the output files are written to
        ## This avoids problems with delayed updates in the underlying file system
        folder = os.path.dirname(self._success_file)
        try:
            subprocess.check_output(['ls', folder], universal_newlines = True, stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError:
            log.debug('Output folder {} does not exist, please check'.format(folder))
        ## Atempt to find success file
        for i in range(self._max_attempts):
            log.debug('Checking success file, attempt #{}'.format(i))
            if os.path.isfile(self._success_file):
                return True
            time.sleep(1)

        return False

def get_listen_files(file_list, folder_list, status):
    import logging
    log = logging.getLogger('slurmy')
    def listen_files(results, interval = 1):
        import os, time, subprocess
        from slurmy import Status
        from collections import OrderedDict
        while True:
            ## Make an explicit ls on the folders where the output files are written to
            ## This avoids problems with delayed updates in the underlying file system
            for folder in folder_list:
                try:
                    subprocess.check_output(['ls', folder], universal_newlines = True, stderr = subprocess.STDOUT)
                except subprocess.CalledProcessError:
                    log.debug('Output folder {} does not exist, please check'.format(folder))
            ## Collect the information and put in results
            res_dict = OrderedDict()
            for file_name in file_list:
                if not os.path.isfile(file_name): continue
                res_dict[file_name] = {'status': status}
            results.put(res_dict)
            time.sleep(interval)

    return listen_files

## Finished classes
class FinishedTrigger:
    """@SLURMY
    Callable class which can be used as finished_func of a slurmy job. It checks if finished_file is present in the underlying file system.

    * `finished_file` The file which is created if the job is finished.
    """
    def __init__(self, finished_file):
        self._finished_file = finished_file

    def __call__(self, config):
        import os, subprocess
        ## Make an explicit ls on the folders where the output files are written to
        ## This avoids problems with delayed updates in the underlying file system
        folder = os.path.dirname(self._finished_file)
        try:
            subprocess.check_output(['ls', folder], universal_newlines = True, stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError:
            log.debug('Output folder {} does not exist, please check'.format(folder))
            
        finished = os.path.isfile(self._finished_file)

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

class CmdLineExec:
    """@SLURMY
    Callable class which can be used as post_func of a slurmy job. It executes an arbitrary command line statement.

    * `command` Command line statement.
    """
    def __init__(self, command):
        self._command = command

    def __call__(self, config):
        import os
        os.system(self._command)

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
    from slurmy.tools import options
    ## Synchronise bookkeeping with entries on disk
    options.Main.sync_bookkeeping()
    bk = options.Main.get_bookkeeping()
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
    from slurmy.tools import options
    from slurmy import JobHandler
    import sys
    ## Synchronise bookkeeping with entries on disk
    options.Main.sync_bookkeeping()
    bk = options.Main.get_bookkeeping()
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
        val_old = getattr(self, name)
        log.debug('Set attribute "{}" of class "{}" from value "{}" to "{}"'.format(name, self, val_old, val))
        if val_old != val:
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

## String manipulation utils
def find_between(s, first, last):
    """Find first substring between two substrings first and last in string s."""
    expression = '{}(.+?){}'.format(first, last)
    results = re.findall(expression, s)
    if len(results) == 0:
        log.error('Could not find substring in "{s}" between "{first}" and "{last}"'.format(s=s, first=first, last=last))
        return ''
    else:
        return results[0]
