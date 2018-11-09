
import time
from sys import stdout
from collections import OrderedDict
import logging
from .defs import Status, Type
from .tags import Tags

log = logging.getLogger('slurmy')


class Printer(object):
    """@SLURMY
    Printer class for the parent JobHandler.

    * `parent` Parent JobHandler instance.
    * `verbosity` Verbosity of the printer's output.
    """
    def __init__(self, parent, verbosity = 1, bar_mode = False):
        ## Parent JobHandler
        self._parent = parent
        ## Printing verbosity
        self._verbosity = verbosity
        ## Running in manual submission mode?
        self._manual_mode = False
        ## Running in progress bar mode?
        self._bar_mode = bar_mode
        ### Check if tqdm is available, otherwise disable bar mode
        if self._bar_mode:
            try:
                from tqdm import tqdm
            except ImportError:
                log.warning('printer_bar_mode is activated but the tqdm module is not available')
                log.warning('Please install tqdm to use the bar mode')
                self._bar_mode = False
        self._bar_format = '{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{postfix}]'
        ## Time
        self._time = None
        ## Tags which are tracked (set during bars setup)
        self._tags = Tags()

    def set_manual(self):
        """@SLURMY
        Set printer to manual mode.
        """
        self._manual_mode = True

    def _setup_bars(self):
        from tqdm import tqdm
        ## Recursive function to add tags
        def add(tags, prefix = '-'):
            for tag in tags:
                n_jobs_tag = len(self._parent.jobs._tags[tag])
                n_initial_tag = sum(updates[tag].values())
                bars[tag] = tqdm(total = n_jobs_tag, initial = n_initial_tag, desc = tag, unit = 'job', bar_format = prefix+self._bar_format)
                bars[tag].set_postfix(updates[tag])
                add(tags[tag], prefix+'-')
        ## Get updates for the initial bar values
        updates = self._get_updates()
        ## Create bars
        bars = OrderedDict()
        ### Add bar for all jobs
        n_jobs = len(self._parent.jobs)
        #### Initial number of success/failed jobs
        n_initial = sum(updates['all'].values())
        bars['all'] = tqdm(total = n_jobs, initial = n_initial, desc = 'all', unit = 'job', bar_format = self._bar_format)
        bars['all'].set_postfix(updates['all'])
        add(self._tags.tree)

        return bars

    def _get_updates(self):
        update_dict = OrderedDict()        
        ## Entry for all jobs
        update_dict['all'] = OrderedDict()
        for status_label, status in zip(['S', 'F', 'C'], [Status.SUCCESS, Status.FAILED, Status.CANCELLED]):
            update_dict['all'][status_label] = len(self._parent.jobs._states[status])
        ## Entries for tracked tags
        for tag in self._tags.tags:
            update_dict[tag] = OrderedDict()
            for status_label, status in zip(['S', 'F', 'C'], [Status.SUCCESS, Status.FAILED, Status.CANCELLED]):
                update_dict[tag][status_label] = len(self._parent.jobs.get(tags = tag, states = status))

        return update_dict

    def _update_bars(self):
        ## Get updates
        updates = self._get_updates()
        ## Update bars
        for tag in updates:
            n_jobs = sum(updates[tag].values())
            n_update_jobs = n_jobs - self._bars[tag].n
            if n_update_jobs > 0:
                ## If update number is positive, just update the bar
                self._bars[tag].update(n_update_jobs)
            elif n_update_jobs < 0:
                ## Else if it's negative, set bar.n to n_jobs
                self._bars[tag].n = n_jobs
            ### Set postfix to number of success/failed/cancelled jobs
            ### This also forces a refresh
            self._bars[tag].set_postfix(updates[tag])

    def start(self):
        """@SLURMY
        Start printer.
        """
        self._time = time.time()
        ## If verbosity is 0, do nothing
        if self._verbosity == 0: return
        ## Set up tags
        self._tags.setup(self._parent.jobs.values())
        if self._bar_mode:
            ## Set up bars
            self._bars = self._setup_bars()
        else:
            self._print_simple()

    def update(self):
        """@SLURMY
        Update printer output.
        """
        ## If verbosity is 0, do nothing
        if self._verbosity == 0: return
        if self._bar_mode:
            self._update_bars()
        else:
            self._print_simple()

    def stop(self):
        """@SLURMY
        Stop printer.
        """
        ## Final update before we stop
        self.update()
        self._time = time.time() - self._time
        ## If verbosity is 0, stop here
        if self._verbosity == 0: return
        if self._bar_mode:
            ## Close bars
            for bar in self._bars.values():
                bar.close()
        n_newlines = 1
        if self._bar_mode:
            n_bars = len(self._bars)
            if n_bars > 1:
                n_newlines = n_bars-1
        stdout.write(n_newlines*'\n')
        self.print_summary()

    def _print_simple(self):
        print_string = self._get_print_string()
        if self._manual_mode:
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
