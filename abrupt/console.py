import __builtin__
import os
import sys
import re
import code
import atexit
import getopt

import abrupt
from abrupt.conf import CONF_DIR
from abrupt.color import *

try: 
  import readline, rlcompleter
  has_readline = True
except ImportError:
  has_readline = False

def _usage():
  print """Usage: abrupt [-h] [-b] [-s session_name]
    -h: print this help message
    -b: no graphical banner
    -s: create or load the session"""
  sys.exit(0)

def _save_history():
  try:
    readline.write_history_file(os.path.join(CONF_DIR, "history"))
  except IOError:
    pass

def _load_history():
  try:
    readline.read_history_file(os.path.join(CONF_DIR, "history"))
  except IOError:
    pass
  atexit.register(_save_history)

class ColorPrompt():
  def __init__(self):
    self.prompt = '>>> '
  def __str__(self):
    return '\001%s\002' % info('\002'+self.prompt+'\001')

def interact():
  ns = {}
  abrupt_builtins = __import__("all", globals(), locals(), ".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)

  banner = """   _   _                  _   
  /_\ | |__ _ _ _  _ _ __| |_ 
 / _ \| '_ \ '_| || | '_ \  _|
/_/ \_\_.__/_|  \_,_| .__/\__|
                 """ + abrupt.__version__ + """|_|
"""
  
  try:
    opts = getopt.getopt(sys.argv[1:], "hbs:")
    for opt, param in opts[0]:
      if opt == "-h":
        _usage()
      elif opt == "-s":
        session_name = param
      elif opt == "-b":
        banner = "Abrupt " + abrupt.__version__
  except getopt.GetoptError:
    _usage()

  if not abrupt.conf.check_config_dir():
    print "Generating SSL certificate..."
    abrupt.cert.generate_ca_cert()
    banner += "Welcome to Abrupt, type help() for more information"
  
  if not len(abrupt.injection.payloads):
    print warning("No payload found for the injection, check abrupt/payloads")

  if has_readline:
    class AbruptCompleter(rlcompleter.Completer):
      def global_matches(self, text):
        matches = []
        n = len(text)
        for word in dir(__builtin__) + ns.keys():
          if word[:n] == text and word != "__builtins__":
            matches.append(word)
        return matches

      def attr_matches(self, text):
        m = re.match(r"(\w+(\.\w+)*)\.(\w*)", text)
        if not m: return
        expr, attr = m.group(1, 3)
        try:
          thisobject = eval(expr)
        except:
          thisobject = eval(expr, ns)
        words = dir(thisobject)
        if hasattr(thisobject, "__class__"):
          words = words + rlcompleter.get_class_members(thisobject.__class__)
        matches = []
        n = len(attr)
        for word in words:
          if word[:n] == attr and word != "__builtins__":
            matches.append("%s.%s" % (expr, word))
        return matches

    readline.set_completer(AbruptCompleter().complete)
    readline.parse_and_bind("tab: complete")
    _load_history() 
 
  sys.ps1 = ColorPrompt() 
  code.interact(banner = banner, local=ns)

