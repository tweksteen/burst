import os
import os.path

CONF_DIR = os.path.expanduser("~/.abrupt/")

def check_config_dir():
  if not os.path.exists(CONF_DIR):
    os.mkdir(CONF_DIR, 0700)
    if not os.path.exists(os.path.join(CONF_DIR, "certs/")):
      os.mkdir(os.path.join(CONF_DIR, "certs/"), 0700)
    return False
  return True
