import __builtin__
import os
import sys
import re
import code
import atexit
import getopt
import pydoc

import abrupt
import abrupt.session
from abrupt.conf import CONF_DIR
from abrupt.color import *

try: 
  import readline, rlcompleter
  has_readline = True
except ImportError:
  has_readline = False

def _usage():
  print """Usage: abrupt [-hbn] [-s session_name]
    -h: print this help message
    -b: no graphical banner
    -n: don't load the session last save
    -s: create or load the session"""
  sys.exit(0)

def _save_history():
  try:
    readline.write_history_file(os.path.join(CONF_DIR, ".history"))
  except IOError:
    pass

def _load_history():
  try:
    readline.read_history_file(os.path.join(CONF_DIR, ".history"))
  except IOError:
    pass
  atexit.register(_save_history)

class ColorPrompt():
  def __str__(self):
    session_name = abrupt.session.session_name
    prompt = '\001%s\002' % info('\002>>> \001')
    if session_name != "default":
      prompt = '\001%s\002 ' % warning('\002'+session_name+'\001') + prompt
    return prompt

def help(obj=None):
  if not obj:
    print """Welcome to Abrupt! 

If this is your first time using Abrupt, you should check the quickstart at
http://securusglobal.github.com/Abrupt/. 

Here are the basic functions of Abrupt, type 'help(function)' for a 
complete description of these functions:
  * p: Start a HTTP proxy on port 8080. The successful requests 
       will be returned.
  * i: Inject a request (see also i_at).
  * c: Create a HTTP request based on a URL.

Abrupt have few classes which worth having a look at:
  * Request 
  * Response 
  * RequestSet

Please, report any bug or comment to tw@securusglobal.com
"""
  else:
    pydoc.help(obj) 
  
 
def interact():
  abrupt_builtins = __import__("all", globals(), locals(), ".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  __builtin__.__dict__["help"] = help
  __builtin__.__dict__["python_help"] = pydoc.help

  banner = """   _   _                  _   
  /_\ | |__ _ _ _  _ _ __| |_ 
 / _ \| '_ \ '_| || | '_ \  _|
/_/ \_\_.__/_|  \_,_| .__/\__|
                 """ + abrupt.__version__ + """|_|
"""
  
  session_loading = True
  # Parse arguments
  try:
    opts = getopt.getopt(sys.argv[1:], "hbs:n")
    for opt, param in opts[0]:
      if opt == "-h":
        _usage()
      elif opt == "-s":
        abrupt.session.session_name = param
      elif opt == "-n":
        session_loading = False
      elif opt == "-b":
        banner = "Abrupt " + abrupt.__version__
    if opts[1]: 
        _usage()
  except getopt.GetoptError:
    _usage()
  
  # First time setup
  if not abrupt.conf.check_config_dir():
    print "Generating SSL certificate..."
    abrupt.cert.generate_ca_cert()
    banner += "Welcome to Abrupt, type help() for more information"
  
  # Could we find the payloads?
  if not len(abrupt.injection.payloads):
    print warning("No payload found for the injection, check abrupt/payloads")

  # Load the session
  if session_loading:
    abrupt.session.load_session()

  # Setup autocompletion if readline
  if has_readline:
    class AbruptCompleter(rlcompleter.Completer):
      def global_matches(self, text):
        matches = []
        n = len(text)
        for word in dir(__builtin__) + abrupt.session.session_dict.keys():
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
          thisobject = eval(expr, abrupt.session.session_dict)
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
 
  # And run the interpreter!
  sys.ps1 = ColorPrompt()
  atexit.register(abrupt.session.store_session)
  code.interact(banner = banner, local=abrupt.session.session_dict)

