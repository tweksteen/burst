import urllib
import urlparse
import httplib
import traceback
import functools
import glob
import os.path
import Cookie

from abrupt.http import RequestSet
from abrupt.color import *

payloads = {}
for f_name in glob.glob(os.path.join(os.path.dirname(__file__), "payloads/*")):
  k = os.path.basename(f_name)
  plds = open(f_name).read().splitlines()
  payloads[k] = plds

class PayloadNotFound(Exception): pass
class NoInjectionPointFound(Exception): pass

def e(s):
  return urllib.quote_plus(s)  

def ee(s):
  return e(e(s))

def d(s):
  return urllib.unquote_plus(s)

def _get_payload(name, kwds, default_payload):
  pds = []
  try:
    if name in kwds:
      if isinstance(kwds[name], list):
        pds = kwds[name]
      else:
        pds = payloads[kwds[name]]
    elif default_payload:
      pds = payloads[default_payload]
    return pds
  except KeyError:
    raise PayloadNotFound("Possible values are: " +", ".join(payloads.keys()))

def _inject_query(r, pre_func=e, default_payload=None, **kwds):
  rs = []
  parsed_url = urlparse.urlparse(r.url)
  i_pts = urlparse.parse_qs(r.query, True)
  for i_pt in i_pts:
    nq = i_pts.copy()
    pds = _get_payload(i_pt, kwds, default_payload)
    for p in pds:
      nq[i_pt] = [pre_func(p),]
      s = list(parsed_url)
      s[4] = urllib.urlencode(nq, True)
      r_new = r.copy()
      r_new.url = urlparse.urlunparse(s)
      r_new.payload = i_pt + "=" + p
      rs.append(r_new)
  return rs

def _inject_cookie(r, pre_func=e, default_payload=None, **kwds):
  rs = []
  b = r.cookies()
  n_headers = [(x,v) for x,v in r.headers if x != "Cookie"]
  for i_pt in b:
    nb = Cookie.SimpleCookie()
    nb.load(b.output(header=""))
    pds = _get_payload(i_pt, kwds, default_payload)
    for p in pds:
      nb[i_pt] = pre_func(p)
      r_new = r.copy()
      nbs =  nb.output(header="", sep=";").strip()
      print n_headers
      r_new.headers = n_headers + [("Cookie", nbs),]
      r_new.payload = i_pt + "=" + p
      rs.append(r_new)
  return rs
  

def _inject_post(r, pre_func=e, default_payload=None, **kwds):
  rs = []
  i_pts = urlparse.parse_qs(r.content, True)
  for i_pt in i_pts:
    nc = i_pts.copy()
    pds = _get_payload(i_pt, kwds, default_payload)
    for p in pds:
      nc[i_pt] = [pre_func(p),]
      n_content = urllib.urlencode(nc, True)
      r_new = r.copy()
      r_new.content = n_content
      r_new.payload = i_pt + "=" + p
      r_new._update_content_length()
      rs.append(r_new)
  return rs

def _inject_offset(r, offset, pre_func=e, default_payload=None, **kwds):
  rs = []
  orig = str(r)
  pds = _get_payload("", kwds, default_payload)
  if isinstance(offset, (list,tuple)): 
    off_b, off_e = offset
  else:
    off_b = off_e = offset, offset + 1
  for p in pds:
    r_new = Request(orig[:off_b] + pre_func(p) + orig[off_e:], 
            hostname=r.hostname, port=r.port, use_ssl=r.use_ssl)
    r_new.payload = "@" + str(offset) + "=" + p
    rs.append(r_new)
  return rs
  
def i(r, **kwds):
  rqs = RequestSet(_inject_query(r, **kwds))
  if r.method in ("POST", "PUT"):
    rqs += RequestSet(_inject_post(r, **kwds))
  if "Cookie" in zip(*r.headers)[0]:
    rqs += RequestSet(_inject_cookie(r, **kwds))
  if not rqs:
    raise NoInjectionPointFound()
  return rqs 

def i_at(r, offset, payload="default"):
  return RequestSet(_inject_offset(r, offset, default_payload=payload))

def f(r, **kwds):
  return i(r, default_payload="default", **kwds)
  

