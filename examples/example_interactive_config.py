

jh = JobHandler()

_run_script = """
sleep {1}
echo $1
echo $2
"""
  
_run_args = [1, 2, 3, 4, 5, 6]
_times = [2, 4, 6, 8, 10, 12]
    
for time_val, run_arg in zip(_times, _run_args):
  jh.add_job(run_script = _run_script.format(run_arg, time_val),
             run_args = 'bla blub')
