
from .defs import Status


class JobContainer(dict, object):        
    def __call__(self, tag = None):
        print(self._jobs_printlist(tag))

    def _jobs_printlist(self, tag = None, status = None):
        printlist = []
        for job_name, job in self.items():
            job_status = job.get_status()
            if tag and tag not in job.get_tags(): continue
            if status and job_status != status: continue
            printlist.append('Job "{}": {}'.format(job.get_name(), job_status.name))

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
def _get_status_property(status):
    def getter(self):
        print(self._jobs_printlist(status = status))

    return property(fget = getter)
## Setting status printing properties for JobContainer class
for status in Status:
    setattr(JobContainer, 'status_{}'.format(status.name), _get_status_property(status))
