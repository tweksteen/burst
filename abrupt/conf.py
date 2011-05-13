import os
import os.path
import pickle

CONF_DIR = os.path.expanduser("~/.abrupt/")

def check_config_dir():
  if not os.path.exists(CONF_DIR):
    os.mkdir(CONF_DIR, 0700)
    if not os.path.exists(os.path.join(CONF_DIR, "certs")):
      os.mkdir(os.path.join(CONF_DIR, "certs"), 0700)
    if not os.path.exists(os.path.join(CONF_DIR, "save")):
      os.mkdir(os.path.join(CONF_DIR, "save"), 0700)
    return False
  return True

def save(obj, name):
  """Save an object in your user directory.
  See also: load
  """
  p = os.path.join(CONF_DIR, "save", name)
  f = open(p, "w")
  pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
  f.close()
  print "Saved in", p


def load(name=None):
  """Load an object saved with save(). If name is
  empty, display the possible files.
  """
  if name:
    p = os.path.join(CONF_DIR, "save", name)
    f = open(p, "r")
    obj = pickle.load(f)
    f.close()
    return obj
  else:
    p = os.path.join(CONF_DIR, "save")
    print os.listdir(p)
