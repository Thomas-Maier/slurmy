
import unittest
import os
import time


class TestPostFunction:
    def __init__(self, file_name):
        self._file_name = file_name
        
    def __call__(self, config):
        os.system('touch {}'.format(self._file_name))


class Test(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'slurmy_unittest/submission'
        if not os.path.isdir(self.test_dir): os.makedirs(self.test_dir)
        self.run_script = '#!/bin/bash\necho "test"'
        self.run_script_fail = '#!/bin/bash\necho "test"; exit 1;'
        self.output_file = '@SLURMY.output_dir/test'
        self.run_script_touch_file = '#!/bin/bash\ntouch {0}; sleep 2;'.format(self.output_file)
        self.run_script_ls_file = '#!/bin/bash\nls {};'.format(self.output_file)
        self.run_script_trigger = '#!/bin/bash\necho "test"; @SLURMY.FINISHED; @SLURMY.SUCCESS;'
        self.run_script_trigger_finished = '#!/bin/bash\necho "test"; @SLURMY.FINISHED;'
        self.run_script_trigger_success = '#!/bin/bash\necho "test"; @SLURMY.SUCCESS;'
        script_path = os.path.abspath(os.path.join(self.test_dir, 'run_script_success.sh'))
        with open(script_path, 'w') as out_file:
            out_file.write(self.run_script)
        self.run_script_success = script_path

    # def tearDown(self):
    #     os.remove(self.run_script_success)

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
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local', listens = False, local_max = 1)
        jh.add_job(run_script = self.run_script_fail, name = 'test', job_type = Type.LOCAL)
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_local_dynamic(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local_dynamic', local_max = 1, local_dynamic = True, listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        type_first = jh.jobs.test.type
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script_success
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
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        id_second = jh.jobs.test.id
        self.assertIsNot(id_first, id_second)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_mix_batch_local(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_mix_batch_local', local_max = 1, local_dynamic = True, listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test_1')
        jh.add_job(run_script = self.run_script_fail, name = 'test_2')
        jh.run_jobs()
        self.assertIsNot(jh.jobs.test_1.type, jh.jobs.test_2.type)
        self.assertIs(jh.jobs.test_1.status, Status.FAILED)
        self.assertIs(jh.jobs.test_2.status, Status.FAILED)
        jh.jobs.test_1.config.backend.run_script = self.run_script_success
        jh.jobs.test_2.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        self.assertIs(jh.jobs.test_1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_2.status, Status.SUCCESS)

    def test_local_listener(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local_listener', local_max = 1)
        jh.add_job(run_script = self.run_script_fail, name = 'test', job_type = Type.LOCAL)
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_local_dynamic_listener(self):
        from slurmy import JobHandler, Status, Type, test_mode
        test_mode(True)
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_local_dynamic_listener', local_max = 1, local_dynamic = True)
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        type_first = jh.jobs.test.type
        status_fail = jh.jobs.test.status
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        test_mode(False)
        self.assertIs(type_first, Type.LOCAL)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_batch_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_batch_listener')
        jh.add_job(run_script = self.run_script_fail, name = 'test')
        jh.run_jobs()
        status_fail = jh.jobs.test.status
        id_first = jh.jobs.test.id
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        status_success = jh.jobs.test.status
        id_second = jh.jobs.test.id
        self.assertIsNot(id_first, id_second)
        self.assertIs(status_fail, Status.FAILED)
        self.assertIs(status_success, Status.SUCCESS)

    def test_mix_batch_local_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_mix_batch_local_listener', local_max = 1, local_dynamic = True)
        jh.add_job(run_script = self.run_script_fail, name = 'test_1')
        jh.add_job(run_script = self.run_script_fail, name = 'test_2')
        jh.run_jobs()
        self.assertIsNot(jh.jobs.test_1.type, jh.jobs.test_2.type)
        self.assertIs(jh.jobs.test_1.status, Status.FAILED)
        self.assertIs(jh.jobs.test_2.status, Status.FAILED)
        jh.jobs.test_1.config.backend.run_script = self.run_script_success
        jh.jobs.test_2.config.backend.run_script = self.run_script_success
        jh.run_jobs(retry = True)
        self.assertIs(jh.jobs.test_1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_2.status, Status.SUCCESS)

    def test_chain(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_chain', listens = False)
        jh.add_job(run_script = self.run_script_touch_file, name = 'test_parent', tags = 'parent')
        jh.add_job(run_script = self.run_script_ls_file, name = 'test_child', parent_tags = 'parent')
        jh.run_jobs()
        self.assertIs(jh.jobs.test_parent.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_child.status, Status.SUCCESS)

    def test_chain_fail(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_chain', listens = False)
        jh.add_job(run_script = self.run_script_fail, name = 'test_parent', tags = 'parent')
        jh.add_job(run_script = self.run_script_success, name = 'test_child', parent_tags = 'parent')
        jh.run_jobs()
        self.assertIs(jh.jobs.test_parent.status, Status.FAILED)
        self.assertIs(jh.jobs.test_child.status, Status.CANCELLED)

    def test_chain_multiparent(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_chain_multiparent', listens = False)
        output1 = '@SLURMY.output_dir/parent1'
        run_script1 = '#!/bin/bash\ntouch {}; sleep 2;'.format(output1)
        jh.add_job(run_script = run_script1, name = 'test_parent1', tags = 'parent1', output = output1)
        output2 = '@SLURMY.output_dir/parent2'
        run_script2 = '#!/bin/bash\ntouch {}; sleep 2;'.format(output2)
        jh.add_job(run_script = run_script2, name = 'test_parent2', tags = 'parent2', output = output2)
        run_script3 = '#!/bin/bash\nls {} {};'.format(output1, output2)
        jh.add_job(run_script = run_script3, name = 'test_child', parent_tags = ['parent1', 'parent2'])
        jh.run_jobs()
        self.assertIs(jh.jobs.test_parent1.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_parent2.status, Status.SUCCESS)
        self.assertIs(jh.jobs.test_child.status, Status.SUCCESS)

    def test_output(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_output', listens = False)
        jh.add_job(run_script = self.run_script_touch_file, name = 'test', output = self.output_file)
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)
        jh.reset()
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.jobs.test.config.output = 'jwoigjwoijegoijwoijegoiwoeg'
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.FAILED)

    def test_output_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_output_listener')
        jh.add_job(run_script = self.run_script_touch_file, name = 'test', output = self.output_file)
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)
        jh.reset()
        jh.jobs.test.config.backend.run_script = self.run_script_success
        jh.jobs.test.config.output = 'jwoigjwoijegoijwoijegoiwoeg'
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.FAILED)

    def test_trigger(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_trigger', listens = False)
        jh.add_job(run_script = self.run_script_trigger, name = 'test')
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_trigger_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_trigger_listener')
        jh.add_job(run_script = self.run_script_trigger, name = 'test')
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_trigger_finished(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_trigger_finished')
        jh.add_job(run_script = self.run_script_trigger_finished, name = 'test')
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_trigger_success(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_trigger_success', listens = False)
        jh.add_job(run_script = self.run_script_trigger_success, name = 'test')
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_trigger_success_listener(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_trigger_success_listener')
        jh.add_job(run_script = self.run_script_trigger_success, name = 'test')
        jh.run_jobs()
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)

    def test_post_process(self):
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_post_process')
        output_file = os.path.join(jh.config.output_dir, 'test')
        post_func = TestPostFunction(output_file)
        jh.add_job(run_script = self.run_script, name = 'test', post_func = post_func)
        jh.run_jobs()
        time.sleep(1)
        self.assertIs(jh.jobs.test.status, Status.SUCCESS)
        self.assertTrue(os.path.isfile(output_file))

    def test_run_max(self):
        ## This effectively only tests if run_jobs finishes or not
        from slurmy import JobHandler, Status
        jh = JobHandler(work_dir = self.test_dir, verbosity = 0, name = 'test_run_max', run_max = 1)
        for i in range(3):
            jh.add_job(run_script = self.run_script, name = 'test_{}'.format(i))
        jh.run_jobs()
        for i in range(3):
            self.assertIs(jh['test_{}'.format(i)].status, Status.SUCCESS)

if __name__ == '__main__':
    unittest.main()
