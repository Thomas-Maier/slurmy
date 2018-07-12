
import unittest
import os


class Test(unittest.TestCase):
    def setUp(self):
        from slurmy import JobHandler, test_mode
        test_mode(True)
        self.test_dir = 'slurmy_unittest/jobconfig'
        self.jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_jobconfig', do_snapshot = False)
        self.run_script = 'echo "test"'
        self.run_script_trigger = '@SLURMY.FINISHED; @SLURMY.SUCCESS;'

    def tearDown(self):
        from slurmy import test_mode
        test_mode(False)

    ##TODO: run_script test --> with direct string and path to file

    def test_run_args(self):
        job = self.jh.add_job(run_script = self.run_script, run_args = 'test')
        self.assertIs(job.config.backend.run_args, 'test')
        
    def test_name(self):
        job = self.jh.add_job(run_script = self.run_script, name = 'test')
        self.assertIs(job.name, 'test')
        self.assertIn('test', self.jh.jobs)
        self.assertIs(self.jh.jobs.test.name, 'test')
        
    def test_type_local(self):
        from slurmy import JobHandler, Type
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_jobconfig_type_local', do_snapshot = False, local_max = 1)
        job = jh.add_job(run_script = self.run_script, job_type = Type.LOCAL)
        self.assertIs(job.type, Type.LOCAL)

    def test_finished_func(self):
        from slurmy import Status, Mode
        job = self.jh.add_job(run_script = self.run_script, finished_func = lambda x: x)
        self.assertIs(job.get_mode(Status.RUNNING), Mode.ACTIVE)
        self.assertTrue(job.config.finished_func(True))

    def test_success_func(self):
        from slurmy import Status, Mode
        job = self.jh.add_job(run_script = self.run_script, success_func = lambda x: x)
        self.assertIs(job.get_mode(Status.FINISHED), Mode.ACTIVE)
        self.assertTrue(job.config.success_func(True))

    def test_post_func(self):
        from slurmy import Status
        job = self.jh.add_job(run_script = self.run_script, post_func = lambda x: x)
        self.assertTrue(job.config.post_func(True))

    def test_output(self):
        from slurmy import Status, Mode
        job = self.jh.add_job(run_script = self.run_script, output = 'test')
        self.assertIs(job.get_mode(Status.FINISHED), Mode.PASSIVE)
        self.assertIsNotNone(job.output)

    def test_tags(self):
        job = self.jh.add_job(run_script = self.run_script, tags = 'hans')
        self.assertIn('hans', job.tags)
        job = self.jh.add_job(run_script = self.run_script, tags = ['hans', 'horst'])
        self.assertIn('hans', job.tags)
        self.assertIn('horst', job.tags)

    def test_parent_tags(self):
        job = self.jh.add_job(run_script = self.run_script, parent_tags = 'hans')
        self.assertIn('hans', job.parent_tags)
        job = self.jh.add_job(run_script = self.run_script, parent_tags = ['hans', 'horst'])
        self.assertIn('hans', job.parent_tags)
        self.assertIn('horst', job.parent_tags)

    def test_variable_substitution(self):
        from slurmy import Status
        job = self.jh.add_job(run_script = self.run_script, output = '@SLURMY.output_dir/test')
        output = os.path.join(self.jh.config.output_dir, 'test')
        self.assertTrue(job.output == output)

    ##TODO: rework to be compatible with new logic
    # def test_trigger(self):
    #     from slurmy import Status, Mode
    #     job = self.jh.add_job(run_script = self.run_script_trigger)
    #     self.assertIsNotNone(job.output)
    #     self.assertIsNotNone(job.config.finished_func)
    #     self.assertIs(job.get_mode(Status.RUNNING), Mode.ACTIVE)
    #     self.assertIs(job.get_mode(Status.FINISHED), Mode.PASSIVE)
    #     job = self.jh.add_job(run_script = self.run_script_trigger, output = 'test')
    #     self.assertIs(job.output, 'test')
    #     self.assertIs(job.get_mode(Status.FINISHED), Mode.ACTIVE)
    #     self.assertIsNotNone(job.config.success_func)
