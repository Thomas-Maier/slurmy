
import unittest

## TODO: maybe just split in classes Local, Batch, Mixed
## TODO: Tests for
##       - variable substitution (in job config)
##       - output listening
class Test(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'slurmy_unittest/submission'
        self.run_script = 'echo "test"'
        self.run_script_fail = 'echo "test"; exit 1;'
        self.run_script_touch_file = 'echo "test"; touch @SLURMY.output_dir/test sleep 2;'
        self.run_script_ls_file = 'echo "test"; touch @SLURMY.output_dir/test;'

    def test_reset(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_reset', listens = False)
        jh.add_job(run_script = self.run_script, name = 'test')
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)
        id_first = jh.jobs.test.id
        jh.reset()
        self.assertIs(jh.jobs.test.status, Status.CONFIGURED)
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)
        id_second = jh.jobs.test.id
        self.assertIsNot(id_first, id_second)
    
    def test_local(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local', listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test', job_type = Type.LOCAL)
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_local_dynamic(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local_dynamic', local_max = 1, listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        type_first = jh.jobs.test.type
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(type_first, Type.LOCAL)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_batch(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_batch', listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        id_first = jh.jobs.test.id
        jh.jobs.test.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        id_second = jh.jobs.test.id
        self.assertIsNot(id_first, id_second)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_mix(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_mix', local_max = 1, listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test_1')
        jh.add_job(run_script = self.run_script_fail, name = 'test_2')
        jh.run_jobs()
        self.assertIsNot(jh.jobs.test_1.type, jh.jobs.test_2.type)
        self.assertIs(jh.jobs.test_1.status, Status.FAILED)
        self.assertIs(jh.jobs.test_2.status, Status.FAILED)
        id_1_first = jh.jobs.test_1.id
        id_2_first = jh.jobs.test_2.id
        jh.jobs.test_1.config.backend.run_script = self.run_script
        jh.jobs.test_2.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        self.assertIsNot(id_1_first, jh.jobs.test_1.id)
        self.assertIsNot(id_2_first, jh.jobs.test_2.id)
        self.assertIs(jh.jobs.test_1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_2.status, Status.SUCCESS)

    def test_local_listener(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local')
        jh.add_job(run_script = self.run_script_fail, name = 'test', job_type = Type.LOCAL)
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_local_dynamic_listener(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local_dynamic', local_max = 1)
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        type_first = jh.jobs.test.type
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(type_first, Type.LOCAL)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_batch_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_batch')
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        id_first = jh.jobs.test.id
        jh.jobs.test.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        id_second = jh.jobs.test.id
        self.assertIsNot(id_first, id_second)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_mix_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_mix', local_max = 1)
        jh.add_job(run_script = self.run_script_fail, name = 'test_1')
        jh.add_job(run_script = self.run_script_fail, name = 'test_2')
        jh.run_jobs()
        self.assertIsNot(jh.jobs.test_1.type, jh.jobs.test_2.type)
        self.assertIs(jh.jobs.test_1.status, Status.FAILED)
        self.assertIs(jh.jobs.test_2.status, Status.FAILED)
        id_1_first = jh.jobs.test_1.id
        id_2_first = jh.jobs.test_2.id
        jh.jobs.test_1.config.backend.run_script = self.run_script
        jh.jobs.test_2.config.backend.run_script = self.run_script
        jh.run_jobs(retry = True)
        self.assertIsNot(id_1_first, jh.jobs.test_1.id)
        self.assertIsNot(id_2_first, jh.jobs.test_2.id)
        self.assertIs(jh.jobs.test_1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_2.status, Status.SUCCESS)

    def test_chain(self):
        from slurmy import JobHandler
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_chain', listens = False)
        jh.add_job(run_script = self.run_script_touch_file, name = 'test_parent', tags = 'parent')
        jh.add_job(run_script = self.run_script_ls_file, name = 'test_child', parent_tags = 'parent')
        jh.run_jobs()
        self.assertIs(jh.jobs.test_1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_2.status, Status.SUCCESS)

if __name__ == '__main__':
    unittest.main()
