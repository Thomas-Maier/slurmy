
import subprocess as sp
import multiprocessing as mp
import glob
import time
from .defs import Status, Mode
import logging

log = logging.getLogger('slurmy')


##TODO: check if a "signaler" module already exists for python
class Listener(object):
    """@SLURMY
    Listener class which is running in the background and collects state change information of jobs attached to the parent JobHandler instance.

    * `parent` Parent JobHandler instance.
    * `listen_func` The function definition used to collect the state change information. Results are collected in self._results as a dictionary with the keys being the defined map_property of the jobs.
    * `listen_status` The job status the listener will consider.
    * `map_property` Property name of jobs to which the respective job name is mapped to. The choice of the property name is driven by the definition of the listen_func.
    """
    def __init__(self, parent, listen_func, listen_status, map_property = None):
        ## Parent JobHandler
        self._parent = parent
        ## Listener function
        self._listen_func = listen_func
        ## Job status to check
        self._listen_status = listen_status
        ## Results handle
        self._results = mp.Queue()
        ## Process pointer
        self._process = None
        ## Mapping dictionary
        self._map = {}
        ## Fill mapping dictionary, if a mapping job property was defined
        ## If no mapping property was set, get job identification from jobcontainer
        if map_property is not None:
            for job in self._parent.jobs.values():
                job_prop = getattr(job, map_property)
                ## Set entry only if property value is something sensible
                if job_prop:
                    self._map[job_prop] = job
        else:
            self._map = self._parent.jobs

    def start(self, interval = 1):
        """@SLURMY
        Spawn subprocess which continuously collects information by configurable mechanism and match any updates in the output to a state change decision of jobs.

        * `interval` Interval at which information is collected by subprocess.
        """
        args = (self._results, interval)
        self._process = mp.Process(target = self._listen_func, args = args)
        self._process.start()

    def update_jobs(self):
        """@SLURMY
        Update jobs associated to parent JobHandler with the collected information.
        """
        for key, update_dict in self._results.get().items():
            ## If key is not registered in the mapping, skip
            if key not in self._map: continue
            job = self._map[key]
            ## If job is not in status which the listener should consider, skip
            if job.status != self._listen_status: continue
            ## If job is in ACTIVE mode, skip
            if job.mode == Mode.ACTIVE: continue
            new_status = update_dict['status']
            ## Set all properties forwarded by the results
            for up_key, up_val in update_dict.items():
                log.debug('(Listener {}) Update {} of job "{}" from {} to {}'.format(self._listen_status.name, up_key, job.name, getattr(job, up_key), up_val))
                setattr(job, up_key, up_val)

    def stop(self):
        """@SLURMY
        Stop listening subprocess.
        """
        self._process.terminate()
