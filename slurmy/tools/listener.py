
import multiprocessing
import glob
import time
from .defs import Status, Mode
import logging

log = logging.getLogger('slurmy')


class Listener(object):
    """@SLURMY
    Listener class which is running in the background and collects state change information of jobs attached to the parent JobHandler instance.

    * `parent` Parent JobHandler instance.
    * `listen_func` The function definition used to collect the state change information. Results are collected in self._results as a dictionary with the keys being the defined map_property of the jobs.
    * `listen_status` The job status the listener will consider.
    * `map_property` Property name of jobs to which the respective job name is mapped to. The choice of the property name is driven by the definition of the listen_func.
    * `max_attempts` Maximum number of attempts that the information collection will be executed.
    * `fail_results` The results the job properties should be set to in case the max_attempts limit is reached.
    """
    def __init__(self, parent, listen_func, listen_status, map_property, max_attempts = None, fail_results = None):
        ## Parent JobHandler
        self._parent = parent
        ## Listener function
        self._listen_func = listen_func
        ## Job status to check
        self._listen_status = listen_status
        ## Max check attempts
        self._max_attempts = max_attempts
        if self._max_attempts is not None:
            self._attempts = {}
        self._fail_results = fail_results or {'status': Status.FAILED}
        ## Results handle
        self._results = multiprocessing.Queue()
        ## Process pointer
        self._process = None
        ## Mapping property
        self._map_property = map_property

    def start(self, interval = 1):
        """@SLURMY
        Spawn subprocess which continuously collects information by configurable mechanism and match any updates in the output to a state change decision of jobs.

        * `interval` Interval at which information is collected by subprocess.
        """
        log.debug('(Listener {}) Start listening'.format(self._listen_status.name))
        args = (self._results, interval)
        self._process = multiprocessing.Process(target = self._listen_func, args = args)
        self._process.start()

    def update_jobs(self):
        """@SLURMY
        Update jobs associated to parent JobHandler with the collected information.
        """
        log.debug('(Listener {}) Update jobs'.format(self._listen_status.name))
        results = self._results.get()
        if self._parent._debug:
            from pprint import pprint
            ## Print the last 10 entries of the results OrderedDict
            pprint(list(results.items())[-10:])
        for job in self._parent.jobs.values():
            ## If job is not in status which the listener should consider, skip
            if job.status != self._listen_status: continue
            ## If job is in ACTIVE mode, skip
            if job.mode == Mode.ACTIVE: continue
            ## Get result key relevant for this job
            key = getattr(job, self._map_property)
            ## Count attempt, if required
            if self._max_attempts is not None:
                if key not in self._attempts: self._attempts[key] = 0
                self._attempts[key] += 1
                log.debug('(Listener {}) Job "{}" is now at {} attempts'.format(self._listen_status.name, job.name, self._attempts[key]))
            update_dict = None
            if key in results:
                ## If key is in results, set update_dict to results
                log.debug('(Listener {}) Found results for job "{}"'.format(self._listen_status.name, job.name))
                update_dict = results[key]
            elif (self._max_attempts is not None) and (self._attempts[key] >= self._max_attempts):
                ## Else if maximum number of attempts is reached, set update_dict to fail results
                log.debug('(Listener {}) Job "{}" reached maximum amount of attempts, setting fail results'.format(self._listen_status.name, job.name))
                update_dict = self._fail_results
            ## If we have results, update job properties
            if update_dict is not None:
                for up_key, up_val in update_dict.items():
                    log.debug('(Listener {}) Update {} of job "{}" to {}'.format(self._listen_status.name, up_key, job.name, up_val))
                    setattr(job, up_key, up_val)

    def stop(self):
        """@SLURMY
        Stop listening subprocess.
        """
        log.debug('(Listener {}) Stop listening'.format(self._listen_status.name))
        self._process.terminate()
