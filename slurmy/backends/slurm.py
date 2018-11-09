
import subprocess
import os
import shlex
import logging
from ..tools.defs import Status
from .base import Base
from .defs import bids

log = logging.getLogger('slurmy')


class Slurm(Base):
    """@SLURMY
    Slurm backend class. Inherits from the Base backend class.

    * `name` Name of the parent job.
    * `log` Log file written by slurm.
    * `run_script` The script that is executed on the worker node.
    * `run_args` Run arguments that are passed to the run_script.

    Slurm batch submission arguments (see slurm documentation):

    * `partition` Partition on which the slurm job is running.
    * `exclude` Worker node(s) that should be excluded.
    * `clusters` Cluster(s) in which the slurm job is running.
    * `qos` Additional quality of service setting.
    * `mem` Memory limit for the slurm job.
    * `time` Time limit for the slurm job.
    * `export` Environment exports that are propagated to the slurm job.
    """
    
    bid = bids['SLURM']
    _script_options_identifier = 'SBATCH'
    _commands = ['sbatch', 'scancel', 'squeue', 'sacct']
    _successcode = '0:0'
    _run_states = set(['PENDING', 'RUNNING'])
    
    def __init__(self, name = None, log = None, run_script = None, run_args = None, partition = None, exclude = None, clusters = None, qos = None, mem = None, time = None, export = None):
        super(Slurm, self).__init__()
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

    def submit(self):
        """@SLURMY
        Submit the job to the slurm batch system.

        Returns the job id (int).
        """
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
        ## Get run_script setup through wrapper
        run_script = self.wrapper.get(self.run_script)
        ## shlex splits run_script in a Popen digestable way
        run_script = shlex.split(run_script)
        submit_list += run_script
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
        """@SLURMY
        Cancel the slurm job.
        """
        log.debug('({}) Cancel job'.format(self.name))
        os.system('scancel {}'.format(self._job_id))

    def status(self):
        """@SLURMY
        Get the status of slurm job from sacct entry.

        Returns the job status (Status).
        """
        sacct_return = self._get_sacct_entry('Job,State,ExitCode')
        status = Status.RUNNING
        if sacct_return is not None:
            job_state = sacct_return['finished']
            if job_state not in Slurm._run_states and 'success' in sacct_return:
                status = Status.FINISHED
                self._exitcode = sacct_return['success']

        return status

    def exitcode(self):
        """@SLURMY
        Get the exitcode of slurm job from sacct entry. Evaluation is actually done by Slurm.status(), Slurm.exitcode() only returns the value. If exitcode at this stage is None, execute Slurm.status() beforehand.

        Returns the job exitcode (str).
        """
        ## If exitcode is not set yet, run status evaluation
        if self._exitcode is None:
            self.status()
            
        return self._exitcode

    def _get_sacct_entry(self, column):
        sacct_list = ['sacct']
        if self.partition:
            sacct_list.extend(['-r', self.partition])
        if self.clusters:
            sacct_list.extend(['-M', self.clusters])
        sacct_list.extend(['-j', '{}'.format(self._job_id), '-P', '-o', column])
        sacct_list = subprocess.check_output(sacct_list, universal_newlines = True).rstrip('\n').split('\n')
        log.debug('({}) Return list from sacct: {}'.format(self.name, sacct_list))
        sacct_return = None
        if len(sacct_list) > 1:
            sacct_return = {}
            for entry in sacct_list[1:]:
                job_string, state, exitcode = entry.split('|')
                log.debug('({}) Column "{}" values from sacct: {} {} {}'.format(self.name, column, job_string, state, exitcode))
                if '.batch' in job_string:
                    sacct_return['success'] = exitcode
                else:
                    sacct_return['finished'] = state

        return sacct_return

    @staticmethod
    def get_listen_func(partition = None, clusters = None):
        command = ['sacct']
        if partition:
            command.extend(['-r', partition])
        if clusters:
            command.extend(['-M', clusters])
        user = os.environ['USER']
        command.extend(['-u', user, '-P', '-o', 'JobID,State,ExitCode'])
        ## Define function for Listener
        def listen(results, interval = 1):
            import subprocess, time
            from collections import OrderedDict
            while True:
                result = subprocess.check_output(command, universal_newlines = True).rstrip('\n').split('\n')
                sacct_returns = {}
                job_ids = set()
                ## Evaluate sacct return values
                for res in result:
                    job_id, state, exitcode = res.split('|')
                    if job_id.endswith('.batch'):
                        sacct_returns[job_id] = exitcode
                    else:
                        sacct_returns[job_id] = state
                        job_ids.add(job_id)
                ## Generate results dict
                res_dict = OrderedDict()
                for job_id in job_ids:
                    if sacct_returns[job_id] in Slurm._run_states: continue
                    batch_string = '{}.batch'.format(job_id)
                    if batch_string not in sacct_returns: continue
                    exitcode = sacct_returns[batch_string]
                    res_dict[int(job_id)] = {'status': Status.FINISHED, 'exitcode': exitcode}
                results.put(res_dict)
                time.sleep(interval)

        return listen
