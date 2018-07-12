
## This is needed so that we can define JobContainer.print in python2
from __future__ import print_function
from .defs import Status, Type


class JobContainer(dict, object):
    """@SLURMY
    Container class which holds the jobs associated to a JobHandler session. Jobs are attached as properties to allow for easy access in interactive slurmy.
    """
    def __init__(self):
        self._states = {Status.CONFIGURED: set(), Status.RUNNING: set(), Status.FINISHED: set(), Status.SUCCESS: set(), Status.FAILED: set(), Status.CANCELLED: set()}
        self._tags = {}
        self._tags[Type.LOCAL] = set()
        self._local = set()
        self._ids = {}

    def add_id(self, job_id, job_name):
        self._ids[job_id] = job_name

    def add(self, job):
        ## Add job to respective tag list
        tags = job.tags
        for tag in tags:
            if tag not in self._tags:
                ## Add tag entry in tags dictionary
                self._tags[tag] = []
            self._tags[tag].append(job)
        ## Add job to internal dictionary and as a property
        self[job.name] = job

    def get(self, tags = None, states = None):
        """@SLURMY
        Get the list of jobs.

        * `tags` Tags that the jobs must match to (single string or list of strings).
        * `states` Job states that the jobs must match to (single Status object or list of Status objects).

        Returns list of jobs ([Job]).
        """
        if tags is not None:
            if not (isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set)):
                tags = [tags]
            if not isinstance(tags, set):
                tags = set(tags)
        if states is not None:
            if not (isinstance(states, list) or isinstance(states, tuple) or isinstance(states, set)):
                states = [states]
            if not isinstance(states, set):
                states = set(states)
        job_list = []
        for job in self.values():
            if tags is not None and not job.has_tags(tags): continue
            if states is not None and job.get_status() not in states: continue
            job_list.append(job)

        return job_list

    def _update_job_status(self, job, skip_eval = False, force_success_check = False):
        name = job.name
        new_status = job.get_status(skip_eval = skip_eval, force_success_check = force_success_check)
        ## If old and new status are the same, do nothing
        if name in self._states[new_status]: return
        ## Remove current status entry for job
        for status in Status:
            if name not in self._states[status]: continue
            self._states[status].remove(name)
        ## Add new one
        self._states[new_status].add(name)

    def _update_job_states(self, **kwargs):
        for job in self.values():
            self._update_job_status(job, **kwargs)

    def _update_tags(self, job):
        name = job.name
        job_type = job.type
        if job_type == Type.LOCAL:
            ## Job name already in list of local jobs, nothing to be done
            if name in self._tags[Type.LOCAL]: return
            self._tags[Type.LOCAL].add(name)
        else:
            ## Job name not in list of local jobs, nothing to be done
            if name not in self._tags[Type.LOCAL]: return
            self._tags[Type.LOCAL].remove(name)

    def _update_job_tags(self):
        for job in self.values():
            self._update_tags(job)

    def print(self, tags = None, states = None, print_summary = True):
        """@SLURMY
        Print the list of jobs and their current status.

        * `tags` Tags that jobs should match with (single string or list of strings). If a job has any of the provided tags it will be printed.
        * `states` States that jobs should match with (single Status object or list of Status objects). If a job is in any of the provided states it will be printed.
        * `print_summary` Print overall summary as well.
        """

        print(self._jobs_printlist(tags = tags, states = states, print_summary = print_summary))

    def _jobs_printlist(self, tags = None, states = None, print_summary = True):
        printlist = []
        summary = {}
        for job in self.get(tags = tags, states = states):
            job_name = job.name
            job_status = job.status
            printlist.append('Job "{}": {}'.format(job_name, job_status.name))
            if job_status.name not in summary:
                summary[job_status.name] = 0
            summary[job_status.name] += 1
        if print_summary:
            printlist.append('------------')
            printlist.append(' - '.join(['{}({})'.format(s, c) for s, c in summary.items()]))
            
        return '\n'.join(printlist)

    def __repr__(self):
        return self._jobs_printlist()

    def __setitem__(self, key, val):
        super(JobContainer, self).__setitem__(key, val)
        ## Check if a property with name key already exists, in this case we would overwrite functionality of the dictionary class
        if getattr(self, key, None) is not None:
            log.error('Take a look at the properties list of the dict class and please do not choose a name that matches any of them')
            raise Exception
        self.__dict__[key] = val

    def __getitem__(self, key):
        ## If key is in job id dict, substitute with job name matched to job id
        if key in self._ids:
            key = self._ids[key]
            
        return super(JobContainer, self).__getitem__(key)

    def __contains__(self, key):
        ## Check own dict as well as the job ids dict for the key
        return (super(JobContainer, self).__contains__(key) or (key in self._ids))
        
## Property for status printing
def _get_status_property(status, docstring):
    def getter(self):
        self.print(states = status, print_summary = False)

    return property(fget = getter, doc = docstring)
## Setting status printing properties for JobContainer class
for status in Status:
    docstring = """@SLURMY
    List jobs in status {}.
    """.format(status.name)
    setattr(JobContainer, 'status_{}'.format(status.name), _get_status_property(status, docstring))
