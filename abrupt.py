#!/usr/bin/python
#
# abrupt 
# tw@securusglobal.com
#

from http import Request, Response
from proxy import p, w, p1, w1

if __name__ == "__main__":
  import code
  import __builtin__
  abrupt_builtins = __import__(__name__,globals(),locals(),".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  try:
    import IPython
    from color import *
    print success("~~--[ ") + great_success("Abrupt 0.1") + success(" ]--~~")
    print "comment and bugs: tw@securusglobal.com"
    print "p(): to run a interactive proxy"
    print "w(): to run a passive proxy",
    ipshell = IPython.Shell.IPShellEmbed([''])
    ipshell()
  except ImportError:
    print "Using classic interpreter, for a better experience, install Ipython"
    code.interact()



