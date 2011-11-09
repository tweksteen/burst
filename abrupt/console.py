import __builtin__
import os
import sys
import re
import code
import atexit
import getopt
import pydoc
import signal

import abrupt
from abrupt.conf import CONF_DIR
from abrupt.color import *

try: 
  import readline, rlcompleter
  has_readline = True
except ImportError:
  has_readline = False

try:
  import termios
  import fcntl
  import struct
  has_termios = True
except ImportError:
  has_termios = False

term_width = None

def _usage():
  print """Usage: abrupt [-bhlv] [-s session_name]
    -b: no graphical banner
    -h: print this help message
    -l: list existing sessions
    -v: print the version and exit
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

def _get_term_width():
  if has_termios:
    for i in range(3):
      try:
        bin_size = fcntl.ioctl(i, termios.TIOCGWINSZ, '????')
        _, width = struct.unpack('hh', bin_size)
        return width
      except:
        pass
  return 80

def _update_term_width(snum, frame):
  global term_width
  if conf.term_width:
    if conf.term_width == "auto":
      term_width = _get_term_width()
    else:
      term_width = int(conf.term_width)
  else:
    term_width = 0

class ColorPrompt(object):
  def __str__(self):
    session_name = abrupt.session.session_name
    prompt = '\001%s\002' % info('\002>>> \001')
    if session_name != "default":
      if abrupt.session.should_save():
        prompt = '\001%s\002 ' % error('\002'+session_name+'\001') + prompt
      else:
        prompt = '\001%s\002 ' % warning('\002'+session_name+'\001') + prompt
    return prompt

class AbruptInteractiveConsole(code.InteractiveConsole):
  re_print_alias = re.compile(r'^p\s(.*)')
  def push(self, line):
    if self.re_print_alias.match(line):
      line = self.re_print_alias.sub(r'print \1', line)
    code.InteractiveConsole.push(self, line)

def help(obj=None):
  if not obj:
    print """Welcome to Abrupt!

If this is your first time using Abrupt, you should check the
quickstart at http://securusglobal.github.com/Abrupt/.

Here are the basic functions of Abrupt, type 'help(function)'
for a complete description of these functions:
  * proxy: Start a HTTP proxy on port 8080.
  * create: Create a HTTP request based on a URL.
  * inject: Inject or fuzz a request.

Abrupt have few classes which worth having a look at, typing 'help(class)':
  * Request
  * Response
  * RequestSet

Please, report any bug or comment to tw@securusglobal.com"""
  else:
    pydoc.help(obj)   
 
def interact(local_dict=None):
  abrupt_builtins = __import__("all", globals(), locals(), ".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  __builtin__.__dict__["help"] = help
  __builtin__.__dict__["python_help"] = pydoc.help

  banner = """   _   _                  _   
  /_\ | |__ _ _ _  _ _ __| |_ 
 / _ \| '_ \ '_| || | '_ \  _|
/_/ \_\_.__/_|  \_,_| .__/\__|
                 """ + abrupt.__version__ + """|_|"""
  
  # Parse arguments
  try:
    opts = getopt.getopt(sys.argv[1:], "s:bhlv")
    for opt, param in opts[0]:
      if opt == "-h":
        _usage()
      elif opt == "-s":
        abrupt.session.session_name = param
      elif opt == "-l":
        abrupt.session.list_sessions()
        sys.exit(0)
      elif opt == "-v":
        print "Abrupt %s, Copyright (c) 2011 Securus Global" % (abrupt.__version__,)
        sys.exit(0)
      elif opt == "-b":
        banner = "Abrupt %s" % abrupt.__version__
    if opts[1]: 
        _usage()
  except getopt.GetoptError:
    _usage()
  
  # First time setup
  if not abrupt.conf.check_config_dir():
    print "Generating SSL certificate..."
    abrupt.cert.generate_ca_cert()
    banner += "\nWelcome to Abrupt, type help() for more information"
  
  # Could we find the payloads?
  if not abrupt.injection.payloads:
    print warning("No payload found for the injection, check abrupt/payloads")

  # Load user configuration, if any
  conf.load()

  # Import config from the environment
  conf.import_env()

  # Load the session, session configuration takes precedence 
  # over global configuration. There is no condition, by default, 
  # load the "default" session.
  abrupt.session.load_session()

  # Insert provided local variables (only used when scripted)
  if local_dict:
    abrupt.session.session_dict.update(local_dict)

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
        m = re.match(r"([\w\[\]]+(\.[\w\[\]]+)*)\.(\w*)", text)
        if m: 
          expr, attr = m.group(1, 3)
        else:
          return
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

    readline.set_completer_delims(" \t\n`~!@#$%^&*()-=+{}\\|;:'\",<>/?")
    readline.set_completer(AbruptCompleter().complete)
    readline.parse_and_bind("tab: complete")
    _load_history() 

  # Hooked window resizing
  _update_term_width(None, None)
  signal.signal(signal.SIGWINCH, _update_term_width)

  # And run the interpreter!
  sys.ps1 = ColorPrompt()
  atexit.register(abrupt.session.store_session)
  aci = AbruptInteractiveConsole(abrupt.session.session_dict)
  aci.interact(banner)

