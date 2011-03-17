import urllib
import urlparse
import httplib
import traceback
import functools

from abrupt.http import RequestSet

def _inject_query(r, payloads):
  rs = []
  parsed_url = urlparse.urlparse(r.url)
  i_pts = urlparse.parse_qs(r.query, True)
  for i_pt in i_pts:
    nq = i_pts.copy()
    for p in payloads:
      nq[i_pt] = [e(p),]
      s = list(parsed_url)
      s[4] = urllib.urlencode(nq, True)
      r_new = r.copy()
      r_new.url = urlparse.urlunparse(s)
      rs.append(r_new)
  return rs

def inject(r, payloads):
  if not payloads:
    payloads = g()
  return RequestSet(_inject_query(r, payloads))

i = functools.partial(inject, payloads=None)

def g():
  return  ['\'', '\' --', '><script>alert(1)</script>', '-1', '2-1']

def e(s):
  return urllib.quote_plus(s)  


def test():
  from StringIO import StringIO
  from abrupt.http import Request
  r = Request(StringIO("""GET http://www.exalead.com/search/web/results/?q=test HTTP/1.1
Host: www.exalead.com
User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.15) Gecko/20110304 Firefox/3.6.15

"""))
  rs = i(r)
  print rs
  rs()
  print rs

if __name__ == '__main__':
  test()
