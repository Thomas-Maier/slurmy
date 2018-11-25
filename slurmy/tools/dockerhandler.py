
import subprocess
import shlex
import re
import os
import logging
from .utils import check_return
from ..backends.slurm import Slurm

log = logging.getLogger('slurmy')


class DockerHandler:
    def __init__(self):
        self.bind_dir = '/tmp/slurmy_test'
        self._container_name = {}
        self._start_command = {}
        self._started_backends = set()
        self.command_wrapper = {}
        self._stop_command = {}
        ## Slurm
        self._container_name[Slurm.bid] = 'slurm'
        self._start_command[Slurm.bid] = self._get_start_command(self._container_name[Slurm.bid])
        self.command_wrapper[Slurm.bid] = DockerHandler._get_command_wrapper(self._container_name[Slurm.bid])
        self._stop_command[Slurm.bid] = DockerHandler._get_stop_command(self._container_name[Slurm.bid])
        ## TODO: HTCondor

    def start(self, bid):
        ## If we already started a container for this backend, there is nothing to do here
        if bid in self._started_backends:
            return
        ## Create the bind_dir if it doesn't exist yet (it's important that this happens before the container is started)
        if not os.path.isdir(self.bind_dir):
            os.system('mkdir -p {}'.format(self.bind_dir))
        container_name = self._container_name[bid]
        inspect_command = 'docker inspect -f "{{.State.Running}}" '+container_name
        ## Start new container if none with container_name already exists
        if not check_return(inspect_command):
            log.debug('Starting docker container "{}".'.format(container_name))
            os.system(self._start_command[bid])
        ## Get the output of the inspect command
        inspect_output = subprocess.check_output(shlex.split(inspect_command), universal_newlines = True)
        ## Check if the container is in Running state, the inspect output should be just "true\n" or "false\n"
        if re.findall('(.+?)\n', inspect_output) == 'false':
            log.error('Docker container "{}" is not in Running state, abort...')
            raise Exception
        ## Finally, add backend bid to already started backend containers
        self._started_backends.add(bid)

    def _get_start_command(self, container_name):
        command = 'docker run -h docker.example.com -p 10022:22 --rm -d --name {container_name} -v {bind_dir}:{bind_dir} agaveapi/slurm'.format(container_name = container_name, bind_dir = self.bind_dir)

        return command

    @staticmethod
    def _get_command_wrapper(container_name):
        wrapper = 'docker exec {}'.format(container_name)
        wrapper += ' {command}'

        return wrapper

    @staticmethod
    def _get_stop_command(container_name):
        command = 'docker container stop {}'.format(container_name)

        return command

## Main DockerHandler singleton
Main = DockerHandler()
