import HTMLParser
from urlparse import urlparse

class AHTMLParser(HTMLParser.HTMLParser):
  
  def __init__(self):
    HTMLParser.HTMLParser.__init__(self)
    self.links = []
    self.comments = []

  def handle_starttag(self, tag, attrs):
    dattrs = dict(attrs)
    if tag == "a":
      if "href" in dattrs:
        self.links.append(dattrs["href"])

  def handle_comment(self, data):
    self.comments.append(data)

def get_links(content, hostname=None):
  c = AHTMLParser()
  c.feed(content)
  if not hostname:
    return c.links
  return [l for l in c.links if urlparse(l).hostname == hostname]

def get_comments(content):
  c = AHTMLParser()
  c.feed(content)
  return c.comments
 
