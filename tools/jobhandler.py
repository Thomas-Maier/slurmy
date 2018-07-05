
from __future__ import print_function
import os
import time
from sys import stdout, version_info
from collections import OrderedDict
import pickle
import logging
from .defs import Status, Type, Theme, Mode
from .job import Job, JobConfig
from .namegenerator import NameGenerator
from . import options
from ..backends.utils import get_backend
from .parser import Parser
from .utils import SuccessTrigger, FinishedTrigger, get_input_func, set_update_properties, make_dir, remove_content
from .jobcontainer import JobContainer
from .utils import update_decorator
from .listener import Listener

log = logging.getLogger('slurmy')
        

class JobHandlerConfig(object):
    """@SLURMY
    Config class for the JobHandler class. Stores all necessary information to load the JobHandler session at a later time. All properties are assigned with a custom getter function, which keeps track of updates to the respective property (tracked with the "update" variable).

    Arguments: see JobHandler class.
    """
    
    ## Properties for which custom getter/setter will be defined (without prepending "_") which incorporate the update tagging
    _properties = ['_name_gen', '_name', '_script_dir', '_log_dir', '_output_dir', '_snapshot_dir', '_tmp_dir', '_path',
                   '_success_func', '_finished_func', '_verbosity', '_local_max', '_max_retries', '_run_max', '_backend', '_do_snapshot',
                   '_wrapper', '_job_config_paths', '_listens', '_output_max_attempts']
    
    def __init__(self, name = None, backend = None, work_dir = '', local_max = 0, verbosity = 1, success_func = None, finished_func = None, max_retries = 0, theme = Theme.Lovecraft, run_max = None, do_snapshot = True, wrapper = None, listens = True, output_max_attempts = 5):
        ## Static variables
        self._name_gen = NameGenerator(name = name, theme = theme)
        self._name = self._name_gen.name
        ## Get directory paths
        self.dirs = JobHandlerConfig.get_dirs(self._name, work_dir)
        ## Pop of path to snapshot
        self._path = self.dirs.pop(-1)
        ## Explicitly set directory properties
        self._script_dir, self._log_dir, self._output_dir, self._snapshot_dir, self._tmp_dir = self.dirs
        self._success_func = success_func
        self._finished_func = finished_func
        self._verbosity = verbosity
        self._local_max = local_max
        self._max_retries = max_retries
        self._run_max = run_max
        self._backend = backend
        self._do_snapshot = do_snapshot
        self._wrapper = wrapper
        self._listens = listens
        self._output_max_attempts = output_max_attempts
        ## Dynamic variables
        self._job_config_paths = []

    def __getitem__(self, key):
        return self.__dict__[key]

    @update_decorator
    def add_job_path(self, job_path):
        self.job_config_paths.append(job_path)

    @staticmethod
    def get_dirs(name, work_dir, script = 'scripts', log = 'logs', output = 'output', snapshot = 'snapshot', tmp = 'tmp', snapshot_name = 'JobHandlerConfig.pkl'):
        base_dir = name
        if work_dir: base_dir = os.path.join(work_dir, base_dir)
        ## Convert to absolute path, if it not already the case
        base_dir = os.path.abspath(base_dir)
        ## Sanity check
        if base_dir == '/':
            log.error('Base dir is "/", something went wrong!')
            raise Exception()
        script_dir = os.path.join(base_dir, script)
        log_dir = os.path.join(base_dir, log)
        output_dir = os.path.join(base_dir, output)
        snapshot_dir = os.path.join(base_dir, snapshot)
        tmp_dir = os.path.join(base_dir, tmp)
        path = os.path.join(snapshot_dir, snapshot_name)
        

        return [script_dir, log_dir, output_dir, snapshot_dir, tmp_dir, path]
    
## Set properties to incorporate update tagging
set_update_properties(JobHandlerConfig)


