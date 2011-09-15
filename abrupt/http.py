import os
import copy
import zlib
import gzip
import ssl
import socket
import urlparse
import tempfile
import webbrowser
import subprocess
import datetime
import Cookie
from collections import defaultdict 
from StringIO import StringIO

from abrupt.conf import conf
from abrupt.color import *
from abrupt.utils import *

class UnableToConnect(Exception): pass
class NotConnected(Exception): pass
class BadStatusLine(Exception): pass
class ProxyError(Exception): pass

class Request():

  def __init__(self, fd, hostname=None, port=80, use_ssl=False):
    """Create a request. fd should be either a socket descriptor
       or a string. In both case, it should contain a full request.
       To generate a request from a URL, see c()"""
    if isinstance(fd, basestring): fd = StringIO(fd)
    try:
      self.method, url, self.http_version = read_banner(fd) 
    except ValueError:
      raise NotConnected()
    if self.method == "CONNECT":
      self.hostname, self.port = url.split(":", 1)
    else:
      p_url = urlparse.urlparse(url)
      self.url = urlparse.urlunparse(("","") + p_url[2:])
      self.hostname = p_url.hostname or hostname
      if not self.hostname: raise Exception("No hostname")
      if p_url.scheme == 'https':
        self.use_ssl = True
        self.port = int(p_url.port) if p_url.port else 443
      else:
        self.port = int(p_url.port) if p_url.port else port
        self.use_ssl = use_ssl
      self.set_headers(read_headers(fd))
      self.content = read_content(fd, self.headers, method=self.method)
      self.response = None
      
  @property
  def path(self):
    return urlparse.urlparse(self.url).path

  @property
  def query(self):
    return urlparse.urlparse(self.url).query

  @property
  def cookies(self):
    b = Cookie.SimpleCookie()
    for h, v in self.headers:
      if h == "Cookie":
        b.load(v)
    return b
  
  def set_headers(self, headers):
    self.headers = []
    for l in headers.splitlines():
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers.append((t.title(), v))

  def _update_content_length(self):
    l = str(len(self.content)) if self.content else "0"
    for i, c in enumerate(self.headers):
      h, v = c  
      if h.title() == "Content-Length":
        self.headers[i] = (h, l) 
        break
    else:
      self.headers.append(("Content-Length", l))

  def __repr__(self):
    fields =[info(self.method), self.hostname, self.path]
    if self.use_ssl: fields.append(warning("SSL"))
    return "<" + " ".join(fields) + ">"
  
  def copy(self):
    r_new = copy.copy(self)
    r_new.headers = copy.deepcopy(self.headers)
    r_new.response = None
    return r_new

  def __str__(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.method, self.url, self.http_version))
    for h, v in self.headers:
      s.write("%s: %s\r\n" % (h, v))
    s.write("\r\n")
    if self.content:
      s.write(self.content)
    return s.getvalue()

  def __eq__(self, r):
    if self.hostname != r.hostname or \
       self.port != r.port or \
       self.use_ssl != r.use_ssl or \
       self.url != r.url or \
       self.headers != r.headers:
      return False
    if (self.content or r.content) and self.content != r.content:
      return False 
    return True
      
  def __call__(self, conn=None, post_call=None):
    if conn:
      sock = conn
    else:
      sock = connect(self.hostname, self.port, self.use_ssl)
    if conf.history:
      history.append(self)
    res_sock = _send_request(sock, self)
    n1 = datetime.datetime.now() 
    self.response = Response(res_sock.makefile('rb',0), self)
    n2 = datetime.datetime.now()
    self.response.time = n2 - n1
    if post_call: post_call(self)

  def edit(self):
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    ret = subprocess.call(conf.editor + " " + fname, shell=True)
    if not ret:
      f = open(fname, 'r')
      r_new = Request(f, self.hostname, self.port, self.use_ssl)
      if r_new.method in ('POST', 'PUT'):
        r_new._update_content_length()
      os.remove(fname)
      return r_new

  def play(self, options='-o2 -c "set autoread" -c "autocmd CursorMoved * checktime" -c "autocmd CursorHold * checktime"'):
    fdreq, freqname = tempfile.mkstemp(suffix=".http")
    fdrep, frepname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fdreq, 'w') as f:
      f.write(str(self))
    if self.response:
      with os.fdopen(fdrep, 'w') as f:
        f.write(str(self.response))
    ret = subprocess.Popen(conf.editor + " " + freqname + " " + frepname + " " + options, shell=True)
    last_access = os.stat(freqname).st_mtime
    r_new = None
    while ret.poll() != 0:
      if os.stat(freqname).st_mtime != last_access:
        freq = open(freqname, 'r')
        try:  
          r_new = Request(freq, self.hostname, self.port, self.use_ssl)
          if r_new.method in ('POST', 'PUT'):
            r_new._update_content_length()
          freq.close()
          r_new()
          if r_new.response:
            frep = open(frepname, 'w')
            frep.write(str(r_new.response))
        except Exception, e:
          frep = open(frepname, 'w')
          frep.write("Error:\n")
          frep.write(str(e))
        frep.close()
        last_access = os.stat(freqname).st_mtime
    os.remove(freqname)
    os.remove(frepname)
    return r_new

  def extract(self, arg):
    if arg.startswith("response__"):
      if self.response: 
        return self.response.extract(arg.replace("response__", ""))
    if hasattr(self, arg):
      return getattr(self, arg)
    if self.query:
      query = urlparse.parse_qs(self.query, True)
      print query
      if arg in query:
        return query[arg][0]
    if self.content:
      post = urlparse.parse_qs(self.content, True)
      print post
      if arg in post:
        return post[arg][0]
    c = self.cookies
    if c:
      if arg in c:
        return c[arg].value      
  
  def filter(self, **kwds):
    check_response = {}
    for kw in kwds:
      if kw.startswith("response__"):
        check_response[kw.replace("response__", "")] = kwds[kw]
      if hasattr(self, kw):
        if getattr(self, kw) != kwds[kw]:
          return False
    if check_response:
      if not self.response or not self.response.filter(**check_response): 
        return False
    return True

  def i(self, **kwds):
    from abrupt.injection import inject
    return inject(self, **kwds)
  
  def i_at(self, offset, payload, **kwds):
    from abrupt.injection import inject_at
    return inject_at(self, offset, payload, **kwds)

  def follow(self):
    if not self.response or not self.response.status in ('301', '302'):
      return
    else:
      for h, v in self.response.headers:
        if h == "Location":
          url_p = urlparse.urlparse(v)
          if url_p.scheme in ('http', 'https'):
            return c(v)
          elif not url_p.scheme and url_p.path:
            nr = self.copy()
            n_path = urlparse.urljoin(self.url, v)
            nr.url = urlparse.urlunparse(urlparse.urlparse(self.url)[:2] + urlparse.urlparse(n_path)[2:])
            return nr
          else:
            raise Exception("Unknown redirection, please add some code in abrupt/http.py:186")  

