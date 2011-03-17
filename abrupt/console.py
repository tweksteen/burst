import __builtin__

def interact():
  abrupt_builtins = __import__("all", globals(), locals(), ".").__dict__
  __builtin__.__dict__.update(abrupt_builtins)
  try:
    import IPython
    import abrupt
    from abrupt.color import success, great_success
    print success("~~--[ ") + great_success("Abrupt " + abrupt.__version__) + success(" ]--~~"),
    ipshell = IPython.Shell.IPShellEmbed()
    ipshell()
  except ImportError:
    import code
    print "Using classic interpreter, for a better experience, install Ipython"
    code.interact()


