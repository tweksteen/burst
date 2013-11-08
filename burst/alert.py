import re

from burst.color import *

try:
  import lxml.html
  has_lxml = True
except ImportError:
  has_lxml = False

class NullAlerter:
  def analyse_request(self, r):
    return []
  def analyse_response(self, r):
    return []

class GenericAlerter:
  html_keywords = [r'Error', r'Warning', r'SQL', r'LDAP', r'Failure']
  js_keywords = [r'password', r'credential']

  def __init__(self):
    self.html_patterns = [re.compile(s, re.I) for s in self.html_keywords]
    self.js_patterns = [re.compile(s, re.I) for s in self.js_keywords]

  def cookies_in_body(self, r):
    alerts = []
    for c in r.response.cookies:
      if c.value in r.response.content:
        alerts.append(error("response.content matches the cookie " + c.value))
    return alerts

  def parse_html(self, r):
    alerts = []
    if has_lxml:
      try:
        root = lxml.html.fromstring(r.response.content)
        content = ''.join([x for x in root.xpath("//text()") if
                            x.getparent().tag != "script"])
      except UnicodeDecodeError:
        alerts.append(stealthy("reponse.content-type says html but " \
                               "unable to parse"))
        return alerts
      except lxml.etree.ParserError:
        return alerts
    else:
      content = r.response.content
    for e in self.html_patterns:
      if e.search(content):
        if has_lxml: # We are more confident of what we've found
          alerts.append(error("response.content matches " + e.pattern))
        else:
          alerts.append(warning("response.content matches " + e.pattern))
    return alerts

  def parse_javascript(self, r):
    alerts = []
    for e in self.js_patterns:
      if e.search(r.response.content):
        alerts.append(error("response.content matches " + e.pattern))
    return alerts

  def analyse_request(self, r):
    return []

  def analyse_response(self, r):
    if r.response and r.response.content:
      if r.response.is_html:
        return self.parse_html(r) + self.cookies_in_body(r)
      if r.response.is_javascript:
        return self.parse_javascript(r)
    return []


class RequestKeywordAlerter(GenericAlerter):

  def __init__(self, words):
    GenericAlerter.__init__(self)
    self.keywords_patterns = [re.compile(s, re.I) for s in words]

  def analyse_request(self, r):
    alerts = []
    alerts.extend(GenericAlerter.analyse_request(self, r))
    for e in self.keywords_patterns:
      if e.search(r.content):
        alerts.append(error("request.content matches " + e.pattern))
    return alerts


class InjectedAlerter(GenericAlerter):

  def analyse_response(self, r):
    alerts = []
    if not hasattr(r, "payload"):
      return alerts
    if "<b>burst</b>" in r.payload and r.response.is_html and \
       "<b>burst</b>" in r.response.content:
      alerts.append(error("response.content includes <b>burst</b>"))

def scan(rs):
  a = InjectedAlerter()
  for i,r in enumerate(rs):
    alerts = a.analyse_response(r)
    if alerts:
      print i, repr(r), repr(r.response)
      for alert in alerts:
        print "  " +  alert