def create(url):
  """Create a request on the fly, based on a URL"""
  p_url = urlparse.urlparse(url) 
  host = p_url.hostname
  if not p_url.path:
    url += "/"
  return Request("""GET %s HTTP/1.1
Host: %s
User-Agent: Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 0.9; en-US)
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en;q=0.5,fr;q=0.2
Accept-Encoding: gzip, deflate 
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7

""" % (url,host))

c = create

class Response():
  
  def __init__(self, fd, request):
    try:
      self.http_version, self.status, self.reason = read_banner(fd)
    except ValueError: 
      raise BadStatusLine()
    self.set_headers(read_headers(fd))
    if request.method == "HEAD": 
      self.content = ""
    else:
      self.content = read_content(fd, self.headers, self.status)
      if self.content:
        self.readable_content = _clear_content(self.headers, self.content)
      else:
        self.readable_content = ""

  def __repr__(self):
    flags = []
    if ("Transfer-Encoding", "Chunked") in self.headers: flags.append("Chunked")
    if ("Content-Encoding", "gzip") in self.headers: flags.append("Gzip")
    if ("Content-Encoding", "deflate") in self.headers: flags.append("Zip")
    if self.content: flags.append(str(len(self.content)))
    return "<" + color_status(self.status) + " " + " ".join(flags)  + ">"

  def __str__(self):
    s = StringIO()
    s.write("%s %s %s\r\n" % (self.http_version, self.status, self.reason))
    for h, v in self.headers:
      s.write("%s: %s\r\n" % (h, v))
    s.write("\r\n")
    if self.content:
      s.write(self.readable_content)
    return s.getvalue()

  def view(self):
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    subprocess.call(conf.editor + " " + fname, shell=True)
    os.remove(fname)

  @property
  def cookies(self):
    b = Cookie.SimpleCookie()
    for h, v in self.headers:
      if h == "Set-Cookie":
        b.load(v)
    return b

  @property
  def closed(self):
    if ("Connection", "close") in self.headers or self.http_version == "HTTP/1.0":
      return True
    return False

  @property
  def length(self):
    return len(self.readable_content)

  @property
  def content_type(self):
    for h,v in self.headers:
      if h == "Content-Type":
        return v

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
        self.headers.append((t.title(), v))

  def preview(self):
    fd, fname = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
      f.write(self.readable_content)
    webbrowser.open_new_tab(fname)

  def extract(self, arg):
    if hasattr(self, arg):
      return getattr(self, arg)
    c = self.cookies
    if arg in c:
      return c[arg].value
  
  def filter(self, **kwds):
    for kw in kwds:
      if not hasattr(self, kw): 
        return False
      if getattr(self, kw) != kwds[kw]:
        return False
    return True

