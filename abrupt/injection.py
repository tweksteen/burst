import re
import urlparse
import glob
import os.path
import json

from abrupt.http import Request, RequestSet
from abrupt.exception import *
from abrupt.color import *
from abrupt.cookie import Cookie
from abrupt.utils import encode, parse_qs, urlencode

payloads = { "default": [] }
for f_name in glob.glob(os.path.join(os.path.dirname(__file__), "payloads/*")):
  k = os.path.basename(f_name)
  plds = open(f_name).read().splitlines()
  payloads[k] = plds

for k in ('sqli', 'xss', 'cmd', 'dir', 'misc'):
  if k in payloads:
    payloads["default"].extend(payloads[k])

def _get_payload(p):
  try:
    if isinstance(p, list):
      return p
    else:
      return payloads[p]
  except KeyError:
    raise PayloadNotFound("Possible values are: " + ", ".join(payloads.keys()))

def _inject_query(r, value, pds, pre_func):
  rs = []
  i_pts = parse_qs(r.query)
  if value in i_pts:
    nq = i_pts.copy()
    parsed_url = urlparse.urlparse(r.url)
    for p in pds:
      nq[value] = [pre_func(p), ]
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
      nc[value] = [pre_func(p), ]
      n_content = urlencode(nc)
      r_new = r.copy()
      r_new.raw_content = n_content
      r_new.content = n_content
      r_new.injection_point = value
      r_new.payload = p
      r_new.update_content_length()
      rs.append(r_new)
  return rs

def _inject_json(r, value, pds, pre_func):
  rs = []
  try:
    x = json.loads(r.content)
  except (ValueError, TypeError):
    return rs
  if x.has_key(value):
    n_json = x.copy()
    for p in pds:
      n_json[value] = pre_func(p)
      r_new = r.copy()
      r_new.raw_content = json.dumps(n_json)
      r_new.content = r_new.raw_content
      r_new.injection_point = value
      r_new.payload = p
      r_new.update_content_length()
      rs.append(r_new)
  return rs

def _inject_cookie(r, value, pds, pre_func):
  rs = []
  cookies = r.cookies
  for i, c in enumerate(cookies):
    if c.name == value:
      break
  else:
    return rs
  c = Cookie(value, "")
  for p in pds:
    c.value = pre_func(p)
    cookies[i] = c
    r_new = r.copy()
    r_new.remove_header('Cookie')
    r_new.add_header('Cookie', "; ".join([str(x) for x in cookies]))
    r_new.injection_point = value
    r_new.payload = p
    rs.append(r_new)
  return rs

def _inject_at(r, offset, payloads, pre_func=encode, choice=None):
  rs = []
  orig = str(r)
  pds = _get_payload(payloads)
  if not pre_func: pre_func = lambda x: x
  if isinstance(offset, (list, tuple)):
    off_b, off_e = offset
  elif isinstance(offset, basestring):
    ct = str(r).count(offset)
    if ct > 1:
      if not choice or choice > ct:
        raise NonUniqueInjectionPoint("The pattern is not unique in" + \
                                      " the request, use choice<=" + str(ct))
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
    off_b, off_e = idx, idx + len(offset)
  else:
    off_b = off_e = offset
  for p in pds:
    ct = orig[:off_b] + pre_func(p) + orig[off_e:]
    ct = re.sub("Content-Length:.*\n", "", ct)
    r_new = Request(ct, hostname=r.hostname, port=r.port, use_ssl=r.use_ssl)
    r_new.update_content_length()
    r_new.injection_point = "@" + str(offset)
    r_new.payload = p
    rs.append(r_new)
  return rs

def _inject_to(r, value, payloads, pre_func=None):
  pds = _get_payload(payloads)
  if not pre_func:
    pre_func = lambda x: encode(x)
  rqs = RequestSet(_inject_query(r, value, pds, pre_func))
  if r.method in ("POST", "PUT"):
    rqs += RequestSet(_inject_post(r, value, pds, pre_func))
  if r.has_header("Cookie"):
    rqs += RequestSet(_inject_cookie(r, value, pds, pre_func))
  rqs += RequestSet(_inject_json(r, value, pds, pre_func))
  if not rqs:
    raise NoInjectionPointFound()
  return rqs

def _inject_multi(r, method, target, payloads, **kwds):
  if isinstance(r, Request):
    return method(r, target, payloads, **kwds)
  elif isinstance(r, RequestSet):
    return RequestSet(reduce(lambda x, y: x + y,
           [ method(ro, target, payloads, **kwds) for ro in r ]))


def inject(r, to=None, at=None, payloads="default", **kwds):
  """ Inject a request.

  This function will create a RequestSet from a Request where a part
  of the request is replaced with some payload. There is two ways to use
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

  payloads could either be a list of the payloads to inject or a key
  of the global dictionnary 'payloads'.

  Before being injected, each payload pass through the pre_func function
  which is by default 'encode'.

  See also: payloads, inject_all, find_injection_points
  """
  rqs = RequestSet()
  if not to and not at:
    print error("I need some help here. Where should I inject? " + \
                "Try 'help(inject)'")
  elif to and at:
    print error("Wow, too many parameters. It is either 'to' or 'at'.")
  elif to:
    if isinstance(to, (list, tuple)):
      for t in to:
        rqs.extend(_inject_multi(r, _inject_to, t, payloads, **kwds))
    else:
      rqs.extend(_inject_multi(r, _inject_to, to, payloads, **kwds))
  elif at:
    if isinstance(at, (list, tuple)):
      for a in at:
        rqs.extend(_inject_multi(r, _inject_at, a, payloads, **kwds))
    else:
      rqs.extend(_inject_multi(r, _inject_at, at, payloads, **kwds))
  return rqs

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
    i_pts = [ c.name for c in r.cookies]
    if i_pts:
      ips.extend(i_pts)
  try:
    i_pts = json.loads(r.content)
    ips.extend(i_pts.keys())
  except (ValueError,TypeError):
    pass
  return ips

fip = find_injection_points

def inject_all(r, payloads="default"):
  ips = find_injection_points(r)
  if ips:
    return reduce(lambda x, y: x + y, [i(r, to=ip, payloads=payloads) for ip in ips])
  return RequestSet()

i_all = inject_all

def fuzz_headers(r, payloads="default"):
  print "TODO: adapt payloads for each header tested"
  rs = []
  for i, e in enumerate(r.headers):
    k, v = e
    pds = _get_payload(payloads)
    for p in pds:
      r_new = r.copy()
      h_new = (k, p)
      r_new.headers[i] = h_new
      r_new.injection_point = k
      r_new.payload = p
      rs.append(r_new)
  return RequestSet(rs)

f_h = fuzz_headers
