#!/usr/bin/python

import httplib
import urlparse
import gzip
import os
import tempfile
import webbrowser
import subprocess
import copy
from StringIO import StringIO

from abrupt.color import *

class HTTPConnection(httplib.HTTPConnection):

  def _clear(self):
    self.__state = httplib._CS_IDLE

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
    self.headers = []
    for l in headers.splitlines():
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers.append((t, v))

  def __repr__(self):
    if self.use_ssl:
      return "<" + " ".join([info(self.method), self.hostname, self.path, warning("SSL")]) + ">"
    else:
      return "<" + " ".join([info(self.method), self.hostname, self.path]) + ">"
  
  def copy(self):
    return copy.deepcopy(self)

  def __str__(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.method, self.url, self.http_version))
    for h, v in self.headers:
      s.write("%s: %s\r\n" % (h, v))
    s.write("\r\n")
    if self.content:
      s.write(self.content)
    return s.getvalue()

  def __call__(self, conn=None):
    if not conn:
      if self.use_ssl:
        conn = httplib.HTTPSConnection(self.hostname + ":" + str(self.port))
      else:
        conn = httplib.HTTPConnection(self.hostname + ":" + str(self.port))
    conn.request(self.method, self.url, self.content, dict(self.headers))
    self.response = Response(conn.sock.makefile('rb',0))

  def edit(self):
    fd, fname = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    editor = os.environ['EDITOR']
    ret = subprocess.call(editor + " " + fname, shell=True)
    f = open(fname, 'r')
    r_new = Request(f, self.hostname, self.port, self.use_ssl)
    return r_new

  @staticmethod
  def filter(reqs, **kwds):
    for k in kwds:
      reqs = [r for r in reqs if getattr(r, k) == kwds[k]]
    return reqs

class Response():
  
  def __init__(self, fd):
    self.http_version, self.status, self.reason = read_banner(fd).strip().split(" ", 2)
    self.set_headers(read_headers(fd))
    self.content = read_content(fd, self.headers, self.status)
    self.readable_content = _clear_content(self.headers, self.content)

  def __repr__(self):
    flags = []
    headers_keys = zip(*self.headers)
    if headers_keys:
      if "Transfer-Encoding" in headers_keys[0]: flags.append("Chunked")
      if "Content-Encoding" in headers_keys[0]: flags.append("Gzip")
    if self.content: flags.append(str(len(self.content)))
    if self.status.startswith("2"):
      st = great_success(self.status)
    elif self.status.startswith("3"):
      st = warning(self.status)
    else:
      st = error(self.status)
    return "<" + st + " " + " ".join(flags)  + ">"

  def __str__(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.http_version, self.status, self.reason))
    for h, v in self.headers:
      s.write("%s: %s\r\n" % (h, v))
    s.write("\r\n")
    if self.content:
      s.write(self.readable_content)
    return s.getvalue()

  def raw(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.http_version, self.status, self.reason))
    for h, v in self.headers:
      s.write("%s: %s\r\n" % (h, v))
    s.write("\r\n")
    if self.content:
      s.write(self.content)
    return s.getvalue()
    
  def set_headers(self, headers):
    self.headers = [] 
    for l in headers.splitlines():
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers.append((t, v))

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
  if ("Transfer-Encoding", "chunked") in headers:
    return _chunked_read_content(fp).getvalue()
  elif "Content-Length" in zip(*headers)[0]:
    length_str = zip(*headers)[1][zip(*headers)[0].index("Content-Length")]
    length = int(length_str)
    return _read_content(fp, length).getvalue()
  elif status == "200": # No indication on what we should read, so just read
    return fp.read()
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
  if ("Transfer-Encoding", "chunked") in headers:
    content_io = StringIO(content)
    buffer = StringIO()
    while True:
      s = int(content_io.readline(), 16)
      if s == 0: 
        readable_content = buffer.getvalue()
        break
      buffer.write(_read_content(content_io, s).getvalue())
      content_io.readline()
  else:
    readable_content = content
  if ("Content-Encoding", "gzip") in headers:
    cs = StringIO(readable_content)
    gzipper = gzip.GzipFile(fileobj=cs)
    return gzipper.read()
  return readable_content
