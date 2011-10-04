import re
import HTMLParser 

from abrupt.color import *

try:
  from BeautifulSoup import BeautifulSoup
  has_soup=True
except ImportError:
  has_soup=False

class Generic:

  html_keywords = [r'Error', r'Warning', r'SQL', r'LDAP', r'Failure']
  js_keywords = [r'password', r'credential']

  def __init__(self):
    self.html_patterns = [re.compile(s, re.I) for s in self.html_keywords]
    self.js_patterns = [re.compile(s, re.I) for s in self.js_keywords]

  def parse_html(self, r):
    alerts = []
    if has_soup:
      try:
        content = BeautifulSoup(r.response.content).findAll(text=True)
        content = ''.join([ x for x in content if x.parent.name != "script" ])
      except HTMLParser.HTMLParseError:
        alerts.append(stealthy("reponse.content-type says html but unable to parse"))
        return alerts
    else:
      content = r.response.content
    for e in self.html_patterns:
      if e.search(content):
        if has_soup:
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
            
  def parse(self, r):
    if r.response and r.response.content:  
      if r.response.is_html:
        return self.parse_html(r)
      if r.response.is_javascript:
        return self.parse_javascript(r)
    return []
