#!/usr/bin/env python3

import inspect
import os
from slurmy.tools.jobhandler import JobHandler, JobHandlerConfig
from slurmy.tools.jobcontainer import JobContainer
from slurmy.tools.job import Job, JobConfig
from slurmy.tools.utils import SuccessOutputFile, SuccessTrigger, FinishedTrigger, LogMover, list_sessions, load, load_path, load_latest


sub_dict = {}
for class_name in ['JobHandler', 'JobHandlerConfig', 'JobContainer', 'Job', 'JobConfig']:
    sub_dict['{}.'.format(class_name)] = '[{0}]({0}.md#{0}).'.format(class_name)
    sub_dict['{} '.format(class_name)] = '[{0}]({0}.md#{0}) '.format(class_name)

def parse():
    classes = [
        [JobHandler, 'docs/classes'],
        [JobHandlerConfig, 'docs/classes'],
        [JobContainer, 'docs/classes'],
        [Job, 'docs/classes'],
        [JobConfig, 'docs/classes'],
        [SuccessOutputFile, 'docs/utils'],
        [SuccessTrigger, 'docs/utils'],
        [FinishedTrigger, 'docs/utils'],
        [LogMover, 'docs/utils'],
    ]

    for class_obj, folder in classes:
        ## Get documentation text
        doc_text = get_md_class(class_obj)
        ## Setup folder
        if not os.path.isdir(folder):
            os.makedirs(folder)
        ## Write file
        file_name = os.path.join(folder, '{}.md'.format(class_obj.__name__))
        with open(file_name, 'w') as out_file:
            out_file.write(doc_text)

    function_bundles = [
        [[list_sessions, load, load_path, load_latest], 'docs/interactive_slurmy.md', 'docs/interactive_slurmy/preamble.md']
    ]

    for func_list, output_file, preamble_file in function_bundles:
        ## Get documentation text
        doc_text = get_md_functions(func_list)
        ## Add preamble
        with open(preamble_file, 'r') as in_file:
            preamble = in_file.read()
        doc_text = '{}\n\n{}'.format(preamble, doc_text)
        ## Write file
        with open(output_file, 'w') as out_file:
            out_file.write(doc_text)

def append_doc_list(obj, doc_list, prefix = '', header_depth = '##'):
    obj_name = obj.__name__
    obj_doc = obj.__doc__
    ## If it doesn't have a doc string, skip
    if not obj_doc: return
    ## If doc string doesn't start with @SLURMY, skip
    if not obj_doc.startswith('@SLURMY'): return
    ## Insert page linking
    for key, val in sub_dict.items():
        if key in obj_doc:
            obj_doc = obj_doc.replace(key, val)
    doc_list.append('{}{}'.format(header_depth, obj_name))
    if callable(obj):
        obj_sig = '{}{}{}'.format(prefix, obj_name, inspect.signature(obj))
        doc_list.append('```python\n{}\n```'.format(obj_sig))
    for line in obj_doc.split('\n'):
        ## Ignore @SLURMY line
        if line.startswith('@SLURMY'): continue
        doc_list.append(line.strip())

def get_md_class(class_obj):
    ## Class info
    class_name = class_obj.__name__
    title = '#{}'.format(class_name)
    sig = '{}{}'.format(class_name, inspect.signature(class_obj))
    docstring = class_obj.__doc__
    ## If doc string doesn't start with @SLURMY, skip
    if not docstring.startswith('@SLURMY'):
        return
    ## Insert page linking
    for key, val in sub_dict.items():
        if key in docstring:
            docstring = docstring.replace(key, val)
    md_list = []
    md_list.append(title)
    md_list.append('```python\n{}\n```'.format(sig))
    for line in docstring.split('\n'):
        ## Ignore @SLURMY line
        if line.startswith('@SLURMY'): continue
        md_list.append(line.strip())

    ## Get class members
    members = sorted([l for l in dir(class_obj) if not l.startswith('_')])

    callables = []
    non_callables = []
    for member in members:
        # ## Set list to which entry is added
        # doc_list = callables if callable(obj) else non_callables
        member_obj = getattr(class_obj, member)
        member_doc = member_obj.__doc__
        ## If it doesn't have a doc string, skip
        if not member_doc: continue
        ## If doc string doesn't start with @SLURMY, skip
        if not member_doc.startswith('@SLURMY'): continue
        ## Insert page linking
        for key, val in sub_dict.items():
            if key in member_doc:
                member_doc = member_doc.replace(key, val)
        ## Set list to which entry is added
        this_list = callables if callable(member_obj) else non_callables
        this_list.append('##{}'.format(member))
        if callable(member_obj):
            member_sig = '{}.{}{}'.format(class_name, member, inspect.signature(member_obj))
            this_list.append('```python\n{}\n```'.format(member_sig))
        for line in member_doc.split('\n'):
            ## Ignore @SLURMY line
            if line.startswith('@SLURMY'): continue
            this_list.append(line.strip())

    ## Add non-callable properties
    if non_callables:
        md_list.append('#Properties')
        md_list.extend(non_callables)
    ## Add functions, i.e. callables
    if callables:
        md_list.append('#Member functions')
        md_list.extend(callables)

    return '\n'.join(md_list)

def get_md_functions(func_list, header_depth = '##'):
    doc_list = []
    for func_obj in func_list:
        append_doc_list(func_obj, doc_list, header_depth = header_depth)

    return '\n'.join(doc_list)

if __name__ == '__main__':
    parse()
