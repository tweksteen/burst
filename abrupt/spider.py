import re
import urlparse
from collections import deque

from abrupt.http import RequestSet
from abrupt.utils import e, clear_line
from abrupt.color import *

try:
  import lxml.html
  has_lxml = True
except ImportError:
  has_lxml = False

def _follow_redirect(r):
  if r.response and r.response.status in ('301', '302'):
    return [r.follow(),]
  return []

def _get_links(r):
  new_reqs = []
  if not has_lxml:
    raise Exception("To use the spider, you need lxml")
  root = lxml.html.fromstring(r.response.content)
  base_tag = root.xpath('//base')
  if base_tag and base_tag[0].get('href'):
    base = base_tag[0].get(["href"])
  else:
    base = r.url
  links = [ x.get("href") for x in root.xpath("//a|//area") if x.get('href')]
  for l in links:
    try:
      l.encode('ascii')
    except UnicodeEncodeError:
      l = e(l.encode('utf-8'), safe='/')
    url_p = urlparse.urlparse(l)
    if url_p.scheme in ('http', 'https'):
      new_reqs.append(c(l))
    elif url_p.scheme in ('javascript', 'mailto', '#'): 
      continue
    elif url_p.scheme == '' and url_p.path:
      nr = r.copy()
      n_path = urlparse.urljoin(base, l)
      nr.url = urlparse.urlunparse(urlparse.urlparse(r.url)[:2] + urlparse.urlparse(n_path)[2:])
      new_reqs.append(nr)
    else:
      if url_p.scheme not in ("ftp", "irc", "xmpp", "mms"):
        print "UNKNOWN PROTOCOL Miam!?:" + l, url_p.scheme
  return RequestSet(new_reqs)

def spider(r_init, max=-1, post_func=None, hosts=None):
  """ 
  Spider a request by following some links.
  
  r_init    - The initial request
  max       - The maximum of request to execute
  post_func - A hook to be executed after each new page fetched
  hosts     - A lists of authorised hosts to spider on. By default,
              only the hostname of r_init is allowed.
  """
  q = deque([r_init,])
  checked = []
  nb = 0
  hs = [r_init.hostname,]
  if hosts:
    hs += hosts 
  try:
    while nb != max and q:
      to_add = []
      r = q.popleft()
      print str(len(checked)) + "/" + str(len(q)),
      clear_line()
      r()
      if r.response.content_type:
        if re.match(r'text/html', r.response.content_type):
          to_add += _follow_redirect(r)
          to_add += _get_links(r)
        else:
          print "\nIgnoring", r.response.content_type
      checked.append(r)
      if post_func: 
        post_func(r)
      for nr in to_add:
        if nr.hostname not in hs:
          continue
        if any(nr == rc for rc in checked + list(q)):
          continue
        q.append(nr)
      nb += 1
  except KeyboardInterrupt:
    pass
  return RequestSet(checked)
   
s = spider
