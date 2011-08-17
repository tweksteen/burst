from abrupt.http import RequestSet

class History(RequestSet):
  
  def _enabled(self):
    if not conf.history:
      raise Exception("History not enabled. Set conf.history = True")

  def __repr__(self):
    self._enabled()
    return RequestSet.__repr__(self)
  
  def __str__(self):
    self._enabled()
    return RequestSet.__str__(self)

history = History()
