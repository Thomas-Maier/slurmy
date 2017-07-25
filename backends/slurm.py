
import subprocess
import os
import shlex
import logging
from ..tools.defs import Status
from .base import Base
from ..tools import options as ops

log = logging.getLogger('slurmy')
## TODO: add more sbatch options
## QUESTION: Can I ask slurm if currently there are free slots?

class Slurm(Base):
  bid = 'Slurm'
  _commands = ['sbatch', 'scancel', 'squeue', 'sacct']
  
  def __init__(self, name = None, log = None, partition = None, exclude = None, clusters = None, qos = None, run_script = None, run_args = None):
    self.name = name
    self.log = log
    self.partition = partition
    self.exclude = exclude
    self.clusters = clusters
    self.qos = qos
    self.run_script = run_script
    self.run_args = run_args
    self.job_id = None
    ## Get default options
    ops.Main.get_backend_options(self)
    ## Check if necessary slurm commands are available on the system
    self._check_commands()

  def write_script(self, script_folder):
    if os.path.isfile(self.run_script): return
    out_file_name = '{}/{}'.format(script_folder.rstrip('/'), self.name)
    with open(out_file_name, 'w') as out_file:
      ## Required for slurm submission script
      if not self.run_script.startswith('#!'): out_file.write('#!/bin/bash \n')
      out_file.write(self.run_script)
    self.run_script = out_file_name

  def sync(self, config):
    if config is None or not isinstance(config, Slurm): return
    self.name = self.name or config.name
    self.log = self.log or config.log
    self.partition = self.partition or config.partition
    self.exclude = self.exclude or config.exclude
    self.clusters = self.clusters or config.clusters
    self.qos = self.qos or config.qos
    self.run_script = self.run_script or config.run_script
    self.run_args = self.run_args or config.run_args

  def submit(self):
    submit_list = ['sbatch']
    if self.name: submit_list += ['-J', self.name]
    if self.log: submit_list += ['-o', self.log]
    if self.partition: submit_list += ['-p', self.partition]
    if self.exclude: submit_list += ['-x', self.exclude]
    if self.clusters: submit_list += ['-M', self.clusters]
    if self.qos: submit_list += ['--qos', self.qos]
    submit_list.append(self.run_script)
    if self.run_args:
      ## shlex splits run_args in a Popen digestable way
      if isinstance(self.run_args, str): self.run_args = shlex.split(self.run_args)
      submit_list += self.run_args
    log.debug('({}) Submit job with command {}'.format(self.name, submit_list))
    submit_string = subprocess.check_output(submit_list, universal_newlines = True)
    job_id = int(submit_string.split(' ')[-1].rstrip('\n'))
    self.job_id = job_id

    return job_id

  def cancel(self):
    log.debug('({}) Cancel job'.format(self.name))
    os.system('scancel {}'.format(self.job_id))

  ## TODO: internally already set the exitcode here and just return it in exitcode(self)
  def status(self):
    status_string = self._get_sacct_entry('State')
    status = Status.Running
    # if not (status_string == 'CANCELLED' or status_string == 'COMPLETED' or status_string == 'FAILED' or status_string == 'NODE_FAIL' or status_string == 'BOOT_FAIL' or status == 'NODE_FAIL'): status = Status.Running
    if status_string is not None: status = Status.Finished
      
    return status

  def exitcode(self):
    exitcode = self._get_sacct_entry('ExitCode')

    return exitcode

  def _get_sacct_entry(self, column):
    sacct_list = []
    sacct_list = subprocess.check_output(['sacct', '-j', '{}.batch'.format(self.job_id), '-P', '-o', column], universal_newlines = True).rstrip('\n').split('\n')
    sacct_string = None
    if len(sacct_list) > 1:
      sacct_string = sacct_list[1].strip()
      log.debug('({}) Column "{}" string from sacct: {}'.format(self.name, column, sacct_string))
    
    return sacct_string
    
