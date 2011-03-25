import __builtin__

def interact():
  abrupt_builtins = __import__("all", globals(), locals(), ".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  import abrupt
  import abrupt.conf
  banner = """   _   _                  _   
  /_\ | |__ _ _ _  _ _ __| |_ 
 / _ \| '_ \ '_| || | '_ \  _|
/_/ \_\_.__/_|  \_,_| .__/\__|
                 """ + abrupt.__version__ + """|_|"""
  
  if not abrupt.conf.check_config_dir():
    print "Generating SSL certificate..."
    abrupt.proxy.generate_ca_cert()
  try:
    import IPython
    if not len(abrupt.injection.payloads):
      from abrupt.color import warning
      print warning("No payload found for the injection, check abrupt/payloads")
    ipshell = IPython.Shell.IPShellEmbed(banner=banner)
    ipshell()
  except ImportError:
    import code
    print banner
    print "Using classic interpreter, for a better experience, install Ipython"
    code.interact()

