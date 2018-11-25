
import json
import os
import sys
import datetime
import logging
import subprocess
import shlex
import re
from ..backends.utils import backend_list, get_backend
from . import dockerhandler

log = logging.getLogger('slurmy')


class Options(object):
    _options_file = '{}/.slurmy'.format(os.environ['HOME'])

    def __init__(self):
        ## General options. Set defaults here, which are overwritten by values set in _options_file.
        self.bookkeeping = '{}/.slurmy_bookkeeping'.format(os.environ['HOME'])
        self.workdir = './'
        self.backend = None
        self.editor = None
        self.user = os.environ['USER']
        self.command_wrapper = {key: '{command}' for key in backend_list}
        ## Additional options
        self.test_mode = False
        self.interactive_mode = False
        self.profile_mode = False
        self.docker_mode = False
        ## Default backends which hold the options configured in _options_file
        self._backend_defaults = {}
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

    def get_bookkeeping(self):
        ## If bookkeeping was already retrieved, do nothing
        if self._bookkeeping:
            return self._bookkeeping
        if self.bookkeeping is None:
            log.error('No bookkeeping file defined')
            return None, None
        self.bookkeeping = Options._parse_file_name(self.bookkeeping)
        ## Set empty dictionary as default
        self._bookkeeping = {}
        if os.path.isfile(self.bookkeeping):
            with open(self.bookkeeping, 'r') as in_file:
                self._bookkeeping = json.load(in_file)

        return self._bookkeeping

    def add_bookkeeping(self, name, work_dir, description = None):
        ## Make sure bookkeeping is already loaded from file
        self.get_bookkeeping()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        path = os.path.join(work_dir, name)
        self._bookkeeping[name] = {'timestamp': timestamp, 'path': path, 'work_dir': work_dir, 'description': description, 'python_version': sys.version_info.major}
        self._update_bookkeeping()

    def sync_bookkeeping(self):
        ## Make sure bookkeeping is already loaded from file
        tmp = self.get_bookkeeping()
        ## If no bookkeeping is present, do nothing
        if tmp is None: return
        pop_names = set()
        for name, vals in self._bookkeeping.items():
            path = vals['path']
            ## If folder exists, assume that bookkeeping entry still exists on disk
            if os.path.isdir(path): continue
            pop_names.add(name)
        for name in pop_names:
            self._bookkeeping.pop(name)
        self._update_bookkeeping()

    def _update_bookkeeping(self):
        with open(self.bookkeeping, 'w') as out_file:
            json.dump(self._bookkeeping, out_file)

    ## TODO: use regex here
    ## TODO: only checking if the backend_options are already set is not really robust
    def _read_options(self, force = False):
        ## If no options file present, do nothing
        if not os.path.isfile(Options._options_file): return
        ## If options were already filled, do nothing
        if self._backend_defaults and not force: return
        backend_options = {}
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
                self[option] = val
            else:
                ## Fill options dict with backend options
                if domain not in backend_list:
                    log.warning('Trying to add an option for unknown backend "{}", list of available backends: {}'.format(domain, backend_list))
                    continue
                if domain not in backend_options: backend_options[domain] = {}
                if option in backend_options[domain]:
                    log.warning('Trying to set a backend option twice, ignoring duplicate')
                    continue
                backend_options[domain][option] = val
        ## Check if backend from options file is refering to an available backend
        if self.backend is not None and self.backend not in backend_list:
            log.warning('Unknown backend "{}", list of available backends: {}'.format(self.backend, backend_list))
            ## Setting backend to None
            self.backend = None
        ## Set backend defaults according to backend options from options file
        self._set_backend_defaults(backend_options)

    def _set_backend_defaults(self, backend_options):
        for domain in backend_options:
            backend = get_backend(domain)
            for option, val in backend_options.items():
                if not option in backend:
                    log.warning('Option "{}" not in backend "{}"'.format(option, backend.bid))
                    continue
                ## If option was already set, give priority to that
                backend[option] = backend[option] or val
            ## Add backend to defaults
            self._backend_defaults[domain] = backend

    def sync_backend(self, backend):
        bid = backend.bid
        if bid not in self._backend_defaults:
            return
        backend.sync(self._backend_defaults[bid])

    def set_docker_mode(self):
        log.debug('Setting up docker mode...')
        ## Set docker mode flag
        self.docker_mode = True
        ## Set user option to root
        self.user = 'root'
        ## Set workdir to DockerHandler bind_dir
        self.workdir = dockerhandler.Main.bind_dir
        ## Set command wrappers to docker wrappers
        self.command_wrapper.update(dockerhandler.Main.command_wrapper)

    @staticmethod
    def _parse_file_name(file_name):
        name_return = file_name
        if file_name.startswith('~/'): name_return = '{}{}'.format(os.environ['HOME'], file_name.replace('~', '', 1))

        return name_return

    @staticmethod
    def _check_line(line):
        if line.count('.') > 1:
            log.warning('Bad line in options file (too many "." delimiter): {}'.format(line))
            return False
        if line.count('=') > 1:
            log.warning('Bad line in options file (too many "=" delimiter): {}'.format(line))
            return False
        if line.count('=') == 0:
            log.warning('Bad line in options file (missing "=" delimiter): {}'.format(line))

        return True

## Main Options singleton
Main = Options()
