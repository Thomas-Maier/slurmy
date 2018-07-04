
## Shamelessly copied and modified from https://gitlab.com/nikoladze/MPF/blob/master/test/__main__.py

import unittest
import argparse
import sys

import logging

log = logging.getLogger('slurmy')

def get_test_names(discover_list, test_modules, test_methods):
    for test in discover_list:
        ## If this is not a TestCase, dig deeper
        if not isinstance(test, unittest.TestCase):
            get_test_names(test, test_modules, test_methods)
        else:
            test_class_module = test.__class__.__module__
            test_modules.add(test_class_module)
            test_class_name = test.__class__.__name__
            test_method_name = test._testMethodName
            test_name = '{}.{}.{}'.format(test_class_module, test_class_name, test_method_name)
            test_methods.append(test_name)
            
## Get discovery start directory via __file__
start_dir = __file__.rsplit('/', 1)[0]
discover_list = unittest.defaultTestLoader.discover(start_dir, pattern = '*.py')
## Remove empty test suites
discover_list = [t for t in discover_list if t.countTestCases()]
test_modules = set()
test_methods = []
## Get test modules and methods from discovery list
get_test_names(discover_list, test_modules, test_methods)


parser = argparse.ArgumentParser(description = 'Run the slurmy unittests')
parser.add_argument('tests', nargs = '*', help = 'Only run given tests')
parser.add_argument('--log', help = 'Logging level')
parser.add_argument('--list', dest = 'list', help = 'List test modules', action = 'store_true')
parser.add_argument('--list-methods', dest = 'list_methods', help = 'List test methods', action = 'store_true')
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
    tests = test_modules

if args.list:
    print("Possible test modules:")
    print("======================")
    for test in test_modules:
        print(test)
    sys.exit(0)
    
if args.list_methods:
    print("Possible test methods:")
    print("======================")
    for test in test_methods:
        print(test)
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
        log.info("Trying to import {}".format(importTest))
        mod = __import__(importTest, globals(), locals(), ['suite'])
    except ImportError:
        log.error("Test {} not found - try {}".format(t, test_modules))
        raise
    try:
        ## If the module defines a suite() function, call it to get the suite.
        suitefn = getattr(mod, 'suite')
        suite.addTest(suitefn())
    except (ImportError, AttributeError):
        ## Else, just load all the test cases from the module.
        log.info("Loading test {}".format(t))
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))

result = unittest.TextTestRunner(verbosity = verbosity).run(suite)
sys.exit(not result.wasSuccessful())
