
import time
from sys import stdout
from collections import OrderedDict
from .defs import Status, Type


class Printer(object):
    """@SLURMY
    Printer class for the parent JobHandler.

    * `parent` Parent JobHandler instance.
    * `verbosity` Verbosity of the printer's output.
    """
    def __init__(self, parent, verbosity = 1):
        ## Parent JobHandler
        self._parent = parent
        ## Printing verbosity
        self._verbosity = verbosity
        ## Running in manual submission mode?
        self._manual = False
        ## Time
        self._time = None

    def set_manual(self):
        """@SLURMY
        Set printer to manual mode.
        """
        self._manual = True

    def start(self):
        """@SLURMY
        Start printer.
        """
        self._time = time.time()
        self._print_simple()

    def update(self):
        """@SLURMY
        Update printer output.
        """
        self._print_simple()

    def stop(self):
        """@SLURMY
        Stop printer.
        """
        self._time = time.time() - self._time
        stdout.write('\n')
        self.print_summary()

    def _print_simple(self):
        print_string = self._get_print_string()
        if self._manual:
            print_string += ' - press enter to update status'
        stdout.write('\r'+print_string)
        stdout.flush()

    def _get_print_string(self):
        print_string = 'Jobs '
        if self._verbosity > 1:
            n_running = len(self._parent.jobs._states[Status.RUNNING])
            n_local = len(self._parent.jobs._local)
            n_batch = n_running - n_local
            print_string += 'running (batch/local/all): ({}/{}/{}); '.format(n_batch, n_local, n_running)
        n_success = len(self._parent.jobs._states[Status.SUCCESS])
        n_failed = len(self._parent.jobs._states[Status.FAILED])
        n_all = len(self._parent.jobs)
        print_string += '(success/fail/all): ({}/{}/{})'.format(n_success, n_failed, n_all)

        return print_string

    def _get_summary_string(self, time_spent = None):
        n_jobs = len(self._parent.jobs)
        n_local = len(self._parent.jobs._tags[Type.LOCAL])
        n_batch = n_jobs - n_local
        summary_dict = OrderedDict()
        summary_dict['all'] = {'string': 'Jobs processed ', 'batch': n_batch, 'local': n_local}
        summary_dict['success'] = {'string': '     successful ', 'batch': 0, 'local': 0}
        summary_dict['fail'] = {'string': '     failed ', 'batch': 0, 'local': 0}
        jobs_failed = ''
        for job in self._parent.jobs.values():
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
        if self._verbosity > 1 and jobs_failed:
            print_string += 'Failed jobs: {}\n'.format(jobs_failed)
        if time_spent:
            print_string += 'Time spent: {:.1f} s'.format(time_spent)

        return print_string

    def print_summary(self):
        """@SLURMY
        Print a summary of the job processing.
        """
        print_string = self._get_summary_string(self._time)
        stdout.write('\r'+print_string)
        stdout.write('\n')
