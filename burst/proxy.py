import re
import sys
import traceback
import socket
import select
import SocketServer
import ssl
import urlparse
import threading
import time

from burst import alert, console
from burst.http import Request, RequestSet, connect
from burst.exception import BadStatusLine, UnableToConnect, NotConnected, \
                             ProxyError
from burst.conf import conf
from burst.color import *
from burst.cert import generate_ssl_cert, get_key_file, extract_name
from burst.utils import flush_input, decode

ui_lock = threading.Lock()

re_images_ext = re.compile(r'\.(png|jpg|jpeg|ico|gif)$')
re_js_ext = re.compile(r'\.js$')
re_css_ext = re.compile(r'\.css$')
ru_forward_all = (lambda x: True, "f")
ru_forward_images = (lambda x: hasattr(x, "path") and re_images_ext.search(x.path), "f")
ru_forward_js = (lambda x: re_js_ext.search(x.path), "f")
ru_forward_css = (lambda x: re_css_ext.search(x.path), "f")
ru_bypass_ssl = (lambda x: x.method == "CONNECT", "b")

class ProxyHTTPRequestHandler(SocketServer.StreamRequestHandler):

  protocol_version = "HTTP/1.1"

  def __init__(self, request, client_address, server):
    self.delay = 1
    self.pt = "[" + threading.current_thread().name.replace("Thread-", "") + "]"
    threading.current_thread().name = "proxy_" + self.pt
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
                                      keyfile=get_key_file(), ssl_version=conf._ssl_version)
      self.rfile = self.ssl_sock.makefile('rb', self.rbufsize)
      self.wfile = self.ssl_sock.makefile('wb', self.wbufsize)
      return Request(self.rfile, hostname=hostname, port=port, use_ssl=True)
    except ssl.SSLError as e:
      ui_lock.acquire()
      if "alert unknown ca" in str(e) or "alert certificate unknown" in str(e):
        print self.pt, "<" + warning("SSLError") + ": " + \
                       "Burst certificate for {} ".format(hostname) + \
                       "has been rejected by your client. >"
      elif "EOF occurred in violation of protocol" in str(e):
        print self.pt, "<" + warning("SSLError") + ": " + \
                       "Connection to {} has been dropped by the client. ".format(hostname) + \
                       "Fake certificate may have been refused? >"
      else:
        print warning(str(e))
      ui_lock.release()

  def _forward_ssl(self, hostname, port):
    client = self.request
    server = connect(hostname, port, False)
    self.wfile.write("HTTP/1.1 200 Connection established\r\n\r\n")
    ui_lock.acquire()
    print self.pt, "<" + info("CONNECT"), hostname + ">"
    ui_lock.release()
    if not server:
      raise UnableToConnect()
    try:
      while not self.server._BaseServer__shutdown_request:
        ready, _, excpt = select.select([client, server], [], [], 2)
        if ready:
          for s in ready:
            data = s.recv(4096)
            if len(data) == 0:
              ui_lock.acquire()
              print self.pt, "<" + info("CONNECT"), hostname + "> ended"
              ui_lock.release()
              return
            for d in [client, server]:
              if d != s:
                d.send(data)
    except socket.error:
      ui_lock.acquire()
      print self.pt, "<" + info("CONNECT"), hostname + "> died"
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
          self.r(conn=self.conn, chunk_func=self._update_chunk)
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
      else:
        r = Request(self.rfile, hostname=self.prev["hostname"],
                    port=self.prev["port"], use_ssl=self.prev["use_ssl"])
    return r

  def _str_request(self, extra="", rl=False):
    if console.term_width:
      return self.pt + " " + self.r.repr(console.term_width - len(extra) - len(self.pt), rl=rl) + extra
    else:
      return self.pt + " " + self.r.repr(rl=rl) + extra

  def _apply_rules(self, r):
    for rule, action in self.server.rules:
      if bool(rule(r)):
        pre_action = action
        automated = True
        break
    else:
      pre_action = "a"
      automated = False
      if self.server.auto and pre_action == "a":
        pre_action = ""
    return pre_action, automated

  def _request_prologue(self):
      self.r = self.server.pre_func(self.r)
      ui_lock.acquire() # before apply rules to allow auto forward
      if self.server._BaseServer__shutdown_request:
        return "d", "d", True
      pre_action, automated = self._apply_rules(self.r)
      alerts = self.server.alerter.analyse_request(self.r)
      if pre_action == "a":
        flush_input()
        if not alerts:
          e = raw_input(self._str_request(extra=" ? ", rl=True))
        else:
          print self._str_request()
          for al in alerts:
            print " " * len(self.pt), " |", al
          e = raw_input(" " * len(self.pt) + " ?")
      else:
        e = pre_action
        if not automated or self.server.verbose:
          print self._str_request(extra=" " + e)
          for al in alerts:
            print " " * len(self.pt), " |", al
      if not automated:
        self.server.reqs.append(self.r)
      return pre_action, e, automated

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
      pre_action, e, automated = self._request_prologue()
      while True:
        if self.r.method == "CONNECT" and (self.server.auto or (e == "" or e == "b")):
          ui_lock.release()
          self.r = self._bypass_ssl(self.r.hostname, self.r.port, proxy_aware=True)
          if not self.r:
            return False
          pre_action, e, automated = self._request_prologue()
          continue
        if self.r.method == "CONNECT" and e == "l":
          ui_lock.release()
          self._forward_ssl(self.r.hostname, self.r.port)
          return False
        if e == "v":
          print  str(self.r)
        if e == "s":
          print self.r.repr()
        if e == "h":
          print self.r.__str__(headers_only=True)
        if e == "e":
          self.r.edit()
        if e == "d":
          ui_lock.release()
          return False
        if self.server.auto or e == "" or e == "f":
          break
        if e == "c":
          self.server.auto = True
          if self.r.method == "CONNECT":
            continue
          else:
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
          print self._str_request()
        flush_input()
        if self.r.method == "CONNECT":
          e = raw_input("[b]ypass, (l)ink, (d)rop, (c)ontinue, (v)iew, (h)eaders, (e)dit, (n)ext? ")
        else:
          e = raw_input("[f]orward, (d)rop, (c)ontinue, (v)iew, (h)eaders, (e)dit, (de)code, (n)ext? ")
      if self.server.verbose >= 2:
        print self.r
      ui_lock.release()
      if not self._do_connection():
        return False
      ui_lock.acquire()
      if not automated or self.server.verbose:
        if pre_action == "a" and not self.server.auto:
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
              self.r.response.edit()
            if e == "d":
              ui_lock.release()
              return False
            if e == "" or e == "f":
              break
            if e == "c":
              self.server.auto = True
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
            e = raw_input("[f]orward, (d)rop, (c)ontinue, (v)iew, (h)eaders, (e)dit, (de)code, (n)ext? ")
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
      if exc_type == socket.error and "Broken pipe" in str(exc_value) and not self.verbose:
        pass
      elif exc_type == ssl.SSLError and "bad write retry" in str(exc_value) and not self.verbose:
        pass
      else:
        print warning(str(exc_type) + ": " + str(exc_value))
        traceback.print_tb(exc_traceback)

def proxy(ip=None, port=None, rules=(ru_bypass_ssl, ru_forward_images,),
          alerter=None, persistent=True, pre_func=None, decode_func=None,
          forward_chunked=False, verbose=False):
  """Intercept all HTTP(S) requests on port. Return a RequestSet of all the
  answered requests.

  ip              -- ip to listen to, by default conf.ip
  port            -- port to listen to, by default conf.port
  alerter         -- alerter triggered on each response, by default GenericAlerter
  rules           -- set of rules for automated actions over requests
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
  See also: conf
  """
  if not ip: ip = conf.ip
  if not port: port = conf.port
  if not alerter: alerter = alert.GenericAlerter()
  if not rules: rules = []
  if not decode_func: decode_func = decode
  if not pre_func: pre_func = lambda x:x
  print "Running on", ip + ":" + str(port)
  print "Ctrl-C to interrupt the proxy..."
  httpd = ProxyHTTPServer((ip, port), ProxyHTTPRequestHandler)
  httpd.rules = rules
  httpd.auto = False
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
        if t.name.startswith("proxy"):
          t.join()
      break
  return RequestSet(httpd.reqs)

p = proxy

