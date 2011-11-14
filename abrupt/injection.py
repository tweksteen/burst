import re
import urlparse
import glob
import os.path
import Cookie

from abrupt.http import Request, RequestSet
from abrupt.color import *
from abrupt.utils import encode, parse_qs, parse_qsl, urlencode

payloads = {}
for f_name in glob.glob(os.path.join(os.path.dirname(__file__), "payloads/*")):
  k = os.path.basename(f_name)
  plds = open(f_name).read().splitlines()
  payloads[k] = plds

class PayloadNotFound(Exception): pass
class NoInjectionPointFound(Exception): pass
class NonUniqueInjectionPoint(Exception): pass


def _get_payload(p):
  try:
    if isinstance(p, list):
      return p
    else:
      return payloads[p]
  except KeyError:
    raise PayloadNotFound("Possible values are: " +", ".join(payloads.keys()))

def _inject_query(r, value, pds, pre_func):
  rs = []
  i_pts = parse_qs(r.query)
  if value in i_pts:
    nq = i_pts.copy()
    parsed_url = urlparse.urlparse(r.url)
    for p in pds:
      nq[value] = [pre_func(p),]
      s = list(parsed_url)
      s[4] = urlencode(nq)
      r_new = r.copy()
      r_new.url = urlparse.urlunparse(s)
      r_new.injection_point = value
      r_new.payload = p
      rs.append(r_new)
  return rs

def _inject_post(r, value, pds, pre_func):
  rs = []
  i_pts = parse_qs(r.content)
  if value in i_pts:
    nc = i_pts.copy()
    for p in pds:
      nc[value] = [pre_func(p),]
      n_content = urlencode(nc)
      r_new = r.copy()
      r_new.content = n_content
      r_new.injection_point = value
      r_new.payload = p
      r_new._update_content_length()
      rs.append(r_new)
  return rs

def _inject_cookie(r, value, pds, pre_func):
  rs = []
  b = r.cookies
  n_headers = [(x,v) for x,v in r.headers if x.title() != "Cookie"]
  if value in b:
    nb = Cookie.SimpleCookie()
    nb.load(b.output(header=""))
    for p in pds:
      nb[value] = pre_func(p)
      r_new = r.copy()
      nbs = nb.output(header="", sep=";").strip()
      r_new.headers = n_headers + [("Cookie", nbs),]
      r_new.injection_point = value
      r_new.payload = p
      rs.append(r_new)
  return rs

def _inject_at(r, offset, payload, pre_func=encode, choice=None):
  rs = []
  orig = str(r)
  pds = _get_payload(payload)
  if not pre_func: pre_func = lambda x:x
  if isinstance(offset, (list,tuple)): 
    off_b, off_e = offset
  elif isinstance(offset, basestring):
    ct = str(r).count(offset)
    if ct > 1:
      if not choice or choice > ct:
        raise NonUniqueInjectionPoint("The pattern is not unique in the request, use choice<=" + str(ct))
      else:
        c_off = 0
        for i in range(choice):
          idx = str(r)[c_off:].find(offset)
          c_off += idx + 1 
        idx = c_off - 1 
    elif ct < 1: 
      raise NoInjectionPointFound("Could not find the pattern")
    else:
      idx = str(r).find(offset)
    off_b, off_e = idx, idx+len(offset)
  else:
    off_b = off_e = offset
  for p in pds:
    ct = orig[:off_b] + pre_func(p) + orig[off_e:]
    ct = re.sub("Content-Length:.*\n", "", ct)
    r_new = Request(ct, hostname=r.hostname, port=r.port, use_ssl=r.use_ssl)
    r_new._update_content_length()
    r_new.injection_point = "@" + str(offset)
    r_new.payload = p
    rs.append(r_new)
  return rs

def _inject_to(r, value, payload, pre_func=None):
  pds = _get_payload(payload)
  if not pre_func:
    pre_func = lambda x:encode(x)
  rqs = RequestSet(_inject_query(r, value, pds, pre_func))
  if r.method in ("POST", "PUT"):
    rqs += RequestSet(_inject_post(r, value, pds, pre_func))
  if r.has_header("Cookie"):
    rqs += RequestSet(_inject_cookie(r, value, pds, pre_func))
  if not rqs:
    raise NoInjectionPointFound()
  return rqs 
  
def inject(r, to=None, at=None, payload="default", **kwds):
  """ Inject a request.

  This function will create a RequestSet from a Request where a part
  of the latter is replaced with some payload. There is two way to use
  this function, either to inject the value of a parameter or to inject
  at a specific location.

  When used with the 'to' parameter, Abrupt will lookup the value
  in the query string, the request content and the cookies. It will
  then replace the value of the parameter with the payloads. If no
  valid injection point is found, an error is raised.

  When used with the 'at' parameter, Abrupt will lookup the string in the 
  whole request text and replace it with the payloads. If no valid injection
  point is found, an error is raised. If the string is found more than
  once, the function will suggest to provide the 'choice' integer keyword.

  payload could either be a list of the payloads to inject or a key
  of the global dictionnary payloads.

  Before being injected, each payload pass through the pre_func function
  which is by default encode.

  See also: payloads, inject_all, find_injection_points
  """
  if not to and not at:
    print error("I need some help here. Where should I inject? " +\
                "Try 'help(inject)'")
    return
  if to and at:
    print error("Wow, too many parameters. It is either 'to' or 'at'.")
    return
  if to:
    if isinstance(r, Request):
      return _inject_to(r, to, payload, **kwds)
    elif isinstance(r, RequestSet):
      return RequestSet(reduce(lambda x,y: x+y,
             [ _inject_to(ro, to, payload, **kwds) for ro in r ]))
  if at:
    if isinstance(r, Request):
      return RequestSet(_inject_at(r, at, payload, **kwds))
    elif isinstance(r, RequestSet):
      return RequestSet(reduce(lambda x,y: x+y,
             [ _inject_at(ro, at, payload, **kwds) for ro in r ]))

i = inject

def find_injection_points(r):
  """Find valid injection points.

  This functions returns the injection points that could
  be used by i().
  """
  ips = []
  if r.query:
    i_pts = parse_qs(r.query)
    if i_pts:
      ips.extend(i_pts)
  if r.content:
    i_pts = parse_qs(r.content)
    if i_pts:
      ips.extend(i_pts)
  if r.cookies:
    i_pts = r.cookies.keys()
    if i_pts:
      ips.extend(i_pts)
  return ips

fip = find_injection_points

def inject_all(r, payload="default"):
  ips = find_injection_points(r)
  if ips:
    return reduce(lambda x,y:x+y, [ i(r, to=ip, payload=payload) for ip in ips])
  return RequestSet()

i_all = inject_all

def fuzz_headers(r, payload):
  print "TODO: adapt payload for each header tested"
  rs = []
  for i, e in enumerate(r.headers):
    k, v = e 
    pds = _get_payload(payload)
    for p in pds:
      r_new = r.copy()
      h_new = (k, p)
      r_new.headers[i] = h_new
      rs.append(r_new)
  return RequestSet(rs)
    
f_h = fuzz_headers
