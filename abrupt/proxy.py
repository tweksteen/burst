import sys
import traceback
import socket
import select
import BaseHTTPServer
import ssl

from abrupt import alert, console
from abrupt.http import Request, RequestSet, connect, \
                        BadStatusLine, UnableToConnect
from abrupt.conf import conf
from abrupt.color import *
from abrupt.cert import generate_ssl_cert, get_key_file
from abrupt.utils import re_images_ext

class ProxyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

  protocol_version = "HTTP/1.1"

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
    return connect(r.hostname, r.port, r.use_ssl)

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
    done = False
    while not done:
      try:
        r(conn=self.server.conn)
        if not r.response.closed:
          self.server.prev = {"hostname":r.hostname, "port":r.port,
                              "use_ssl":r.use_ssl}
        else:
          self.server.conn.close()
          self.close_connection = 1
        done = True
      except (socket.error, BadStatusLine):
        self.server.conn = self._init_connection(r)

  def handle_one_request(self):
    """
    Accept a request, enable the user to modify, drop or forward it.
    """
    if self.server.persistent:
      self.close_connection = 0
    try:
      r = Request(self.rfile)
      if r.method == "CONNECT":
        r = self._bypass_ssl(r)
      for rule, action in self.server.rules:
        if bool(rule(r)):
          pre_action = action
          default = False
          break
      else:
        pre_action = self.server.default_action
        default = True
      if self.server.overrided_ask and pre_action == "a":
        pre_action = self.server.overrided_ask
      if pre_action == "a":
        if console.term_width:
          print r.repr(console.term_width), "?",
        else:
          print r.repr(), "?",
        e = raw_input()
      else:
        e = pre_action
        if default or self.server.verbose:
          if console.term_width:
            print r.repr(console.term_width), e
          else:
            print r.repr(), e
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
          self.server.overrided_ask = "f"
          break
        e = raw_input("(v)iew, (e)dit, (f)orward, (d)rop, (c)ontinue [f]? ")
      if self.server.verbose >= 2:
        print r
      self.server.reqs.append(r)
      self._do_connection(r)
      if default or self.server.verbose:
        if pre_action == "a" and not self.server.overrided_ask:
          print repr(r.response), "?",
          e = raw_input()
          while True:
            if e == "v":
              print str(r.response)
            if e == "e":
              r.response = r.response.edit()
            if e == "d":
              return
            if e == "" or e == "f":
              break
            e = raw_input("(v)iew, (e)dit, (f)orward, (d)rop [f]? ")
        else:
          print repr(r.response)
        for al in self.server.alerter.parse(r):
          print " |", al
      if self.server.verbose >= 3:
        print r.response
      self.wfile.write(r.response.raw())

    except (ssl.SSLError, socket.timeout, UnableToConnect), e:
      self.close_connection = 1
      print warning(str(e))
      #self.wfile.write("Abrupt: " + str(e))
      return
   
class ProxyHTTPServer(BaseHTTPServer.HTTPServer):
  
  def handle_error(self, request, client_address):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type == KeyboardInterrupt:
      raise KeyboardInterrupt()
    else:
      print warning(str(exc_type) + ":" + str(exc_value))
      traceback.print_tb(exc_traceback)

def proxy(port=None, nb=-1, rules=((lambda x: re_images_ext.search(x.path), "f"),), 
          default_action="a", alerter=None, persistent=False, verbose=False):
  """Intercept all HTTP(S) requests on port. Return a RequestSet of all the
  answered requests.
  
  port           -- port to listen to
  nb             -- number of request to intercept (-1 for infinite)
  alerter        -- alerter triggered on each response, by default alerter.Generic
  rules          -- set of rules for automated actions over requests
  default_action -- action to execute when no rules matches, by default "a"
  persistent     -- keep the connection persistent with your client 
  verbose        -- degree of verbosity:
                    False -- Only display requests undergoing default_action
                    1     -- Display all requests, including automated ones
                    2     -- Display all requests with their full content
                    3     -- Display all requests and responses with their 
                             full content
  See also: w()
  """
  if not port: port = conf.port
  if not alerter: alerter = alert.Generic()
  if not rules: rules = []
  e_nb = 0
  try:
    print "Running on port", port
    print "Ctrl-C to interrupt the proxy..."
    server_address = ('', port)
    httpd = ProxyHTTPServer(server_address, ProxyHTTPRequestHandler)
    httpd.rules = rules
    httpd.default_action = default_action
    httpd.overrided_ask = None
    httpd.alerter = alerter
    httpd.reqs = []
    httpd.verbose = verbose
    httpd.persistent = persistent
    httpd.prev = None
    while e_nb != nb:
      try:
        httpd.handle_request()
      except select.error:
        # select syscall got interrupted by window resizing
        pass
      e_nb += 1
    return httpd.reqs
  except KeyboardInterrupt:
    print "%d request intercepted" % e_nb
    return RequestSet(httpd.reqs)

p = proxy

def w(**kwds): 
  """Run a proxy without user interaction, all the requests are forwarded. 
     See also p()"""
  return proxy(default_action="f", **kwds)

