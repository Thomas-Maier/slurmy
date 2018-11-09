import subprocess
import os
import shlex
import logging
from ..tools.defs import Status
from .base import Base
from .defs import bids
from ..tools.utils import make_dir, find_between
log = logging.getLogger('slurmy')


class HTCondor(Base):
    """@SLURMY
    HTCondor backend class. Inherits from the Base backend class.

    * `name` Name of the parent job.
    * `log` Output, Error, and Log files written by htcondor.
    * `run_script` The script that is executed on the worker node.
    * `run_args` Run arguments that are passed to the run_script.

    HTCondor batch submission arguments (see slurm documentation):

    * `mem` Memory limit for the slurm job.
    * `time` Time limit for the slurm job.
    * `export` Environment exports that are propagated to the slurm job.
    """
    
    bid = bids['HTCONDOR']
    _commands = ['condor_submit', 'condor_rm', 'condor_history', 'condor_q']
    _successcode = '0'
    _run_states = set([1, 2])  # 1: IDLE, 2: RUNNING
    
    def __init__(self, name = None, log = None, run_script = None, run_args = None, mem = None, time = None, export = None):
        super(HTCondor, self).__init__()
        ## Common backend options
        self.name = name
        self.log = log
        self.run_script = run_script
        self.run_args = run_args
        ## Batch options
        self.mem = mem
        self.time = time
        self.export = export
        ## Internal variables
        self._job_id = {}
        self._exitcode = None


    def _write_submissionfile(self, script_folder):
        """@SLURMY
        Write submission file required for HTCondor to disk.

        Returns the path to the submission file
        """
        submissionfile_path = os.path.join(script_folder, "{job}.sub".format(job=self.name))

        log.debug('({}) Writing submission file to {}'.format(self.name, script_folder))
        with open(submissionfile_path, 'w') as f:
            f.write("""universe                = vanilla
executable              = {executable}
output                  = {logdir}/{name}.$(ClusterId).$(Process).out
error                   = {logdir}/{name}.$(ClusterId).$(Process).err
log                     = {logdir}/{name}.$(ClusterId).$(Process).log

transfer_executable     = True

request_cpus            = {nproc}
{runtime}
{memory}

queue
            """.format(
                    executable=self.wrapper.get(self.run_script),  # Get run_script setup through wrapper
                    logdir=os.path.abspath(os.path.join(script_folder, os.pardir, 'logs')),
                    name=self.name,
                    nproc="1",
                    runtime="+RequestRuntime         = {runtime}".format(runtime=self.time) if self.time else "",
                    memory="RequestMemory           = {memory}".format(memory=self.mem) if self.mem else ""
                ))
        return submissionfile_path


    def write_script(self, script_folder):
        """@SLURMY
        Write the run_script according to configuration.
        Do everything that is done in base class and in addition add HTCondor submission file

        * `script_folder` Folder to store the script file in.
        """
        super(HTCondor, self).write_script(script_folder)
        submission_file = self._write_submissionfile(script_folder)


    def submit(self):
        """@SLURMY
        Submit the job to the HTCondor batch system.
        Adds the job id (int) and the absolute path to the log file to this class
        Returns the job id (int).
        """
        submit_list = ['condor_submit', '-verbose']

        ## shlex splits run_script in a Popen digestable way
        submissionfile = self.run_script + '.sub'
        submissionfile = shlex.split(submissionfile)
        submit_list += submissionfile

        if self.run_args:
            log.info('({}) Run arguments are not yet supported. Won\'t consider {}'.format(self.name, self.run_args))
            
        log.debug('({}) Submit job with command {}'.format(self.name, submit_list))
        submit_string = subprocess.check_output(submit_list, universal_newlines = True)
        job_id = find_between(submit_string, '** Proc ', ':')
        job_log = find_between(submit_string, 'UserLog = "', '"')
        self._job_id[job_id] = job_log
        return job_id

    def cancel(self):
        """@SLURMY
        Cancel the slurm job.
        """
        log.debug('({}) Cancel job'.format(self.name))
        os.system('condor_rm {}'.format(" ".join(self._job_id.keys())))


    def _get_job_info(self):
        """ @SLURMY
        Get information about job from log file.
        By using local log files to get information about job status, the load on the HTCondor schedd is reduced.
        Information about job status can be found here: http://pages.cs.wisc.edu/~adesmet/status.html

        """
        command = ['condor_history']
        command.extend(['-autoformat', 'ClusterId', 'JobStatus', 'ExitCode'])
        command.extend(['-userlog', ''])  # path to user log needs to be swapped
        for jobid, logpath in self._job_id.items():
            command[-1] = logpath
            condor_history_list = subprocess.check_output(command, universal_newlines = True).rstrip('\n').split('\n')
            log.debug('({}) Return list for job id {} from condor_history: {}'.format(self.name, jobid, condor_history_list))
            condor_history_return = None
            if len(condor_history_list) > 0:
                condor_history_return = {}
                for entry in condor_history_list:
                    job_id, state, exitcode = entry.split()
                    log.debug('({}) Values from condor_history: {} {} {}'.format(self.name, job_id, state, exitcode))
                    condor_history_return['finished'] = state
                    if exitcode != 'undefined':
                        condor_history_return['success'] = exitcode
                    elif state in ('3', '5', '6') :  # state 3: job removed, state 5: job help, state 6: submission error
                        condor_history_return['success'] = 1

        return condor_history_return

    def status(self):
        """@SLURMY
        Get the status of slurm job from htcondor job log file (to reduce load on scheduler).

        Returns the job status (Status).
        """
        jobinfo = self._get_job_info()

        status = Status.RUNNING
        if jobinfo is not None:
            job_state = jobinfo['finished']
            if job_state not in HTCondor._run_states and 'success' in jobinfo:
                status = Status.FINISHED
                self._exitcode = jobinfo['success']

        return status

    def exitcode(self):
        """@SLURMY
        Get the exitcode of slurm job from htcondor job log file. Evaluation is actually done by HTCondor.status(), HTCondor.exitcode() only returns the value. If exitcode at this stage is None, execute HTCondor.status() beforehand.

        Returns the job exitcode (str).
        """
        ## If exitcode is not set yet, run status evaluation
        if self._exitcode is None:
            self.status()
            
        return self._exitcode

    @staticmethod
    def get_listen_func():
        """@SLURMY
        Listener function, will be added to listener instance.
        Limited functionality, updating of jobs not fully functional at the moment.

        It is recommended to use a "non-listening" JobHandler when using HTCondor.
        Example how to set up a job handler for HTCondor: jh = JobHandler(backend=HTCondor(), listens=False)

        Returns listen function.
        """

        command = ['condor_q']
        user = os.environ['USER']
        command.extend(['-autoformat', 'ClusterId', 'JobStatus', '-constraint', 'owner == "{}"'.format(user)])
        ## Define function for Listener
        def listen(results, interval = 1):
            import subprocess, time
            from collections import OrderedDict
            job_ids = set()
            while True:
                result = subprocess.check_output(command, universal_newlines = True).rstrip('\n').split('\n')
                unfinished_job_ids = set()
                for res in result:
                    if not res: continue
                    job_id, state = res.split()
                    print(job_id, state)
                    job_ids.add(job_id)
                    unfinished_job_ids.add(job_id)
                ## Generate results dict
                res_dict = OrderedDict()
                for job_id in job_ids:
                    if job_id not in unfinished_job_ids:
                        exitcode_cmd = ['condor_history', '-autoformat', 'ExitCode', '-constraint', 'ClusterId == {}'.format(job_id)]
                        exitcode = subprocess.check_output(exitcode_cmd, universal_newlines = True).rstrip('\n')
                        res_dict[int(job_id)] = {'status': Status.FINISHED, 'exitcode': int(exitcode)}
                results.put(res_dict)
                time.sleep(interval)

        return listen
