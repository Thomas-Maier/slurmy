
from .defs import Status


class JobContainer(dict, object):
    """@SLURMY
    Container class which holds the jobs associated to a JobHandler session. Jobs are attached as properties to allow for easy access in interactive slurmy.
    """
    def __init__(self):
        self.states = {Status.CONFIGURED: set(), Status.RUNNING: set(), Status.FINISHED: set(), Status.SUCCESS: set(), Status.FAILURE: set(), Status.CANCELLED: set()}

    ## TODO: probably should be a generator
    def get(self, tags = None):
        """@SLURMY
        Get the list of jobs.

        * `tags` Tags that jobs are filtered on.
        """
        job_list = []
        for job in self.values():
            if tags is not None and not job.has_tags(tags): continue
            job_list.append(job)

        return job_list

    def _update_job_status(self, job, skip_eval = False, force_success_check = False):
        name = job.name
        new_status = job.get_status(skip_eval = skip_eval, force_success_check = force_success_check)
        ## If old and new status are the same, do nothing
        if name in self.states[new_status]: return
        ## Remove current status entry for job
        for status in Status:
            if name not in self.states[status]: continue
            self.states[status].remove(name)
        ## Add new one
        self.states[new_status].add(name)

    def _update_job_states(self, **kwargs):
        for job in self.values():
            self._update_job_status(job, **kwargs)

    def print(self, tags = None, states = None, print_summary = True):
        """@SLURMY
        Print the list of jobs and their current status.

        * `tags` Tags that jobs should match with (single string or list of strings). If a job has any of the provided tags it will be printed.
        * `states` States that jobs should match with (single string or list of strings). If a job is in any of the provided states it will be printed.
        * `print_summary` Print overall summary as well.
        """
        if tags is not None:
            if not (isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set)):
                tags = [tags]
            tags = set(tags)
        if states is not None:
            if not (isinstance(states, list) or isinstance(states, tuple) or isinstance(states, set)):
                states = [states]
            states = set(states)

        print(self._jobs_printlist(tags = tags, states = states, print_summary = print_summary))

    def _jobs_printlist(self, tags = None, states = None, print_summary = True):
        printlist = []
        summary = {}
        for job_name, job in self.items():
            job_status = job.get_status()
            if tags and job.has_tags(tags): continue
            if states and job_status not in states: continue
            printlist.append('Job "{}": {}'.format(job.name, job_status.name))
            if job_status not in summary:
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
