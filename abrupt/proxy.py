import sys
import socket
import BaseHTTPServer
import ssl
import httplib

from abrupt.conf import CERT_DIR
from abrupt.http import Request, Response, RequestSet, HTTPConnection, HTTPSConnection
from abrupt.color import *
from abrupt.cert import generate_ssl_cert, get_key_file
from abrupt.utils import re_filter_images

class ProxyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

  def _bypass_ssl(self, r):
    """
    SSL bypass, behave like the requested server and provide a certificate.
    """
    l = self.rfile.readline()  # Purge headers
    while l !="\r\n":
      l = self.rfile.readline()
    self.wfile.write("HTTP/1.1 200 Connection established\r\n\r\n") # yes, sure
    self.ssl_sock = ssl.wrap_socket(self.request, server_side=True,
                                    certfile=generate_ssl_cert(r.hostname), 
                                    keyfile=get_key_file())
    self.rfile = self.ssl_sock.makefile('rb', self.rbufsize)
    self.wfile = self.ssl_sock.makefile('wb', self.wbufsize)
    return Request(self.rfile, hostname=r.hostname, port=r.port, use_ssl=True)
 
  def _init_connection(self, r):
    """
    Init the connection with the remote server
    """
    if r.use_ssl:
      conn = HTTPSConnection(r.hostname + ":" + str(r.port))
    else:
      conn = HTTPConnection(r.hostname + ":" + str(r.port))
    return conn

  def _do_connection(self, r):
    """
    Do the request to the remote server. Equivalent to r().
    Just reuse the socket if we can.
    """
    if not self.server.prev or \
       self.server.prev["hostname"] != r.hostname or \
       self.server.prev["port"] != r.port or \
       self.server.prev["use_ssl"] != r.use_ssl:
      self.server.conn = self._init_connection(r)
    else: 
      self.server.conn._clear()
    done = False
    while not done:
      try:
        r(conn=self.server.conn)
        if not r.response.closed:
          self.server.prev = {"hostname":r.hostname, "port":r.port, "use_ssl":r.use_ssl}
        else:
          self.server.conn.close()
        done = True
      except (httplib.HTTPException, socket.error), e:
        self.server.conn = self._init_connection(r)

  def handle_one_request(self):
    """
    Accept a request, enable the user to modify, drop or forward it.
    """
    try:
      r = Request(self.rfile)
      if r.method == "CONNECT":
        r = self._bypass_ssl(r)
      if not self.server.filter or not self.server.filter.search(r.url):
        if self.server.prompt:
          e = raw_input(repr(r) + " ? ")
          while True:
            if e == "v":
              print str(r)
            if e == "e":
              r = r.edit()
            if e == "d":
              return
            if e == "" or e == "f":
              break
            if e == "c":
              self.server.prompt = False
              break
            e = raw_input("(v)iew, (e)dit, (f)orward, (d)rop, (c)ontinue [f]? ") 
        else:
          print repr(r)
        if self.server.verbose:
          print r
        self._do_connection(r)
        print repr(r.response)
        if self.server.verbose:
          print r.response
        self.wfile.write(r.response.raw())
        self.server.reqs.append(r)
      else:
        self._do_connection(r)
        self.wfile.write(r.response.raw())
    
    except (ssl.SSLError, socket.timeout), e:
      print warning(str(e))
      return
   
class ProxyHTTPServer(BaseHTTPServer.HTTPServer):
  
  def handle_error(self, request, client_address):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type == KeyboardInterrupt:    
      raise KeyboardInterrupt()
    else:
      print warning(str(exc_value))

def proxy(port=8080, prompt=True, nb=-1, filter=re_filter_images, verbose=False):
  """Intercept all HTTP(S) requests on port. Return a RequestSet of all the 
  answered requests.
  
  port   -- port to listen to
  prompt -- if True, action will be asked to the user for each request
  nb     -- number of request to intercept (-1 for infinite)
  filter -- regular expression to filter ignored files. By default, it 
            ignores .png, .jp(e)g, .gif and .ico.
  See also: w(), p1(), w1()
  """
  e_nb = 0
  try:
    print "Running on port", port
    print "Ctrl-C to interrupt the proxy..."
    server_address = ('', port)
    httpd = ProxyHTTPServer(server_address, ProxyHTTPRequestHandler)
    httpd.filter = filter
    httpd.reqs = []
    httpd.prompt = prompt
    httpd.verbose = verbose
    httpd.prev = None
    while e_nb != nb:
      httpd.handle_request() 
      e_nb += 1
    return httpd.reqs
  except KeyboardInterrupt:
    print "%d request intercepted" % e_nb
    return RequestSet(httpd.reqs)

p = proxy

def w(**kwds): 
  """Run a proxy without user interaction, all the requests are forwarded. 
     See also p(), w1()"""
  return proxy(prompt=False, **kwds)

def p1(**kwds):
  """Intercept one request and prompt for action.
     See also: p(), w1()"""
  return proxy(nb=1, **kwds)[0]

def w1(**kwds):
  """Intercept one request and forward it.
     See also: p1(), w()"""
  return w(nb=1, **kwds)[0]
