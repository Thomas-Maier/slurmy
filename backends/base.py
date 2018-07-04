
import subprocess
import shlex
import logging
import os
import stat
from ..tools import options
from ..tools.utils import _prompt_decision
from .defs import bids
from ..tools.wrapper import Wrapper

log = logging.getLogger('slurmy')


class Base(object):
    bid = bids['BASE']
    _script_options_identifier = ''
    _commands = []
    _successcode = '0:0'
    name = None
    log = None
    wrapper = Wrapper()
    run_script = None
    run_args = None

    def __init__(self):
        self._check_commands()

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

    def load_default_config(self):
        """@SLURMY
        Load the default backend configuration, as defined in the slurmy config file.
        """
        options.Main.get_backend_options(self)

    def sync(self, config):
        """@SLURMY
        Synchronise backend configuration with reference one. Options from self are prioritised.

        * `config` Reference backend object to synchronise with.
        """
        if config is None: return
        if not isinstance(config, self.__class__):
            log.error('({})Backend class "{}" does not match class "{}" of sync object'.format(self.name, self.__class__, config.__class__))
            return
        for key in self.__dict__.keys():
            if key.startswith('_'): continue
            log.debug('({})Synchronising option "{}"'.format(self.name, key))
            self[key] = self[key] or config[key]

    def write_script(self, script_folder):
        """@SLURMY
        Write the run_script according to configuration.

        * `script_folder` Folder to store the script file in.
        """
        out_file_name = os.path.join(script_folder, self.name)
        ## If the provided run script is already existing, just copy it
        if os.path.isfile(self.run_script):
            os.system('cp {} {}'.format(self.run_script, out_file_name))
            with open(out_file_name, 'r') as in_file:
                self.run_script = in_file.read()
        ## Bash shebang required for slurm submission script, but probably fairly general (to be followed up after other backend implementations)
        if not self.run_script.startswith('#!'):
            self.run_script = '#!/bin/bash\n' + self.run_script
        ## Execute wrapper setup
        self.run_script = self.wrapper.setup(self.run_script, self._script_options_identifier)
        ## Write run script
        with open(out_file_name, 'w') as out_file:
            out_file.write(self.run_script)
        ## Set run script path
        self.run_script = out_file_name
        ## Set executable permissions
        os.chmod(self.run_script, stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    def _check_commands(self):
        ## If we are in test mode, skip this sanity check
        if options.Main.test_mode:
            return
        for command in self._commands:
            if Base._check_command(command): continue
            log.error('{} command not found: "{}"'.format(self.bid, command))
            ## If we are in interactive mode, switch into test/local mode. If in normal mode, prompt the user.
            if options.Main.interactive_mode:
                log.warning('Switching to test/local mode (batch submission will not work)!')
                options.Main.test_mode = True
                break
            elif _prompt_decision('Switch to test mode (batch submission will not work)?'):
                options.Main.test_mode = True
                break
            raise Exception

    @staticmethod
    def _check_command(command):
        proc = subprocess.Popen(shlex.split('which {}'.format(command)), stdout = subprocess.PIPE, stderr = subprocess.STDOUT, universal_newlines = True)
        ret_code = proc.wait()
        ## Close stdout streaming
        proc.stdout.close()
        if ret_code != 0:
            return False

        return True

    ## Backend specific implementations
    def submit(self):
        return 0

    def cancel(self):
        return 0

    def status(self):
        return 0

    def exitcode(self):
        return 0
