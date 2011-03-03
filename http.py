#!/usr/bin/python
#
# abrupt.http 
# tw@securusglobal.com
#

import httplib
import urlparse
import gzip
import os
import tempfile
import webbrowser
import subprocess
from StringIO import StringIO

from color import *
from payload import Injection

class Request():
  
  def __init__(self, fd, hostname=None, port=80, use_ssl=False):
    self.method, url, self.http_version = read_banner(fd).strip().split(" ", 2)
    if self.method == "CONNECT":
      self.hostname, self.port = url.split(":", 1)
    else:
      p_url = urlparse.urlparse(url)
      self.url = urlparse.urlunparse(("","") + p_url[2:])
      self.hostname = p_url.hostname or hostname
      self.port = int(p_url.port) if p_url.port else port
      self.use_ssl = use_ssl
      self.set_headers(read_headers(fd))
      self.content = read_content(fd, self.headers)
      self.response = None
      
  @property
  def path(self):
    return urlparse.urlparse(self.url).path

  @property
  def query(self):
    return urlparse.urlparse(self.url).query
  
  def set_headers(self, headers):
    self.headers = {}
    for l in headers.splitlines():
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers[t] = v

  def __repr__(self):
    if self.use_ssl:
      return "<" + " ".join([info(self.method), self.hostname, self.path, warning("SSL")]) + " >"
    else:
      return "<" + " ".join([info(self.method), self.hostname, self.path]) + " >"
  

  def __str__(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.method, self.url, self.http_version))
    for h in self.headers:
      s.write("%s: %s\r\n" % (h, self.headers[h]))
    s.write("\r\n")
    if self.content:
      s.write(self.content.getvalue())
    return s.getvalue()

  def __call__(self):
    if self.use_ssl:
      conn = httplib.HTTPSConnection(self.hostname + ":" + str(self.port))
    else:
      conn = httplib.HTTPConnection(self.hostname + ":" + str(self.port))
    conn.request(self.method, self.url, self.content, self.headers)
    self.response = Response(conn.sock.makefile('rb',0))
    conn.close()

  def edit(self):
    fd, fname = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    editor = os.environ['EDITOR']
    ret = subprocess.call(editor + " " + fname, shell=True)
    f = open(fname, 'r')
    r_new = Request(f, self.hostname, self.port, self.use_ssl)
    return r_new

  def inject(self, **kwds):
    return Injection(self, **kwds) 

class Response():
  
  def __init__(self, fd):
    self.http_version, self.status, self.reason = read_banner(fd).strip().split(" ", 2)
    self.set_headers(read_headers(fd))
    self.content = read_content(fd, self.headers, self.status)
    #self.clear_content = _clear_content(self.headers, self.content)

  def __repr__(self):
    flags = []
    if "Transfer-Encoding" in self.headers: flags.append("Chunked")
    if "Content-Encoding" in self.headers: flags.append("Gzip")
    if self.content: flags.append(str(len(self.content.getvalue())))
    if str(self.status).startswith("2"):
      return "<" + great_success(str(self.status)) + " " + " ".join(flags)  + ">"
    else: 
      return "<" + error(str(self.status)) + " " + " ".join(flags)  + ">"

  def __str__(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.http_version, self.status, self.reason))
    for h in self.headers:
      s.write("%s: %s\r\n" % (h, self.headers[h]))
    s.write("\r\n")
    if self.content:
      s.write(self.content.getvalue())
    return s.getvalue()
 
  def set_headers(self, headers):
    self.headers = {}
    for l in headers.splitlines():
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers[t] = v

  def preview(self):
    fd, fname = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
      f.write(self.clear_content)
    webbrowser.open_new_tab(fname)
    os.unlink(fname)


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
    return _chunked_read_content(fp)
  elif "Content-Length" in headers:
    length = int(headers["Content-Length"])
    return _read_content(fp, length)
  elif status == "200": # No indication on what we should read, so just read
    return StringIO(fp.read())
  return None

def _chunked_read_content(fp):
  buffer = StringIO()
  while True:
    l = fp.readline()
    buffer.write(l)
    s = int(l,16)
    if s == 0:
      return buffer
    buffer.write(_read_content(fp, s).getvalue())
    buffer.write(fp.readline()) 

def _read_content(fp, length):
  buffer = StringIO()
  while True:
    l = len(buffer.getvalue())
    if l < length:
      buffer.write(fp.read(length-l))
    else:
      break
  return buffer

def _clear_content(headers, content):
  if "Transfer-Encoding" in headers:
    buffer = StringIO()
    while True:
      s = int(content.readline(),16)
      if s == 0:
        break
      buffer.write(_read_content(content, s))
      content.readline()
  else:
    buffer = content
  if "Content-Encoding" in headers and headers["Content-Encoding"] == "gzip":
    cs = StringIO(buffer)
    gzipper = gzip.GzipFile(fileobj=cs)
    buffer = gzipper.read()
  return buffer.getvalue()
