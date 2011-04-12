import re
import sys
import socket
import BaseHTTPServer
import traceback
import ssl
import functools
import os.path
import subprocess
import shlex
import random

from abrupt.conf import CONF_DIR
from abrupt.http import Request, Response, RequestSet
from abrupt.color import *
from abrupt.utils import re_filter_images

class ProxyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

  def generate_serial(self):
    return hex(random.getrandbits(64))[:-1]

  def generate_ssl_cert(self, domain):
    domain_cert = os.path.join(CONF_DIR, "certs/", domain + ".pem")
    if not os.path.exists(domain_cert):
      gen_req_cmd = "openssl req -new -out %(conf_dir)sreq.pem -key %(conf_dir)skey.pem -subj '/O=Abrupt/CN=%(domain)s'" % {'conf_dir': CONF_DIR, 'domain':domain} 
      p_req = subprocess.Popen(shlex.split(gen_req_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      ss, se = p_req.communicate()
      if p_req.returncode:
        raise Exception("Error while creating the certificate request:" + se)
      sign_req_cmd = "openssl x509 -req -in %(conf_dir)sreq.pem -CA %(conf_dir)sca.pem -CAkey %(conf_dir)skey.pem -out %(domain_cert)s -set_serial %(serial)s" % {'conf_dir':CONF_DIR, 'domain_cert': domain_cert, 'serial':self.generate_serial()}
      p_sign = subprocess.Popen(shlex.split(sign_req_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      ss, se = p_sign.communicate()
      if p_sign.returncode:
        raise Exception("Error while signing the certificate:" + se)
    return domain_cert

  def bypass_ssl(self, r):
    """
    SSL bypass, behave like the requested server and provide a certificate.
    """
    l = self.rfile.readline()  # Purge headers
    while l !="\r\n":
      l = self.rfile.readline()
    self.wfile.write("HTTP/1.1 200 Connection established\r\n\r\n") # yes, sure
    self.ssl_sock = ssl.wrap_socket(self.request, server_side=True,
                                    certfile=self.generate_ssl_cert(r.hostname), keyfile=os.path.join(CONF_DIR, "key.pem"))
    self.rfile = self.ssl_sock.makefile('rb', self.rbufsize)
    self.wfile = self.ssl_sock.makefile('wb', self.wbufsize)
    return Request(self.rfile, hostname=r.hostname, port=r.port, use_ssl=True)
 
  def handle_one_request(self):
    """
    Accept a request, enable the user to modify, drop or forward it.
    """
    try:
      r = Request(self.rfile)
      if r.method == "CONNECT":
        r = self.bypass_ssl(r)
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
        r()
        print repr(r.response)
        self.wfile.write(r.response.raw())
        self.server.reqs.append(r)  
      else: 
        r()
        self.wfile.write(r.response.raw())

    except (ssl.SSLError, socket.timeout), e:
      print warning(str(e))
      self.close_connection = 1
      return
   
class ProxyHTTPServer(BaseHTTPServer.HTTPServer):
  
  def handle_error(self, request, client_address):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type == KeyboardInterrupt:    
      raise KeyboardInterrupt()
    else:
      print warning(str(exc_value))

def intercept(port=8080, prompt=True, nb=-1, filter=re_filter_images, verbose=False):
  """Intercept all HTTP(S) requests on port. Return a RequestSet of all the 
  answered requests.
  
  port   -- port to listen to
  prompt -- if True, action will be asked to the user for each request
  nb     -- number of request to intercept (-1 for infinite)
  filter -- regular expression to filter ignored files. By default, it 
            ignores .png, .jp(e)g, .gif and .ico.
  See also: p(), w(), p1(), w1()
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
    while e_nb != nb:
      httpd.handle_request() 
      e_nb += 1
    return httpd.reqs
  except KeyboardInterrupt:
    print "%d request intercepted" % e_nb
    return RequestSet(httpd.reqs)

def generate_ca_cert():
  gen_key_cmd = "openssl genrsa -out %skey.pem 2048" % CONF_DIR
  gen_ca_cert_cmd = "openssl req -new -x509 -extensions v3_ca -days 3653 " + \
                    "-subj '/O=Abrupt/CN=Abrupt Proxy' " + \
                    "-out %(conf_dir)sca.pem -key %(conf_dir)skey.pem" % {'conf_dir': CONF_DIR}
  p_key = subprocess.Popen(shlex.split(gen_key_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ss, se = p_key.communicate()
  if p_key.returncode:
    raise Exception("Error while creating the key:" + se)
  p_cert = subprocess.Popen(shlex.split(gen_ca_cert_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ss, se = p_cert.communicate()
  if p_cert.returncode:
    raise Exception("Error while creating the certificate:" + se)
  print "CA certificate : " + CONF_DIR + "ca.pem"

def p(**kwds):
  """Run a proxy. 
     See also: intercept(), w(), p1()"""
  return intercept(**kwds)

def w(**kwds): 
  """Run a proxy without user interaction, all the requests are forwarded. 
     See also intercept(), p(), w1()"""
  return p(prompt=False, **kwds)

def p1(**kwds):
  """Intercept one request and prompt for action.
     See also: intercept(), p(), w1()"""
  return p(nb=1, **kwds)[0]

def w1(**kwds):
  """Intercept one request and forward it.
     See also: intercept(), p1(), w()"""
  return w(nb=1, **kwds)[0]
