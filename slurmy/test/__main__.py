
## Shamelessly copied and modified from https://gitlab.com/nikoladze/MPF/blob/master/test/__main__.py

import unittest
import argparse
import sys
import os
import logging

log = logging.getLogger('slurmy')

def get_test_names(discover_list, test_dict):
    for test in discover_list:
        ## If this is not a TestCase, dig deeper
        if not isinstance(test, unittest.TestCase):
            get_test_names(test, test_dict)
        else:
            test_class_module = test.__class__.__module__
            if test_class_module not in test_dict: test_dict[test_class_module] = []
            test_class_name = test.__class__.__name__
            test_method_name = test._testMethodName
            test_name = '{}.{}.{}'.format(test_class_module, test_class_name, test_method_name)
            test_dict[test_class_module].append(test_name)
            
## Get discovery start directory via __file__
start_dir = os.path.dirname(__file__)
discover_list = unittest.defaultTestLoader.discover(start_dir, pattern = '*.py')
## Remove empty test suites
discover_list = [t for t in discover_list if t.countTestCases()]
test_dict = {}
## Get test modules and methods from discovery list
get_test_names(discover_list, test_dict)


parser = argparse.ArgumentParser(description = 'Run the slurmy unittests')
parser.add_argument('tests', nargs = '*', help = 'Only run given tests')
parser.add_argument('--log', help = 'Logging level')
parser.add_argument('-l', '--list', dest = 'list', help = 'List test modules and methods', action = 'store_true')
parser.add_argument('-q', help = 'Set test verbosity to 1 (default 2)', action = 'store_true', default = False)
args = parser.parse_args()

if args.log:
    log.setLevel(getattr(logging, args.log.upper()))
if args.q:
    verbosity = 1
else:
    verbosity = 2

if args.tests:
    tests = args.tests
else:
    tests = []
    for test_names in test_dict.values():
        for test_name in test_names:
            ## If this is python2, skip all "local" tests
            if sys.version_info.major == 2 and 'local' in test_name: continue
            tests.append(test_name)

if args.list:
    print("Possible test modules and methods:")
    print("======================")
    for test_module in sorted(test_dict.keys()):
        print(test_module)
        for test_method in test_dict[test_module]:
            print('-- {}'.format(test_method))
    sys.exit(0)
    

suite = unittest.TestSuite()

## Based on code snippet from http://stackoverflow.com/questions/1732438/how-do-i-run-all-python-unit-tests-in-a-directory#15630454
for postfix in tests:
    t = "slurmy.test."+postfix
    if "." in postfix:
        ## I don't have a better solution yet, so hack for now
        importTest = ".".join(t.split(".")[:-2])
    else:
        importTest = t
    try:
        mod = __import__(importTest, globals(), locals(), ['suite'])
    except ImportError:
        log.error("Test {} not found - try {}".format(t, test_dict.keys()))
        raise
    try:
        ## If the module defines a suite() function, call it to get the suite.
        suitefn = getattr(mod, 'suite')
        suite.addTest(suitefn())
    except (ImportError, AttributeError):
        ## Else, just load all the test cases from the module.
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))

result = unittest.TextTestRunner(verbosity = verbosity).run(suite)
sys.exit(not result.wasSuccessful())
