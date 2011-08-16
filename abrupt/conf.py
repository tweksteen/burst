import os
import os.path
import pickle

CONF_DIR = os.path.expanduser("~/.abrupt/")
CERT_DIR = os.path.join(CONF_DIR, "certs")
SESSION_DIR = os.path.join(CONF_DIR, "sessions")

def check_config_dir():
  if not os.path.exists(CONF_DIR):
    os.mkdir(CONF_DIR, 0700)
    if not os.path.exists(CERT_DIR):
      os.mkdir(CERT_DIR, 0700)
      if not os.path.exists(os.path.join(CERT_DIR, "sites")):
        os.mkdir(os.path.join(CERT_DIR, "sites"), 0700)
    if not os.path.exists(SESSION_DIR):
      os.mkdir(SESSION_DIR, 0700)
    return False
  return True

class Configuration():
  def __init__(self):
    if "http_proxy" in os.environ:
      self.proxy = os.environ["http_proxy"]
      print "Using", self.proxy, "as proxy" 
    else:
      self.proxy = None
    self.autosave = True

conf = Configuration()
