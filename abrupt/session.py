import os
import atexit
import cPickle
import datetime
import glob

from abrupt.conf import SESSION_DIR
from abrupt.color import *

session_name = "default"
session_dict = {}

def clear_session():
  session_dict.clear()

def load_session():
  d = os.path.join(SESSION_DIR, session_name)
  if os.path.exists(d):
    fs = sorted(glob.glob(d + "/*"))
    if not fs:
      return False
    fn = fs[-1]
    print "Loading", os.path.basename(fn)
    f = open(fn, "rb")
    v = cPickle.load(f)
    session_dict.update(v)
  else:
    os.mkdir(d, 0700)

def store_session(force=False):
  if session_name == "default" and not force:
    return 
  d = os.path.join(SESSION_DIR, session_name)
  to_save = session_dict.copy()
  if to_save.has_key("__builtins__"):
    del(to_save["__builtins__"])
  if not os.path.exists(d):
    os.mkdir(d, 0700)
  n = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.p")
  print "Saving session..."
  f = open(os.path.join(d, n), "wb")
  cPickle.dump(to_save, f, -1)
  f.close()
  
def save(obj=None, force=False):
  """ Save the current session.
  By default, this function is automatically called when the session 
  is terminated (either by switching session (ss) or exiting Abrupt) 
  except is the session is "default".

  See also: ss, lss.
  """
  if not force and session_name == "default":
    print error("""It is a bad idea to save your data in the default session, you should 
create another session with ss('my_session'). If you are sure, 
use save(force=True)""")
  if not obj:
    store_session(force=force)
  else:
    # Save a particular object?
    pass

def ss(name="default"):
  """ Switch session.
  The current session will be saved (if not default)
  and the new will be loaded if it exists or created.

  See also: save, lss.
  """
  global session_name
  print "TODO: check if we should clear the current session"
  if name == session_name: return
  if session_name != "default":
    store_session()
  session_name = name
  clear_session()
  load_session()
 
def lss():
  """ List sessions.
  List the existing sessions.
  
  See also: ss, save.
  """
  print "Existing sessions: " + ", ".join([ s for s in os.listdir(SESSION_DIR) 
                      if os.path.isdir(os.path.join(SESSION_DIR, s)) ])

def sd():
  """ Delete a session.
  Remove a session and any associated backup
  """
  pass
