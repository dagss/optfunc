#!/usr/bin/env python
import optfunc

def upper(filename, verbose = False):
    "Usage: %prog <file> [--verbose] - output file content in uppercase"
    s = open(filename).read()
    if verbose:
        print "Processing %s bytes..." % len(s)
    print s.upper()

def lower(filename, verbose = False):
    "Usage: %prog <file> [--verbose] - output file content in lowercase"
    s = open(filename).read()
    if verbose:
        print "Processing %s bytes..." % len(s)
    print s.lower()

if __name__ == '__main__':
    optfunc.run([upper, lower])
