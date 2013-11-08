from burst.exception import CookieException

class Cookie:

  @classmethod
  def parse(cls, header, set_cookie=False):
    if set_cookie:
      if ";" in header:
        nvp, attributes = header.split(";", 1)
      else:
        nvp, attributes = header, ""
      if not "=" in nvp:
        raise CookieException("No '=' character in the cookie")
      name, value = [ x.strip() for x in nvp.split("=", 1) ]
      return Cookie(name, value, attributes)
    else:
      nvps = header.split(";")
      cookies = []
      for nvp in nvps:
        if not "=" in nvp:
          raise CookieException("No '=' character in the cookie")
        name, value = [ x.strip() for x in nvp.split("=", 1) ]
        cookies.append(Cookie(name, value))
      return cookies

  def __init__(self, name, value, attributes=""):
    self.name = name
    self.value = value
    self.attributes = attributes

  def __repr__(self):
    return "<Cookie: " + self.name + "=" + self.value + " | " + self.attributes + ">"

  def __str__(self):
    return self.name + "=" + self.value

