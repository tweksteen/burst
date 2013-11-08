import os
import cPickle
import datetime
import glob
import types
import gzip
import operator
import __builtin__

from burst.conf import conf, SESSION_DIR, ARCHIVE_DIR
from burst.http import Request, RequestSet, history
from burst.color import *

session_name = "default"
session_dict = {}
session_readonly = False
last_save = None

def reset_last_save():
  global last_save
  last_save = datetime.datetime.now()

def should_save():
  delta_t = datetime.datetime.now() - last_save
  return (delta_t > datetime.timedelta(minutes=20) and not session_readonly)

def clear_session():
  for k in session_dict:
    if k != "__builtins__" and k in __builtin__.__dict__:
      del __builtin__.__dict__[k]
  session_dict.clear()
  history.clear()
  conf.__init__()
  conf.load()

def load_session():
  global history
  d = os.path.join(SESSION_DIR, session_name)
  if os.path.exists(d):
    fs = sorted(glob.glob(d + "/*"))
    if fs:
      fn = fs[-1]
      print "Loading", os.path.basename(fn)
      f = open(fn, "rb")
      v = cPickle.load(f)
      if "__history" in v:
        history.extend(v["__history"])
        del v["__history"]
      if "__conf" in v:
        conf.import_dict(v["__conf"])
        del v["__conf"]
      session_dict.update(v)
      __builtin__.__dict__.update(session_dict)
  else:
    os.mkdir(d, 0700)
  reset_last_save()

def autosave_session():
  if conf.autosave and session_name != "default" and not session_readonly:
    save()

def save(force=False):
  """ Save the current session.
  By default, this function is automatically called when the session
  is terminated (either by switching session (ss) or exiting Burst)
  except is the session is "default" or if conf.autosave is False.

  See also: ss, lss, conf.autosave.
  """
  if not isinstance(force, bool):
    print error("""The force parameter should be a boolean. """
                """Are you looking for switch_session?""")
    return
  if session_name == "default" and not force:
    print error("""It is usually a bad idea to save your data in the default session,\n"""
                """you should create another session with switch_session('my_session').\n"""
                """If you are sure, use save(force=True)""")
    return
  if session_readonly and not force:
    print error("""This session is read-only.\n"""
                """To overwrite it, use save(force=True)""")
    return
  d = os.path.join(SESSION_DIR, session_name)
  to_save = session_dict.copy()
  to_save["__conf"] = conf
  to_save["__history"] = history
  if "__builtins__" in to_save:
    del to_save["__builtins__"]
  for k in to_save.keys():
    if type(to_save[k]) in (types.TypeType, types.ClassType, types.ModuleType, types.FunctionType, types.NoneType):
      del to_save[k]
  if not os.path.exists(d):
    os.mkdir(d, 0700)
  n = datetime.datetime.now().strftime("%Y-%m-%dT%H%M.p")
  print "Saving session..."
  f = open(os.path.join(d, n), "wb")
  try:
    cPickle.dump(to_save, f, -1)
  except cPickle.PicklingError, e:
    print "Unable to save the session:"
    print e
  reset_last_save()
  f.close()

def archive(name=None):
  if not name:
    name = session_name
  to_archive = [v for k, v in session_dict.items() if isinstance(v, Request)]
  for rs in [v for k, v in session_dict.items() if isinstance(v, RequestSet)]:
    to_archive.extend(rs)
  to_archive.extend(history)
  output = ""
  for r in to_archive:
    response = str(r.response) if r.response else ""
    output += "\n".join((str(r), response))
    output += "\n" + "=" * 80 + "\n"
  f_name = name + "-" + datetime.datetime.now().strftime("%Y-%m-%dT%H%M.txt.gz")
  full_path = os.path.join(ARCHIVE_DIR, f_name)
  f = gzip.open(full_path, "w")
  f.write(output)
  f.close()
  print "Archived under", full_path

def switch_session(name="default"):
  """ Switch session.
  The current session will be saved (if not default)
  and the new will be loaded if it exists or created.
  If the current session is saved, its context will
  not appear in the new one.

  See also: save, lss.
  """
  global session_name
  if name == session_name: return
  if session_name != "default":
    if conf.autosave and not session_readonly:
      save()
    clear_session()
  session_name = name
  load_session()

ss = switch_session

def list_sessions():
  """ List sessions.
  List the existing sessions.

  See also: ss, save.
  """
  print "Existing sessions:"
  sessions = []
  for s in os.listdir(SESSION_DIR):
    if os.path.isdir(os.path.join(SESSION_DIR, s)):
      last_used = sorted(glob.glob(os.path.join(SESSION_DIR, s, "*")))
      d = ""
      if last_used:
        try:
          d = datetime.datetime.strptime(os.path.basename(last_used[-1]),
                                         "%Y-%m-%dT%H%M.p")
          # TODO, add size (os.stat().st_size)
        except ValueError:
          pass
      sessions.append((s, d))
  shift = max([len(x[0]) for x in sessions])
  print "\n".join([ "  " + s.ljust(shift) + " " + str(d) for s,d in
                         sorted(sessions, key=operator.itemgetter(0))])

lss = list_sessions
