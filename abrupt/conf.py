import os
import os.path
import pickle
import ConfigParser
import UserDict

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
    self.proxy = None
    self.autosave = True
    self.history = True
    self._values = ["proxy", "autosave", "history"]

  def __repr__(self):
    return str(self)

  def __str__(self):
    return "\n".join([ s+": "+str(getattr(self,s)) for s in self._values])

  def import_env(self):
   if "http_proxy" in os.environ:
    conf.proxy = os.environ["http_proxy"]
    print "Using", conf.proxy, "as proxy"

  def load(self):
    if os.path.exists(os.path.join(CONF_DIR, "abrupt.conf")):
      c = ConfigParser.RawConfigParser()
      c.read(os.path.join(CONF_DIR, "abrupt.conf"))
      if not c.has_section("abrupt"):
        raise Exception("Configuration file corrupted")
      if c.has_option("abrupt", "proxy"):
        self.proxy = c.get("abrupt", "proxy")
      if c.has_option("abrupt", "autosave"):
        self.autosave = c.getboolean("abrupt", "autosave")
      if c.has_option("abrupt", "history"):
        self.history = c.getboolean("abrupt", "history")
      
  def save(self):
    c = ConfigParser.RawConfigParser()
    c.add_section('abrupt')
    for s in self._values:
      p = getattr(self, s)
      if not p is None:
        c.set('abrupt', s, p)
    with open(os.path.join(CONF_DIR, "abrupt.conf"), "w") as f:
      c.write(f)

conf = Configuration()

