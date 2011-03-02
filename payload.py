#!/usr/bin/python
#
# abrupt.payload
# tw@securusglobal.com
#

import urllib
import urlparse
import cStringIO as StringIO

class Injection():

  def __init__(self, r):
    i_pts = urlparse.parse_qs(r.query, True)
    payloads = Payload()
    for i_pt in i_pts:
      d = i_pts.copy()
      for p in payloads.payloads:
        d[i_pt] = list(p)
        print d
        r_new = Request.create_request(StringIO.StringIO(r.raw), r.hostname, r.port, r.use_ssl)
        print r_new
        r_new.query = urllib.urlencode(d) 
        print r_new

  def run():
    pass
  


class Payload():
  
  def __init__(self):
    self.payloads = ["'", "' -- "]

  def __next__(self):
    return self.quote(self.payloads.next())
  
  def quote(self, s):  
    return urllib.quote_plus(s)
