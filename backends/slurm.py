
import subprocess
import os
import shlex
import logging
from ..tools.defs import Status
from .base import Base
from ..tools import options as ops
from .defs import bids

log = logging.getLogger('slurmy')


class Slurm(Base):
    bid = bids['SLURM']
    _script_options_identifier = 'SBATCH'
    _commands = ['sbatch', 'scancel', 'squeue', 'sacct']
    def __init__(self, name = None, log = None, run_script = None, run_args = None, partition = None, exclude = None, clusters = None, qos = None, mem = None, time = None, export = None):
        ## Common backend options
        self.name = name
        self.log = log
        self.run_script = run_script
        self.run_args = run_args
        ## Batch options
        self.partition = partition
        self.clusters = clusters
        self.qos = qos
        self.exclude = exclude
        self.mem = mem
        self.time = time
        self.export = export
        ## Internal variables
        self._job_id = None
        self._exitcode = None
        ## Get default options
        ops.Main.get_backend_options(self)
        ## Check if necessary slurm commands are available on the system
        self._check_commands()

    def submit(self):
        submit_list = ['sbatch']
        if self.name: submit_list += ['-J', self.name]
        if self.log: submit_list += ['-o', self.log]
        if self.partition: submit_list += ['-p', self.partition]
        if self.exclude: submit_list += ['-x', self.exclude]
        if self.clusters: submit_list += ['-M', self.clusters]
        if self.qos: submit_list.append('--qos={}'.format(self.qos))
        if self.mem: submit_list.append('--mem={}'.format(self.mem))
        if self.time: submit_list.append('--time={}'.format(self.time))
        if self.export: submit_list.append('--export={}'.format(self.export))
        submit_list.append(self.run_script)
        if self.run_args:
            ## shlex splits run_args in a Popen digestable way
            if isinstance(self.run_args, str): self.run_args = shlex.split(self.run_args)
            submit_list += self.run_args
        log.debug('({}) Submit job with command {}'.format(self.name, submit_list))
        submit_string = subprocess.check_output(submit_list, universal_newlines = True)
        job_id = int(submit_string.split(' ')[3].rstrip('\n'))
        self._job_id = job_id

        return job_id

    def cancel(self):
        log.debug('({}) Cancel job'.format(self.name))
        os.system('scancel {}'.format(self._job_id))

    def status(self):
        sacct_list = self._get_sacct_entry('State,ExitCode')
        status = Status.RUNNING
        if sacct_list is not None:
            status = Status.FINISHED
            self._exitcode = sacct_list[-1]

        return status

    def exitcode(self):
        return self._exitcode

    def _get_sacct_entry(self, column):
        sacct_list = ['sacct']
        if self.partition:
            sacct_list.extend(['-r', self.partition])
        if self.clusters:
            sacct_list.extend(['-M', self.clusters])
        sacct_list.extend(['-j', '{}.batch'.format(self._job_id), '-P', '-o', column])
        sacct_list = subprocess.check_output(sacct_list, universal_newlines = True).rstrip('\n').split('\n')
        sacct_return = None
        if len(sacct_list) > 1:
            sacct_return = sacct_list[1].split('|')
            log.debug('({}) Column "{}" string from sacct: {}'.format(self.name, column, sacct_return))

        return sacct_return