class JobHandler(object):
    """@SLURMY
    Main handle to setup and submit jobs. Internally stores most information in the JobHandlerConfig class, which is stored on disk as a snapshot of the JobHandler session.

    * `name` Name of the JobHandler. Defines the base directory name of the session.
    * `backend` Default backend instance used for the job setup.
    * `work_dir` Path where the base directory is created.
    * `local_max` Maximum number of local jobs that will be submitted at a time.
    * `verbosity` Verbosity of the shell output.
    * `success_func` Default success function used for the job setup.
    * `finished_func` Default finished function used for the job setup.
    * `max_retries` Maximum number of retries that are attempted for failing jobs.
    * `theme` Naming theme used to name the jobhandler and jobs.
    * `run_max` Maximum number of jobs that are submitted at a time.
    * `do_snapshot` Turn on/off snapshot creation. This is needed to load jobhandler instances in interactive slurmy.
    * `use_snapshot` Load snapshot from disk instead of creating new jobhandler.
    * `description` Description of jobhandler that is stored in the bookkeeping.
    * `wrapper` Default run script wrapper used for the job setup.
    * `profiler` Profiler to be used for profiling.
    """
    
    def __init__(self, name = None, backend = None, work_dir = '', local_max = 0, verbosity = 1, success_func = None, finished_func = None, max_retries = 0, theme = Theme.Lovecraft, run_max = None, do_snapshot = True, use_snapshot = False, description = None, wrapper = None, profiler = None, listens = True, output_max_attempts = 5):
        ## Set debug mode
        self._debug = False
        if log.level == 10: self._debug = True
        ## Local jobs not supported in python 2
        if local_max > 0 and version_info.major == 2:
            log.warning('Local job processing not supported in python 2, switched off')
            local_max = 0
        ## Variables that are not picklable
        self.jobs = JobContainer()
        ## Snapshot loading
        if use_snapshot:
            if not name:
                log.error('Cannot use snapshot without a name')
                raise Exception()
            path = JobHandlerConfig.get_dirs(name, work_dir)[-1]
            if not os.path.isfile(path):
                log.error('Could not find path to snapshot')
                raise Exception()
            log.debug('Load JobHandler snapshot from {}'.format(path))
            with open(path, 'rb') as in_file:
                self.config = pickle.load(in_file)
            log.debug('Load job snapshots')
            for job_config_path in self.config.job_config_paths:
                with open(job_config_path, 'rb') as in_file:
                    job_config = pickle.load(in_file)
                self._add_job_with_config(job_config)
        else:
            ## Backend setup
            if backend is None and options.Main.backend is not None:
                backend = get_backend(options.Main.backend)
            ## Set default backend configuration
            backend.load_default_config()
            ## Make new JobHandler config
            self.config = JobHandlerConfig(name = name, backend = backend, work_dir = work_dir, local_max = local_max, verbosity = verbosity, success_func = success_func, finished_func = finished_func, max_retries = max_retries, theme = theme, run_max = run_max, do_snapshot = do_snapshot, wrapper = wrapper, listens = listens, output_max_attempts = output_max_attempts)
            self.reset(skip_jobs = True)
            ## Add this session to the slurmy bookkeeping only if snapshot making is activated
            if do_snapshot:
                JobHandler._add_bookkeeping(self.config.name, work_dir, description)
        ## Variable parser
        self._parser = Parser(self.config)
        ## Set profiler
        self._profiler = profiler

    def __getitem__(self, key):
        return self.jobs[key]

    def __repr__(self):
        return self.config.name

    def reset(self, skip_jobs = False):
        """@SLURMY
        Reset the JobHandler session.

        * `skip_jobs` Skip job reset.
        """
        log.debug('Reset JobHandler')
        ## Make folders if it doesn't exist yet
        for folder in self.config.dirs:
            make_dir(folder)
        ## Remove logs
        remove_content(self.config.log_dir)
        ## Remove remaining tmp files
        remove_content(self.config.tmp_dir)
        ## Remove outputs
        remove_content(self.config.output_dir)
        if not skip_jobs:
            ## Reset jobs
            for job in self.jobs.values():
                job.reset()
            ## Reset job states bookkeeping:
            for status in self.jobs._states:
                self.jobs._states[status].clear()
        ## Make snapshots
        self.update_snapshot()

    def update_snapshot(self, skip_jobs = False):
        """@SLURMY
        Update snapshots of the JobHandler and the associated Jobs on disk. Snaphots are only updated if something changed in the respective JobHandlerConfig or JobConfig.

        * `skip_jobs` Skip the job snapshot update.
        """
        ## If snapshotting is deactivated, do nothing
        if not self.config.do_snapshot: return
        if not skip_jobs:
            log.debug('Update job snapshots')
            for job in self.jobs.values():
                job.update_snapshot()
        ## If JobHandler config is not tagged for an update, do nothing
        if not self.config.update:
            log.debug('No changes made, skip JobHandler snapshot update')
            return
        log.debug('Update JobHandler snapshot')
        with open(self.config.path, 'wb') as out_file:
            pickle.dump(self.config, out_file)
        ## Reset update flag
        self.config.update = False

    def _add_job_with_config(self, job_config):
        log.debug('Add job {}'.format(job_config.name))
        job = Job(config = job_config)
        self.jobs[job.name] = job
        tags = job_config.tags
        if tags is not None:
            if isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set):
                for tag in tags:
                    if tag not in self.jobs._tags: self.jobs._tags[tag] = []
                    self.jobs._tags[tag].append(job)
            else:
                if tags not in self.jobs._tags: self.jobs._tags[tags] = []
                self.jobs._tags[tags].append(job)
        ## Ensure that a first snapshot is made
        if self.config.do_snapshot: job.update_snapshot()
        ## If job is a batch job, store job id if it already has one
        if job.type == Type.BATCH and job.id is not None:
            self.jobs.add_id(job.id, job.name)

        return job

    def add_job(self, backend = None, run_script = None, run_args = None, success_func = None, finished_func = None, post_func = None, max_retries = None, output = None, tags = None, parent_tags = None, name = None, job_type = Type.BATCH):
        """@SLURMY
        Add a job to the list of jobs to be processed by the JobHandler.

        * `backend` Backend instance to be used by the job.
        * `run_script` The run script processed by the job. This can be a string specifying the content of the script or a the absolute path to an already existing script file.
        * `run_args` The arguments passed to the run script.
        * `success_func` Success function used for the job setup.
        * `finished_func` Finished function used for the job setup.
        * `post_func` Post execution function used for the job setup.
        * `max_retries` Maximum number of retries that are attempted when job is failing.
        * `output` Output file of the job. This **must** be an absolute path.
        * `tags` List of tags attached to the job.
        * `parent_tags` List of parent tags attached to the job.
        * `name` Name of the job. This must be a string that conforms with the restrictions on class property names. Slurmy will make sure that job names stay unique, even if the same job name is set multiple times.
        * `job_type` Type of the job. Can be set to Type.LOCAL to make it a local processing job.

        Returns the job (Job).
        """
        ##TODO: rethink how this should be handled
        # ## If job type is LOCAL but maximum number of local jobs is 0, set to 1
        # if job_type == Type.LOCAL and self.config.local_max == 0:
        #     log.warning('Job is created as Type.LOCAL but local_max is set to 0. Setting local_max to 1.')
        #     self.config.local_max = 1
        if backend is None and options.Main.backend is not None:
            backend = get_backend(options.Main.backend)
        if backend is None:
            log.error('No backend set for job, either set directly or define default in ~/.slurmy')
            return
        ## Set run_script and run_args if not already done
        backend.run_script = backend.run_script or run_script
        backend.run_args = backend.run_args or run_args
        ## Set wrapper if defined
        if self.config.wrapper:
            backend.wrapper = self.config.wrapper
        ## Get job name
        name = self.config.name_gen.next(name)
        backend.name = name
        ## Set and evaluate job label
        job_label = {Status.FINISHED: None, Status.SUCCESS: None}
        for status in job_label:
            backend.run_script, job_label[status] = self._parser.set_status_label(backend.run_script, name, status)
        label_finished_func = None
        label_success_func = None
        if job_label[Status.FINISHED] is not None:
            label_finished_func = FinishedTrigger(job_label[Status.FINISHED])
        ##TODO: this needs examples in the documentation
        if job_label[Status.SUCCESS] is not None:
            if output is None:
                ## Set output if none is defined
                output = job_label[Status.SUCCESS]
            else:
                ## Else set success_func
                label_success_func = SuccessTrigger(job_label[Status.SUCCESS], self.config.output_max_attempts)
        job_finished_func = finished_func or label_finished_func or self.config.finished_func
        job_success_func = success_func or label_success_func or self.config.success_func
        ## Parse variables
        backend.run_script = self._parser.replace(backend.run_script)
        if output: output = self._parser.replace(output)
        backend.write_script(self.config.script_dir)
        backend.log = os.path.join(self.config.log_dir, name)
        backend.sync(self.config.backend)
        job_max_retries = max_retries or self.config.max_retries
        config_path = os.path.join(self.config.snapshot_dir, name+'.pkl')

        job_config = JobConfig(backend, path = config_path, success_func = job_success_func, finished_func = job_finished_func, post_func = post_func, max_retries = job_max_retries, job_type = job_type, output = output, tags = tags, parent_tags = parent_tags)
        ## Set modes
        ### If JobHandler listens, set the mode for RUNNING to PASSIVE by default
        if self.config.listens:
            job_config.set_mode(Status.RUNNING, Mode.PASSIVE)
        ### If we have a custom finished_func, set the mode for RUNNING to ACTIVE
        if job_finished_func:
            job_config.set_mode(Status.RUNNING, Mode.ACTIVE)
        ### If we have an output file, but no custom success_function, set the mode for FINISHED to PASSIVE
        if output and not job_success_func:
            job_config.set_mode(Status.FINISHED, Mode.PASSIVE)
        ## Add job config snapshot path to list in JobHandlerConfig
        self.config.add_job_path(config_path)
        ## Update snapshot to make sure job config paths list is properly updated
        self.update_snapshot(skip_jobs = True)

        return self._add_job_with_config(job_config)

    def _job_ready(self, job):
        """@SLURMY
        Check if job is ready to be submitted. Checks if all associated parent jobs are finished and in status SUCCESS. For local job, checks if local job queue is full.

        * `job` Job to be checked.

        Returns if the job is ready or not (bool).
        """
        ## Check if parent jobs are finished
        parent_tags = job.parent_tags
        if not parent_tags:
            return True
        for tag in parent_tags:
            if tag not in self.jobs._tags:
                log.error('Parent tag is not registered in jobs list!')
                continue
            for tagged_job in self.jobs._tags[tag]:
                status = tagged_job.get_status()
                if status == Status.SUCCESS: continue
                ## If a parent job is unrecoverably failed/cancelled, cancel this job as well
                if (status == Status.FAILED or status == Status.CANCELLED) and not tagged_job._do_retry(): job.cancel(clear_retry = True)
                return False
        ## Check if local job queue is full
        if job.type == Type.LOCAL:
            if len(self.jobs._local) >= self.config.local_max:
                return False

        return True

    def _get_print_string(self):
        print_string = 'Jobs '
        if self.config.verbosity > 1:
            n_running = len(self.jobs._states[Status.RUNNING])
            n_local = len(self.jobs._local)
            n_batch = n_running - n_local
            print_string += 'running (batch/local/all): ({}/{}/{}); '.format(n_batch, n_local, n_running)
        n_success = len(self.jobs._states[Status.SUCCESS])
        n_failed = len(self.jobs._states[Status.FAILED])
        n_all = len(self.jobs)
        print_string += '(success/fail/all): ({}/{}/{})'.format(n_success, n_failed, n_all)

        return print_string

    def _get_summary_string(self, time_spent = None):
        n_jobs = len(self.jobs)
        n_local = len(self.jobs._tags[Type.LOCAL])
        n_batch = n_jobs - n_local
        summary_dict = OrderedDict()
        summary_dict['all'] = {'string': 'Jobs processed ', 'batch': n_batch, 'local': n_local}
        summary_dict['success'] = {'string': '     successful ', 'batch': 0, 'local': 0}
        summary_dict['fail'] = {'string': '     failed ', 'batch': 0, 'local': 0}
        jobs_failed = ''
        for job in self.jobs.values():
            status = job.get_status()
            if status == Status.SUCCESS:
                if job.type == Type.LOCAL:
                    summary_dict['success']['local'] += 1
                else:
                    summary_dict['success']['batch'] += 1
            elif status == Status.FAILED or status == Status.CANCELLED:
                jobs_failed += '{} '.format(job.name)
                if job.type == Type.LOCAL:
                    summary_dict['fail']['local'] += 1
                else:
                    summary_dict['fail']['batch'] += 1

        print_string = ''
        for key, summary_val in summary_dict.items():
            if key == 'fail' and not jobs_failed: continue
            n_batch = summary_val['batch']
            n_local = summary_val['local']
            n_all = summary_val['batch'] + summary_val['local']
            print_string += '{}(batch/local/all): ({}/{}/{})\n'.format(summary_val['string'], n_batch, n_local, n_all)
        if self.config.verbosity > 1 and jobs_failed:
            print_string += 'Failed jobs: {}\n'.format(jobs_failed)
        if time_spent:
            print_string += 'Time spent: {:.1f} s'.format(time_spent)

        return print_string

    def _wait_for_jobs(self, tags = None):
        for job in self.jobs.get(tags):
            if job.type != Type.LOCAL: continue
            log.debug('Wait for job {}'.format(job.name))
            job.wait()

    def print_summary(self, time_spent = None):
        """@SLURMY
        Print a summary of the job processing.
        """
        print_string = self._get_summary_string(time_spent)
        stdout.write('\r'+print_string)
        stdout.write('\n')

    def _setup_listeners(self):
        """@SLURMY
        Prepare Listeners.
        """
        listeners = []
        ## If JobHandler doesn't listen, return empty list
        if not self.config.listens:
            return listeners
        ## Set up backend specific FINISHED listeners (for now only SLURMY). TODO: dynamically assert which backends are used (one listener for each?)
        ## If we are in test mode (aka local mode), don't add batch listeners
        if not options.Main.test_mode:
            from ..backends.slurm import Slurm
            ## This one also sets the exitcode of the job, so the success evaluation can be done by itself.
            listen_slurm = Slurm.get_listen_func()
            listener_slurm = Listener(self, listen_slurm, Status.RUNNING, 'id')
            listeners.append(listener_slurm)
        ## Get list of defined output files
        file_list = [l.output for l in self.jobs.values() if l.output is not None]
        ## Set up output file listener, if any are defined
        if file_list:
            from .utils import get_listen_files
            ### Get list of associated folders
            folder_list = set([f.rsplit('/', 1)[0] for f in file_list])
            listen_success = get_listen_files(file_list, folder_list, Status.SUCCESS)
            listener_success = Listener(self, listen_success, Status.FINISHED, 'output', max_attempts = self.config.output_max_attempts, fail_results = {'status': Status.FAILED})
            listeners.append(listener_success)

        return listeners

    def run_jobs(self, interval = 1, retry = False):
        """@SLURMY
        Run the job submission routine. Jobs will be submitted continuously until all of them have been processed.

        * `interval` The interval at which the job submission will be done (in seconds). Can also be set to -1 to start every submission cycle manually.
        * `retry` Retry jobs in status FAILED or CANCELLED. This will attempt one cycle of job retrying.
        """
        ## If a profiler is set, start profiling
        if self._profiler is not None:
            self._profiler.start()
        ## Prepare listeners
        listeners = self._setup_listeners()
        time_now = time.time()
        try:
            ## Start listeners
            for listener in listeners:
                listener.start()
            ## If retry is set to True, for the relevant jobs (FAILED and CANCELLED) set maximum number of retries to 1 and number of attempted retries to 0
            ## This will trigger the automatic retry routine for these jobs
            if retry:
                job_states = set([Status.FAILED, Status.CANCELLED])
                self.set_jobs_config_attr('max_retries', 1, states = job_states)
                self.set_jobs_config_attr('n_retries', 0, states = job_states)
            n_all = len(self.jobs)
            running = True
            ## Initial printout to avoid empty line until first cycle of submits is done
            if self.config.verbosity > 0:
                stdout.write('\r'+self._get_print_string())
                stdout.flush()
            while running:
                ## Update jobs with listeners
                for listener in listeners:
                    listener.update_jobs()
                self.submit_jobs(wait = False)
                print_string = self._get_print_string()
                if interval == -1: print_string += ' - press enter to update status'
                n_success = len(self.jobs._states[Status.SUCCESS])
                n_failed = len(self.jobs._states[Status.FAILED])
                n_cancelled = len(self.jobs._states[Status.CANCELLED])
                if (n_success+n_failed+n_cancelled) == n_all:
                    running = False
                else:
                    if not self._debug:
                        if self.config.verbosity > 0:
                            stdout.write('\r'+print_string)
                            stdout.flush()
                    else:
                        log.debug(print_string)
                    if interval == -1:
                        get_input_func()()
                    else:
                        time.sleep(interval)
        except KeyboardInterrupt:
            if not self._debug: stdout.write('\n')
            log.warning('Quitting gracefully...')
            try:
                log.warning('Waiting for local jobs, ctrl+c again to cancel them...')
                self._wait_for_jobs()
            except KeyboardInterrupt:
                log.warning('Cancel local jobs...')
                ## Need to cancel cleanly, since jobs are setup to ignore signals to parent process
                self.cancel_jobs(only_local = True, make_snapshot = False)
        except:
            ## If something explodes, cancel all running jobs
            self.cancel_jobs(make_snapshot = False)
            raise
        finally:
            ## If retry is set to True, set maximum number of retries of all jobs to the JobHandler configuration again
            if retry:
                self.set_jobs_config_attr('max_retries', self.config.max_retries)
            ## Stop listeners
            for listener in listeners:
                listener.stop()
            ## Final snapshot
            self.update_snapshot()
            time_now = time.time() - time_now
            ## Print final summary
            if not self._debug:
                if self.config.verbosity > 0:
                    self.print_summary(time_now)
            ## If profiler is set, print profiling result
            if self._profiler is not None:
                self._profiler.stop()

    def submit_jobs(self, tags = None, make_snapshot = True, wait = True, retry = False, skip_eval = False):
        """@SLURMY
        Submit jobs according to the JobHandler configuration.

        * `tags` Tags of jobs that will be submitted.
        * `make_snapshot` Make a snapshot of the jobs and the JobHandler after the submission cycle.
        * `wait` Wait for locally submitted job.
        * `retry` Retry jobs in status FAILED or CANCELLED. This circumvents the automatic retry routine.
        * `skip_eval` Skip job status evaluation everywhere.
        """
        try:
            for job in self.jobs.get(tags):
                ## Check job status and tags
                self._check_job(job)
                ## Check local job status, skip status evaluation since this was already done
                self._check_local_job(job, skip_eval = True)
                ## Submit new jobs only if current number of running jobs is below maximum, if set
                if self.config.run_max and not (len(self.jobs._states[Status.RUNNING]) < self.config.run_max):
                    log.debug('Maximum number of running jobs reached, skip job submission')
                    break
                ## Current job status
                status = job.status
                ## If jobs are in FAILED or CANCELLED state, do retry routine. Ignore maximum number of retries if requested.
                if (status == Status.FAILED or status == Status.CANCELLED):
                    status = job._retry(submit = False, ignore_max_retries = retry)
                ## If job is not in Configured state there is nothing to do
                if status != Status.CONFIGURED: continue
                ## Check if job is ready to be submitted
                if not self._job_ready(job): continue
                ## Dynamically set job type to LOCAL, if local job queue is not full
                if len(self.jobs._local) < self.config.local_max:
                    job.type = Type.LOCAL
                ## If job is type LOCAL, add job name to list of currently running local jobs
                if job.type == Type.LOCAL:
                    self.jobs._local.add(job.name)
                ## Submit the job
                status = job.submit()
                ### If job is a batch job, store the job id with job name
                if job.type == Type.BATCH:
                    self.jobs.add_id(job.id, job.name)
                ## Check job status and tags again, skip status evaluation since this was already done
                self._check_job(job, skip_eval = True)
            if wait: self._wait_for_jobs(tags)
            ## Make JobHandler snapshot update, skip jobs since we already did them
            if make_snapshot: self.update_snapshot()
        ## In case of a keyboard interrupt we just want to stop slurmy processing but keep current batch jobs running
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        ## If anything else happens, cancel all running jobs
        except:
            self.cancel_jobs(make_snapshot = False)
            raise

    def cancel_jobs(self, tags = None, only_local = False, only_batch = False, make_snapshot = True):
        """@SLURMY
        Cancel running jobs.

        * `tags` Tags of jobs that will be cancelled.
        * `only_local` Cancel only local jobs.
        * `only_batch` Cancel only batch jobs.
        * `make_snapshot` Make a snapshot after cancelling jobs.
        """
        for job in self.jobs.get(tags):
            ## Nothing to do when job is not in Running state
            if job.get_status() != Status.RUNNING: continue
            if only_local and job.type != Type.LOCAL: continue
            if only_batch and job.type == Type.LOCAL: continue
            job.cancel()
        if make_snapshot: self.update_snapshot()

    def check(self, force_success_check = False, skip_eval = False, print_summary = True):
        """@SLURMY
        Check the status and tags of the jobs.

        * `force_success_check` Force the success routine to be run, even if the job is already in a post-finished state.
        * `print_summary` Print the job processing summary.
        """
        for job in self.jobs.values():
            self._check_job(job, force_success_check = force_success_check, skip_eval = skip_eval)
        if print_summary:
            print_string = self._get_print_string()
            print (print_string)

    def _check_job(self, job, force_success_check = False, skip_eval = False):
        ## Update job status
        self.jobs._update_job_status(job, force_success_check = force_success_check, skip_eval = skip_eval)
        ## Update job tags (keeping track of local jobs)
        self.jobs._update_tags(job)

    def _check_local_jobs(self, skip_eval = False):
        for job_name in self.jobs._local:
            job = self[job_name]
            self._check_local_job(job, skip_eval = skip_eval)

    def _check_local_job(self, job, skip_eval = False):
        job_type = job.type
        ## If job is not type LOCAL, nothing to do
        if job_type != Type.LOCAL: return
        name = job.name
        ## If job name is not in the list of currently running local jobs, nothing to do
        if name not in self.jobs._local: return
        status = job.get_status(skip_eval = skip_eval)
        ## If job is still running, nothing to do
        if status == Status.RUNNING: return
        ## Remove job from list of currently running local jobs
        self.jobs._local.remove(name)

    def set_jobs_config_attr(self, attr, val, tags = None, states = None):
        """@SLURMY
        Set the job config attribute of jobs associated to the JobHandler.

        * `attr` Name of the attribute which is set.
        * `val` Value that the attribute is set to.
        * `tags` Set of tags which the jobs have to match to.
        * `states` Set of job states which the jobs have to match to.
        """
        for job in self.jobs.get(tags = tags, states = states):
            setattr(job.config, attr, val)

    @staticmethod
    def _add_bookkeeping(name, folder, description = None):
        pwd = os.environ['PWD']
        work_dir = folder
        if not work_dir.startswith('/'): work_dir = os.path.join(pwd, work_dir)
        options.Main.add_bookkeeping(name, work_dir, description)
