import sys
import traceback
import socket
import select
import SocketServer
import ssl
import urlparse
import threading
import time

from abrupt import alert, console
from abrupt.http import Request, RequestSet, connect
from abrupt.exception import BadStatusLine, UnableToConnect, NotConnected, \
                             ProxyError
from abrupt.conf import conf
from abrupt.color import *
from abrupt.cert import generate_ssl_cert, get_key_file, extract_name
from abrupt.utils import re_images_ext, flush_input, decode

ui_lock = threading.Lock()

class ProxyHTTPRequestHandler(SocketServer.StreamRequestHandler):

  protocol_version = "HTTP/1.1"

  def __init__(self, request, client_address, server):
    self.delay = 1
    self.pt = "[" + threading.current_thread().name.replace("Thread-", "") + "]"
    SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)

  def _bypass_ssl(self, hostname, port, proxy_aware=False):
    """
    SSL bypass, behave like the requested server and provide a certificate.
    """
    if proxy_aware:
      self.wfile.write("HTTP/1.1 200 Connection established\r\n\r\n") # yes, sure
    try:
      if conf.ssl_reverse:
        s = connect(hostname=hostname, port=port, use_ssl=True)
        cert = s.getpeercert()
        if cert:
          name = extract_name(cert)
          if name:
            ssl_hostname = name
      elif conf.ssl_hostname:
        hostname = conf.ssl_hostname
        ssl_hostname = hostname
      else:
        ssl_hostname = hostname
      self.ssl_sock = ssl.wrap_socket(self.request, server_side=True,
                                      certfile=generate_ssl_cert(ssl_hostname),
                                      keyfile=get_key_file())
      self.rfile = self.ssl_sock.makefile('rb', self.rbufsize)
      self.wfile = self.ssl_sock.makefile('wb', self.wbufsize)
      return Request(self.rfile, hostname=hostname, port=port, use_ssl=True)
    except ssl.SSLError as e:
      ui_lock.acquire()
      if "alert unknown ca" in str(e) or "alert certificate unknown" in str(e):
        print self.pt, "<" + warning("SSLError") + ": " + \
                       "Abrupt certificate for {} ".format(hostname) + \
                       "has been rejected by your client. >"
      else:
        print warning(str(e))
      ui_lock.release()

  def _init_connection(self):
    """
    Init the connection with the remote server
    """
    return connect(self.r.hostname, self.r.port, self.r.use_ssl)

  def _update_chunk(self, diff):
    if hasattr(self, "chunk_written"):
      self.wfile.write(diff)
      self.chunk_written += diff
    else:
      self.wfile.write(self.r.response.raw())
      self.wfile.write(diff)
      self.chunk_written = diff

  def _do_connection(self):
    """
    Do the request to the remote server. Equivalent to r().
    Just reuse the socket if we can.
    """
    if not hasattr(self, 'prev') or not self.prev or \
           self.prev["hostname"] != self.r.hostname or \
           self.prev["port"] != self.r.port or \
           self.prev["use_ssl"] != self.r.use_ssl:
      self.conn = self._init_connection()
    done = False
    tries = 0
    while not done:
      try:
        if self.server.forward_chunked:
          self.r(conn=self.conn, chunk_callback=self._update_chunk)
        else:
          self.r(conn=self.conn)
        if not self.r.response.closed:
          self.prev = {"hostname": self.r.hostname, "port": self.r.port, "use_ssl": self.r.use_ssl}
        else:
          self.conn.close()
          self.close_connection = 1
        done = True
      except (socket.error, BadStatusLine), e:
        self.conn = self._init_connection()
        if tries == 3:
          ui_lock.acquire()
          print self.pt + " " + repr(UnableToConnect(message=repr(e)))
          ui_lock.release()
          break
        tries += 1
    return done

  def _read_request(self):
    if conf.target:
      t = urlparse.urlparse(conf.target)
      if t.scheme == 'https':
        port = int(t.port) if t.port else 443
        r = self._bypass_ssl(t.hostname, port, proxy_aware=False)
      else:
        port = int(t.port) if t.port else 80
        r = Request(self.rfile, hostname=t.hostname, port=port, use_ssl=False)
    else:
      if not hasattr(self, 'prev') or not self.prev or not self.prev["use_ssl"]:
        r = Request(self.rfile)
        if r.method == "CONNECT":
          r = self._bypass_ssl(r.hostname, r.port, proxy_aware=True)
      else:
        r = Request(self.rfile, hostname=self.prev["hostname"], port=self.prev["port"], use_ssl=self.prev["use_ssl"])
    return r

  def _apply_rules(self):
    for rule, action in self.server.rules:
      if bool(rule(self.r)):
        pre_action = action
        default = False
        break
    else:
      pre_action = self.server.default_action
      default = True
    if self.server.overrided_ask and pre_action == "a":
      pre_action = self.server.overrided_ask
    return pre_action, default

  def poll(self):
    while True:
      if self.server._BaseServer__shutdown_request:
        return False
      r, _, _ = select.select([self.request],[], [], 0.5)
      if self.request in r:
        return True

  def handle(self):
    self.close_connection = 1
    if not self.handle_one_request():
      return
    while not self.close_connection:
      n = self.poll()
      if not n: break
      if not self.handle_one_request(): break

  def handle_one_request(self):
    """
    Accept a request, enable the user to modify, drop or forward it.
    """
    if self.server.persistent:
      self.close_connection = 0
    try:
      self.r = self._read_request()
      if not self.r:
        return False
      self.r = self.server.pre_func(self.r)
      ui_lock.acquire()
      pre_action, default = self._apply_rules()
      if pre_action == "a":
        flush_input()
        alerts =  self.server.alerter.analyse_request(self.r)
        if not alerts:
          if console.term_width:
            e = raw_input(self.pt + " " + self.r.repr(console.term_width - 4 - len(self.pt), rl=True) + " ? ")
          else:
            e = raw_input(self.pt + " " + self.r.repr(rl=True) + " ? ")
        else:
          if console.term_width:
            print self.pt, self.r.repr(console.term_width - len(self.pt))
          else:
            print self.pt, self.r.repr()
          for al in alerts:
            print " " * len(self.pt), " |", al
          e = raw_input(" " * len(self.pt) + " ?")
      else:
        e = pre_action
        if default or self.server.verbose:
          alerts = self.server.alerter.analyse_request(self.r)
          if console.term_width:
            print self.pt, self.r.repr(console.term_width - len(self.pt) - len(e)), e
          else:
            print self.pt, self.r.repr(), e
          for al in alerts:
            print " " * len(self.pt), " |", al
      while True:
        if e == "v":
          print  str(self.r)
        if e == "s":
          print self.r.repr()
        if e == "h":
          print self.r.__str__(headers_only=True)
        if e == "e":
          self.r = self.r.edit()
        if e == "d":
          ui_lock.release()
          return False
        if e == "" or e == "f":
          break
        if e == "c":
          self.server.overrided_ask = "f"
          break
        if e == "de":
          if self.r.content:
            print self.server.decode_func(self.r.content)
          else:
            print "no content to decode"
        if e == "n":
          ui_lock.release()
          time.sleep(1)
          ui_lock.acquire()
          if console.term_width:
            print self.pt, self.r.repr(console.term_width - 5), e
          else:
            print self.pt, self.r.repr(), e
        flush_input()
        e = raw_input("(f)orward, (d)rop, (c)ontinue, (v)iew, (h)eaders, (e)dit, (de)code, (n)ext [f]? ")
      if self.server.verbose >= 2:
        print self.r
      self.server.reqs.append(self.r)
      ui_lock.release()
      if not self._do_connection():
        return False
      ui_lock.acquire()
      if default or self.server.verbose:
        if pre_action == "a" and not self.server.overrided_ask:
          flush_input()
          e = raw_input(self.pt + " " + self.r.response.repr(rl=True) + " ? ")
          while True:
            if e == "v":
              print str(self.r.response)
            if e == "s":
              print self.r.repr()
              print self.r.response.repr()
            if e == "h":
              print self.r.response.__str__(headers_only=True)
            if e == "e":
              self.r.response = self.r.response.edit()
            if e == "d":
              ui_lock.release()
              return False
            if e == "" or e == "f":
              break
            if e == "c":
              self.server.overrided_ask = "f"
              break
            if e == "de":
              if self.r.response.content:
                print self.server.decode_func(self.r.response.content)
              else:
                print "no content to decode"
            if e == "n":
              ui_lock.release()
              time.sleep(1)
              ui_lock.acquire()
              print self.pt, self.r.response.repr()
            flush_input()
            e = raw_input("(f)orward, (d)rop, (c)ontinue, (v)iew, (h)eaders, (e)dit, (de)code, (n)ext [f]? ")
        else:
          print self.pt, repr(self.r.response)
        for al in self.server.alerter.analyse_response(self.r):
          print " " * len(self.pt), " |", al
      if self.server.verbose >= 3:
        print self.r.response
      ui_lock.release()
      if not hasattr(self, "chunk_written"):
        self.wfile.write(self.r.response.raw())
      return True
    except ssl.SSLError as e:
      self.close_connection = 1
      ui_lock.acquire()
      if "certificate verify failed" in str(e):
        print self.pt, "<" + warning("SSLError") + ": Unable to verify the CA " + \
              "chain. Is conf.ssl_verify set properly? >"
      else:
        print self.pt, "<" + warning("SSLError") + ": " + str(e) + ">"
      ui_lock.release()
    except NotConnected as e:
      self.close_connection = 1
    except (UnableToConnect, socket.timeout, ProxyError) as e:
      self.close_connection = 1
      ui_lock.acquire()
      print self.pt, repr(e)
      ui_lock.release()
    return False

class ProxyHTTPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

  deamon_threads = True
  allow_reuse_address = 1

  def handle_error(self, request, client_address):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type == KeyboardInterrupt:
      raise KeyboardInterrupt()
    else:
      print warning(str(exc_type) + ":" + str(exc_value))
      traceback.print_tb(exc_traceback)

def proxy(port=None, rules=((lambda x: re_images_ext.search(x.path), "f"),),
          default_action="a", alerter=None, persistent=True, pre_func=None,
          decode_func=None, forward_chunked=False, verbose=False):
  """Intercept all HTTP(S) requests on port. Return a RequestSet of all the
  answered requests.

  port            -- port to listen to
  alerter         -- alerter triggered on each response, by default GenericAlerter
  rules           -- set of rules for automated actions over requests
  default_action  -- action to execute when no rules matches, by default (a)sk
  pre_func        -- callback used before processing a request
  decode_func     -- callback used when (de)coding a request/response content, by
                     default, decode().
  forward_chunked -- forward chunked response without waiting for the end of it
  persistent      -- keep the connection persistent with your client
  verbose         -- degree of verbosity:
                     False  -- Only display requests undergoing default_action
                     1/True -- Display all requests, including automated ones
                     2      -- Display all requests with their full content
                     3      -- Display all requests and responses with their
                              full content
  See also: conf, watch()
  """
  if not port: port = conf.port
  if not alerter: alerter = alert.GenericAlerter()
  if not rules: rules = []
  if not decode_func: decode_func = decode
  if not pre_func: pre_func = lambda x:x
  print "Running on", conf.ip + ":" + str(port)
  print "Ctrl-C to interrupt the proxy..."
  httpd = ProxyHTTPServer((conf.ip, port), ProxyHTTPRequestHandler)
  httpd.rules = rules
  httpd.default_action = default_action
  httpd.overrided_ask = None
  httpd.pre_func = pre_func
  httpd.decode_func = decode_func
  httpd.alerter = alerter
  httpd.reqs = []
  httpd.forward_chunked = forward_chunked
  httpd.verbose = verbose
  httpd.persistent = persistent
  while True:
    try:
      httpd.serve_forever()
    except select.error:
      # select syscall got interrupted by window resizing
      pass
    except KeyboardInterrupt:
      print "Waiting for the threads to stop"
      httpd.shutdown()
      for t in threading.enumerate():
        if t != threading.current_thread():
          t.join()
      break
  return RequestSet(httpd.reqs)

p = proxy

def watch(**kwds):
  """Run a proxy without user interaction, all the requests are forwarded.
     See also proxy()"""
  return proxy(default_action="f", **kwds)

w = watch
