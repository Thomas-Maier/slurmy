
import unittest
import os

## TODO: maybe just split in classes Local, Batch, Mixed
class Test(unittest.TestCase):

    def setUp(self):
        self.test_dir = 'slurmy_unittest/submission'
    
    def test_local(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local')
        run_script = 'echo "test"'
        jh.add_job(run_script = run_script, name = 'test', job_type = Type.LOCAL)
        jh.run_jobs(interval = 1)
        test_mode(False)
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_local_dynamic(self):
        from slurmy import JobHandler, Status, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local_dynamic', local_max = 1)
        run_script = 'echo "test"'
        jh.add_job(run_script = run_script, name = 'test')
        jh.run_jobs(interval = 1)
        test_mode(False)
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_batch(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_batch')
        run_script = 'echo "test"'
        jh.add_job(run_script = run_script, name = 'test')
        jh.run_jobs(interval = 1)
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_mix(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_mix', local_max = 1)
        run_script = 'echo "test"'
        jh.add_job(run_script = run_script, name = 'test_1')
        jh.add_job(run_script = run_script, name = 'test_2')
        jh.run_jobs(interval = 1)
        self.assertIs(jh.jobs.test_1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_2.status, Status.SUCCESS)
        self.assertIsNot(jh.jobs.test_1.type, jh.jobs.test_2.type)

if __name__ == '__main__':
    unittest.main()
