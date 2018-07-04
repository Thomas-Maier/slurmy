
## Shamelessly copied and modified from https://gitlab.com/nikoladze/MPF/blob/master/test/__main__.py

import unittest
import argparse
import sys

import logging

log = logging.getLogger('slurmy')

testmodules = [
    'submission'
    ]

print(sys.argv)

parser = argparse.ArgumentParser(description = 'Run the slurmy unittests')
parser.add_argument('tests', nargs = '*', help = 'Only run given tests')
parser.add_argument('--log', help = 'Logging level')
parser.add_argument('-l', '--list', help = 'List test modules', action = 'store_true')
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
    tests = testmodules

## TODO: also allow for printout of the tests themselves, if a detailed list is requested (also merge request to MPF)
if args.list:
    print("Possible test modules:")
    print("======================")
    for test in testmodules:
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
        log.error("Test {} not found - try {}".format(t, testmodules))
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