def compare(r1, r2):
  fd1, f1name = tempfile.mkstemp(suffix=".http")
  fd2, f2name = tempfile.mkstemp(suffix=".http")
  with os.fdopen(fd1, 'w') as f:
    f.write(str(r1))
  with os.fdopen(fd2, 'w') as f:
    f.write(str(r2))
  subprocess.call(conf.diff_editor + " " + f1name + " " + f2name, shell=True)
  os.remove(fname1)
  os.remove(fname2)

cmp = compare

class RequestSet():
  
  def __init__(self, reqs=None):
    self.reqs = reqs if reqs else []
    self.hostname = None
  
  def __getitem__(self, i):
    return self.reqs[i]

  def __len__(self):
    return len(self.reqs)

  def __add__(self, other):
    return RequestSet(self.reqs + other.reqs)

  def __bool__(self):
    return bool(self.reqs)

  def append(self, r):
    self.reqs.append(r)

  def extend(self, rs):
    self.reqs.extend(rs)

  def pop(self):
    return self.reqs.pop()  

  def filter(self, **kwds):
    return RequestSet([ r for r in self.reqs if r.filter(**kwds)])

  def extract(self, arg):
    return [ r.extract(arg) for r in self.reqs]

  def cmp(self, i1, i2):
    compare(self[i1], self[i2])

  def cmp_response(self, i1, i2):
    compare(self[i1].response, self[i2].response)

  def __repr__(self):
    status = defaultdict(int)
    for r in self.reqs:
      if r.response:
        status[r.response.status] += 1
      else:
        status["unknown"] += 1
    status_flat = [ color_status(x) + ":" + str(nb) for x, nb in status.items()]
    hostnames = set([r.hostname for r in self.reqs])
    return "{" + " ".join(status_flat) + " | " + ", ".join(hostnames) + "}"
     
  def __str__(self):
    columns =  ([
      ("Method", lambda r, i: info(r.method)),
      ("Path", lambda r, i:  r.path[:27] + "..." if len(r.path)>30 else r.path),
      ("Query", lambda r,i: r.query[:27] + "..." if len(r.query)>30 else r.query),
      ("Status", lambda r, i: color_status(r.response.status)
                 if r.response else "-"),
      ("Length", lambda r, i: str(len(r.response.content)) 
                 if (r.response and r.response.content) else "-")
      ])
    if any([hasattr(x, "payload") for x in self.reqs]):
      columns.insert(2, ("Payload", lambda r, i: getattr(r,"payload","-")[:30]))
      columns.append(("Time", lambda r,i: "%.4f" % (r.response.time.seconds+r.response.time.microseconds/1.e6)
                              if r.response else "-"))
    if len(set([r.hostname for r in self.reqs])) > 1:
      columns.insert(1, ("Host", lambda r, i: r.hostname)) 
    if len(self.reqs) > 5:
      columns.insert(0, ("Id", lambda r,i: str(i)))
    return make_table(self.reqs, columns)

  def _init_connection(self):
    return connect(self.hostname, self.port, self.use_ssl)

  def __call__(self, post_call=None, force=False, verbose=False):
    if not self.reqs:
      raise Exception("No request to proceed")
    hostnames = set([r.hostname for r in self.reqs])
    ports = set([r.port for r in self.reqs])
    use_ssls = set([r.use_ssl for r in self.reqs])
    if len(hostnames) > 1 or len(ports) > 1 or len(use_ssls) > 1:
      raise Exception("Only one host per request set to run them")
    self.hostname = hostnames.pop()
    self.port = ports.pop()
    self.use_ssl = use_ssls.pop()
    conn = self._init_connection()
    print "Running %s requests..." % len(self.reqs),
    clear_line()
    for i, r in enumerate(self.reqs):
      if not verbose:
        print "Running %s requests...%d%%" % (len(self.reqs), i*100/len(self.reqs)),
        clear_line()
      next = False
      if r.response and not force:
        next = True
      while not next:
        try:
          if verbose: print repr(r)
          r(conn=conn, post_call=post_call)
          if verbose: print repr(r.response)
          if r.response.closed: 
            conn = self._init_connection()
          next = True
        except (socket.error, BadStatusLine):
          conn = self._init_connection()
          next = False
    print "Running %s requests...done." % len(self.reqs)
    conn.close()

