from abrupt.color import *

class AbruptException(Exception):
  def __repr__(self):
    return "<{}: {}>".format(error(self.__class__.__name__), str(self))

class UnableToConnect(AbruptException):
  def __init__(self, message="Unable to connect to the server"):
    AbruptException.__init__(self, message)

class NotConnected(AbruptException):
  def __init__(self, junk):
    self.junk = junk
    AbruptException.__init__(self, "Unable to read the request from the client")
  def __str__(self):
    return self.message + " [" + str(self.junk) + "]"

class BadStatusLine(AbruptException):
  def __init__(self, junk):
    self.junk = junk
    AbruptException.__init__(self, "The host did not return a correct banner")
  def __str__(self):
    return self.message + " [" + str(self.junk) + "]"

class ProxyError(AbruptException):
  pass

class CertError(AbruptException):
  pass

class PayloadNotFound(AbruptException): 
  pass

class NoInjectionPointFound(AbruptException): 
  pass

class NonUniqueInjectionPoint(AbruptException): 
  pass

class CookieException(AbruptException):
  pass

