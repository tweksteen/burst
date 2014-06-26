from burst.color import *

class BurstException(Exception):
  def __repr__(self):
    return "<{}: {}>".format(error(self.__class__.__name__), str(self))

class UnableToConnect(BurstException):
  def __init__(self, message="Unable to connect to the server"):
    BurstException.__init__(self, message)

class NotConnected(BurstException):
  def __init__(self, junk):
    self.junk = junk
    BurstException.__init__(self, "Unable to read the request from the client")
  def __str__(self):
    return self.message + " [" + str(self.junk) + "]"

class BadStatusLine(BurstException):
  def __init__(self, junk):
    self.junk = junk
    BurstException.__init__(self, "The host did not return a correct banner")
  def __str__(self):
    return self.message + " [" + str(self.junk) + "]"

class ProxyError(BurstException):
  pass

class CertError(BurstException):
  pass

class PayloadNotFound(BurstException):
  pass

class NoInjectionPointFound(BurstException):
  pass

class NonUniqueInjectionPoint(BurstException):
  pass

class CookieException(BurstException):
  pass