class History(RequestSet):

  def _enabled(self):
    if not conf.history:
      raise Exception("History not enabled. Set conf.history = True")

  def __repr__(self):
    self._enabled()
    return RequestSet.__repr__(self)

  def __str__(self):
    self._enabled()
    return RequestSet.__str__(self)

  def clear(self):
    self.reqs = []

history = History()

# Following, internal function used by Request and Response
# mostly inspired by httplib

def read_banner(fp):
  banner = re_space.split(fp.readline().strip(), maxsplit=2)
  return banner

def read_headers(fp):
  headers = ""
  while True:
    l = fp.readline()
    headers += l
    if l == "\r\n" or l == "\n":
      break
  return headers

def read_content(fp, headers, status=None, method=None):
  if status == "304": 
    return None
  elif ("Transfer-Encoding", "chunked") in headers:
    return _chunked_read_content(fp).getvalue()
  elif "Content-Length" in zip(*headers)[0]:
    length_str = zip(*headers)[1][zip(*headers)[0].index("Content-Length")]
    length = int(length_str)
    return _read_content(fp, length).getvalue()
  elif status == "200" or method == "POST": # No indication on what we should read, so just read
    return fp.read()
  return None

def _chunked_read_content(fp):
  buffer = StringIO()
  while True:
    l = fp.readline()
    buffer.write(l)
    s = int(l,16)
    if s == 0:
      buffer.write(fp.readline())
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
  if ("Content-Encoding", "deflate") in headers:
    unzipped = StringIO(zlib.decompress(readable_content, -zlib.MAX_WBITS))
    return unzipped.read()
  return readable_content

def connect(hostname, port, use_ssl):
  if conf.proxy:
    p_url = urlparse.urlparse(conf.proxy)
    hostname = p_url.hostname
    port = p_url.port
    use_ssl = True if p_url.scheme[-1] == 's' else False
  try:
    sock = socket.create_connection((hostname, port))
  except socket.error:
    if conf.proxy:
      raise ProxyError("Unable to connect to the proxy")
    raise UnableToConnect()
  if use_ssl:
    sock = ssl.wrap_socket(sock, ssl_version=conf._ssl_version)
  return sock

def _send_request(sock, request):
  if conf.proxy: 
    if request.use_ssl:
      f = sock.makefile("rwb", 0)
      f.write("CONNECT %s:%s HTTP/1.1\r\n\r\n" % (request.hostname, request.port))
      try:
        v, s, m = read_banner(f)
      except ValueError:
        raise BadStatusLine()
      if s != "200":
        raise ProxyError("Bad status " + s + " " + m)
      _ = read_headers(f)
      res_sock = ssl.wrap_socket(sock, ssl_version=conf._ssl_version)
      buf = ["%s %s %s" % (request.method, request.url, request.http_version), ]
    else:
      p_url = urlparse.urlparse(request.url)
      url =  urlparse.urlunparse(("http", request.hostname+":"+str(request.port)) + p_url[2:])
      buf = ["%s %s %s" % (request.method, url, request.http_version), ]
      res_sock = sock
  else: 
    buf = ["%s %s %s" % (request.method, request.url, request.http_version), ]
    res_sock = sock
  buf += [ "%s: %s" % (h, v) for h, v in request.headers] + ["", ""]
  data = "\r\n".join(buf) 
  if request.content:
    data += request.content 
  res_sock.sendall(data)
  return res_sock
