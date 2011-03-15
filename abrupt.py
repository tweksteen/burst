#!/usr/bin/python2

from abrupt import *

if __name__ == "__main__":
  import code
  import __builtin__
  abrupt_builtins = __import__(__name__,globals(),locals(),".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  try:
    import IPython
    from abrupt.color import *
    print success("~~--[ ") + great_success("Abrupt 0.1") + success(" ]--~~"),
    ipshell = IPython.Shell.IPShellEmbed()
    ipshell()
  except ImportError:
    print "Using classic interpreter, for a better experience, install Ipython"
    code.interact()

