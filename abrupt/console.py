import __builtin__

def interact():
  abrupt_builtins = __import__("all", globals(), locals(), ".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  import abrupt
  banner = """   _   _                  _   
  /_\ | |__ _ _ _  _ _ __| |_ 
 / _ \| '_ \ '_| || | '_ \  _|
/_/ \_\_.__/_|  \_,_| .__/\__|
           v""" + abrupt.__version__ + """|_|"""
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

