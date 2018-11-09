
class Wrapper(object):
    _dummy_script = '.wrapper.sh'
    _wrap_args = ''
    _dummy_wrap_args = '$@'
    _command = '{args}'
    _condition = '{command}'
    
    def __init__(self, insitu = True):
        self._insitu = insitu
        if not self._insitu:
            self._create_wrap_script()

    def _wrap(self, run_script, script_options_identifier):
        ## Define command
        command = self._command.format(args = self._wrap_args)
        command = self._condition.format(command = command)
        ## Recursive function to scan script and find proper position for the command
        def add_command(tail, head = ''):
            line, tail = tail.split('\n', 1)
            line = line.strip()
            ## When line is not empty and is not commented out, command must be inserted before here in any case
            if line and not line.startswith('#'):
                return head + command + '{}\n'.format(line) + tail
            ## If tail doesn't contain the backend options identifier, command can be inserted here
            elif script_options_identifier and '#{}'.format(script_options_identifier) not in tail:
                return head + '{}\n'.format(line) + command + tail
            else:
                head += '{}\n'.format(line)
                return add_command(tail, head)
        ## Add the command
        run_script = add_command(run_script)
        
        return run_script

    def _create_wrap_script(self):
        wrap_script = '#!/bin/bash\n'
        wrap_script += self._command.format(args = self._dummy_wrap_args)
        with open(self._dummy_script, 'w') as out_file:
            out_file.write(wrap_script)

    def setup(self, run_script, script_options_identifier):
        ## Include preamble to run_script if wrapping with additional script is not active
        if self._insitu:
            run_script = self._wrap(run_script, script_options_identifier)

        return run_script

    def get(self, run_script_path):
        if not self._insitu:
            return '{} {}'.format(self._dummy_script, run_script_path)
        
        return run_script_path

class SingularityWrapper(Wrapper):
    def __init__(self, image, **kwargs):
        self._wrap_args = '$0 $@'
        self._command = 'singularity exec {image} {{args}}'.format(image = image)
        self._condition = 'if [[ -z "$SINGULARITY_INIT" ]]\nthen\n  {command}\n  exit $?\nfi\n'
        super(SingularityWrapper, self).__init__(**kwargs)
