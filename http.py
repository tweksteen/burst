#!/usr/bin/python
#
# abrupt.http 
# tw@securusglobal.com
#

import httplib
import urlparse
import cStringIO as StringIO
import gzip
import os
import tempfile
import webbrowser
import subprocess

from color import *
from payload import Injection

class Request():
  
  def __init__(self, requestline, hostname, port, use_ssl):
    self.method, url, self.http_version = requestline.split(" ", 2)
    if self.method == "CONNECT":
      self.init_ssl = True
      self.hostname, self.port = url.split(":", 1)
    else:
      r = urlparse.urlparse(url)
      self.init_ssl = False
      self.use_ssl = use_ssl
      self.url = urlparse.urlunparse(("","") + r[2:])
      self.path = r.path
      self.query = r.query
      self.hostname = r.hostname or hostname
      self.port = int(r.port) if r.port else port
      self.headers = None
      self.content = None
      self.response = None
      self.raw = "%s %s %s" % (self.method, self.url, self.http_version)
    
  def set_headers(self, headers):
    self.headers = {}
    self.raw += headers 
    if "\r" in headers: 
      d = "\r\n" 
    else: 
      d = "\n"
    for l in headers.split(d):
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers[t] = v

  def __repr__(self):
    if self.use_ssl:
      return "<" + " ".join([info(self.method), self.hostname, self.path, warning("SSL")]) + " >"
    else:
      return "<" + " ".join([info(self.method), self.hostname, self.path]) + " >"
  

  def __str__(self):
    return self.raw

  def __call__(self):
    if self.use_ssl:
      conn = httplib.HTTPSConnection(self.hostname + ":" + str(self.port))
    else:
      conn = httplib.HTTPConnection(self.hostname + ":" + str(self.port))
    conn.request(self.method, self.url, self.content, self.headers)
    self.response = Response.create_response(conn.sock)
    conn.close()

  def set_content(self, content):
    self.content = content

  def edit(self):
    fd, fname = tempfile.mkstemp()
    f = os.fdopen(fd, 'w')
    f.write(self.raw)
    f.close()
    ret = subprocess.call("vim " + fname, shell=True)
    f = open(fname, 'r')
    r_new = Request.create_request(f, self.hostname, self.port, self.use_ssl)
    return r_new

  def inject(self, **kwds):
    return Injection(self, **kwds) 

  @staticmethod
  def create_request(sock, hostname=None, port=80, use_ssl=False):
    r = Request(read_banner(sock), hostname, port, use_ssl=use_ssl)
    if r.init_ssl:
      return r
    else:
      r.set_headers(read_headers(sock)) 
      raw_content, content = read_content(sock, r.headers)
      r.raw += raw_content
      r.set_content(content)
      return r  

class Response():
  
  def __init__(self, statusline):
    self.http_version, self.status, self.reason = statusline.split(" ", 2)
    self.raw = statusline
    self.headers = None
    self.content = None

  def __repr__(self):
    flags = []
    if "Transfer-Encoding" in self.headers: flags.append("Chunked")
    if "Content-Encoding" in self.headers: flags.append("Gzip")
    if self.content: flags.append(str(len(self.content)))
    if str(self.status).startswith("2"):
      return "<" + great_success(str(self.status)) + " " + " ".join(flags)  + ">"
    else: 
      return "<" + error(str(self.status)) + " " + " ".join(flags)  + ">"

  def __str__(self):
    return self.raw
  
  def set_headers(self, headers):
    self.headers = {}
    self.raw += headers
    if "\r" in headers:
      d = "\r\n"
    else: 
      d = "\n"
    for l in headers.split(d):
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers[t] = v

  def set_content(self, content):
    self.content = content

  def preview(self):
    fd, fname = tempfile.mkstemp()
    f = os.fdopen(fd, 'w')
    f.write(self.content)
    f.close()
    webbrowser.open_new_tab(fname)
    os.unlink(fname)

  @staticmethod
  def create_response(sock):
    fp = sock.makefile('rb', 0)
    r = Response(read_banner(fp))
    r.set_headers(read_headers(fp))
    raw_content, content = read_content(fp, r.headers, status=r.status)
    r.raw += raw_content
    r.set_content(content)
    # self.charset = r.getheader('content-type').split('charset=')[-1]
    return r  

def read_banner(fp):
  return fp.readline()
 
def read_headers(fp):
  headers = ""
  while True:
    l = fp.readline()
    headers += l
    if l == "\r\n" or l == "\n":
      break
  return headers

def read_content(fp, headers, status=None):
  if "Transfer-Encoding" in headers:
    raw, buffer = _chunked_read_content(fp, headers)
  else:
    length = 0
    if "Content-Length" in headers:
      length = int(headers["Content-Length"])
    buffer = _read_content(fp, length)
    raw = buffer
  content = buffer
  if content:
    if "Content-Encoding" in headers and headers["Content-Encoding"] == "gzip":
      cs = StringIO.StringIO(content)
      gzipper = gzip.GzipFile(fileobj=cs)
      content = gzipper.read()
    return raw, content
  elif status == "200": # No indication on what we should read, so just read
    buffer = fp.read()
    return buffer, buffer
  else:
    return "", ""

def _chunked_read_content(fp, headers):
  buffer = StringIO.StringIO()
  raw = StringIO.StringIO()
  while True:
    l = fp.readline()
    raw.write(l)
    s = int(l,16)
    if s == 0:
      return raw.getvalue(), buffer.getvalue()
    b =  _read_content(fp, s)
    buffer.write(b)
    raw.write(b)
    raw.write(fp.readline()) 

def _read_content(fp, length):
  buffer = StringIO.StringIO()
  while True:
    l = len(buffer.getvalue())
    if l < length:
      buffer.write(fp.read(length-l))
    else:
      break
  return buffer.getvalue()
