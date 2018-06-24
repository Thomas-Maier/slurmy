#!/usr/bin/env python3

import inspect
import os
from slurmy.tools.jobhandler import JobHandler, JobHandlerConfig
from slurmy.tools.jobcontainer import JobContainer
from slurmy.tools.job import Job, JobConfig


def parse_classes():
    classes = [
        [JobHandler, 'docs/classes'],
        [JobHandlerConfig, 'docs/classes'],
        [JobContainer, 'docs/classes'],
        [Job, 'docs/classes'],
        [JobConfig, 'docs/classes'],
    ]

    for class_obj, folder in classes:
        ## Get documentation text
        doc_text = get_md(class_obj)
        ## Setup folder
        if not os.path.isdir(folder):
            os.makedirs(folder)
        ## Write file
        file_name = os.path.join(folder, '{}.md'.format(class_obj.__name__))
        with open(file_name, 'w') as out_file:
            out_file.write(doc_text)

def get_md(class_obj):
    ## Class info
    class_name = class_obj.__name__
    title = '#{}'.format(class_name)
    sig = '{}{}'.format(class_name, inspect.signature(class_obj))
    docstring = class_obj.__doc__
    ## If doc string doesn't start with @SLURMY, skip
    if not docstring.startswith('@SLURMY'):
        return
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
        member_obj = getattr(class_obj, member)
        member_doc = member_obj.__doc__
        ## If it doesn't have a doc string, skip
        if not member_doc: continue
        ## If doc string doesn't start with @SLURMY, skip
        if not member_doc.startswith('@SLURMY'): continue
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

if __name__ == '__main__':
    parse_classes()
