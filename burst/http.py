import os
import time
import copy
import zlib
import gzip
import ssl
import struct
import socket
import urlparse
import operator
import random
import tempfile
import webbrowser
import threading
import shlex
import subprocess
import datetime
import itertools
from collections import defaultdict
from StringIO import StringIO

import burst.injection
from burst import console
from burst.conf import conf
from burst.cookie import Cookie
from burst.color import *
from burst.exception import *
from burst.utils import make_table, clear_line, chunks, encode, \
                         re_space, smart_split, smart_rsplit, \
                         truncate, stats, parse_qs, play_notifier, \
                         play_updater


class Request():
  """The Request class is the base of Burst. To create an instance, you have
  two options: either use a socket or a string representing the whole request
  into the constructor or use the 'create' function.

  The two methods __repr__ and __str__ have been defined to provide
  user-friendly interaction within the interpreter.
  """

  def __init__(self, fd, hostname=None, port=None, use_ssl=False):
    """Create a request. fd should be either a socket descriptor
       or a string. In both case, it should contain a full request.
       To generate a request from a URL, see c()"""
    if isinstance(fd, basestring):
      fd = StringIO(fd)
    try:
      banner = read_banner(fd)
      # ASSUMPTION: The request line contains three elements seperated by
      #             a space.
      self.method, url, self.http_version = banner
    except ValueError:
      raise NotConnected(' '.join(banner))
    if self.method.upper() == "CONNECT":
      # ASSUMPTION: CONNECT method needs a hostname and port
      self.hostname, self.port = url.rsplit(":", 1)
      self.port = int(self.port)
      self.url = ""
      self.use_ssl = False
    elif hostname:
      self.hostname = hostname
      self.port = port if port else 80
      self.use_ssl = use_ssl
      self.url = url
    else:
      p_url = urlparse.urlparse(url)
      self.url = urlparse.urlunparse(("", "") + p_url[2:])
      if p_url.scheme:
        self.hostname = p_url.hostname
        if not self.hostname:
          raise BurstException("No hostname: " + str(url))
        if p_url.scheme == 'https':
          self.use_ssl = True
          self.port = int(p_url.port) if p_url.port else 443
        else:
          self.port = int(p_url.port) if p_url.port else 80
          self.use_ssl = use_ssl
    self.raw_headers = read_headers(fd)
    if not hasattr(self, "hostname"): # Last chance, try the Host header
      hosts = self.get_header('Host')
      if not hosts:
        raise BurstException("Unable to find the host for the request")
      else:
        host = hosts[0]
      self.hostname = host.split(":")[0]
      self.port = int(host.split(":")[1]) if ":" in host else 80
      self.use_ssl = False
    self.raw_content = read_content(fd, parse_headers(self.raw_headers), method=self.method)
    if self.raw_content:
      self.content = _clear_content(parse_headers(self.raw_headers), self.raw_content)
    else:
      self.content = ""
    self.response = None

  @property
  def path(self):
    return urlparse.urlparse(self.url).path

  @property
  def query(self):
    return urlparse.urlparse(self.url).query

  @property
  def cookies(self):
    cookies = []
    for h in self.get_header("Cookie"):
      cookies.extend(Cookie.parse(h))
    return cookies

  @property
  def headers(self):
    return parse_headers(self.raw_headers)

  def has_header(self, name, value=None):
    """Test if the request contains a specific header (case insensitive).
    If value is supplied, it is matched (case insensitive) against the first
    header with the matching name.
    """
    return _has_header(parse_headers(self.raw_headers), name, value)

  def get_header(self, name):
    """Return the headers of the request matching name (case insensitive).
    This method always returns a list.
    """
    return _get_header(parse_headers(self.raw_headers), name)

  def update_content_length(self):
    """Update the Content-Length header according to the content of the
    request"""
    l = str(len(self.raw_content)) if self.raw_content else "0"
    self.remove_header('Content-Length')
    self.add_header('Content-Length', l)

  def add_header(self, name, value):
    new_headers = parse_headers(self.raw_headers)
    new_headers.append((name, value))
    self.raw_headers = build_headers(new_headers)

  def remove_header(self, name):
    """Remove all the headers matching the specified name"""
    new_headers = [ (h, v) for (h, v) in parse_headers(self.raw_headers) if not h.title() == name ]
    self.raw_headers = build_headers(new_headers)

  def bind(self, r):
    """Bind the Request to another one. This method will copy the supplied
    request's cookies and response set-cookies to the Request."""
    r_new = self.copy()
    for c in r.get_header('Cookie'):
      r_new.add_header('Cookie', c)
    if r.response:
      cookies = []
      for c in r.response.get_header('Set-Cookie'):
        cookies.append(Cookie.parse(c, set_cookie=True))
      r_new.add_header('Cookie', "; ".join([str(x) for x in cookies]))
    return r_new

  def __repr__(self):
    return self.repr(width=None)

  def repr(self, width=None, rl=False):
    if width:
      hostname = smart_rsplit(self.hostname, int(0.3 * width), ".")
      path = smart_split(self.path, int(0.6 * width), "/")
    else:
      hostname = self.hostname
      path = self.path
    fields = [info(self.method, rl=rl), hostname, path]
    if self.use_ssl and self.port != 443:
      fields.insert(2, str(self.port))
    elif not self.use_ssl and self.port != 80:
      fields.insert(2, str(self.port))
    if self.use_ssl: fields.append(warning("SSL", rl=rl))
    return ("<" + " ".join(fields) + ">").encode("utf-8")

  def copy(self):
    """Copy a request. The response is not duplicated."""
    r_new = copy.copy(self)
    r_new.response = None
    return r_new

  def __str__(self, headers_only=False):
    s = StringIO()
    if self.method == "CONNECT":
      s.write("{s.method} {s.hostname}:{s.port} {s.http_version}\r\n".format(s=self))
    else:
      s.write("{s.method} {s.url} {s.http_version}\r\n".format(s=self))
    s.write(build_headers(parse_headers(self.raw_headers)))
    s.write("\r\n")
    if not headers_only and self.content:
      s.write(self.content)
    return s.getvalue()

  def __mul__(self, op):
    """Duplicate a request"""
    return RequestSet([self.copy() for i in range(op)])

  __rmul__ = __mul__

  def __eq__(self, r):
    """Compare two requests based on the host, port, use of ssl, url, headers
    and content (if present)"""
    if self.hostname != r.hostname or \
       self.port != r.port or \
       self.use_ssl != r.use_ssl or \
       self.url != r.url or \
       self.headers != r.headers:
      return False
    if (self.content or r.content) and self.content != r.content:
      return False
    return True

  def similar(self, r):
    """Compare two requests based on the host, port, use of ssl and path"""
    if self.hostname != r.hostname or \
       self.port != r.port or \
       self.use_ssl != r.use_ssl or \
       self.path != r.path:
      return False
    return True

  def expand_curl_ranges(self):
    return burst.injection.expand_curl_ranges(self)

  def inject(self, **kwds):
    return burst.injection.inject(self, **kwds)

  def _init_connection(self):
      return connect(self.hostname, self.port, self.use_ssl)

  def __call__(self, conn=None, chunk_func=None, complete=True):
    """Make the request to the server. If conn is supplied, it will be used
    as connection socket.

    If chunk_func is supplied, it will be call for every chunk received, if
    applicable.

    If complete is False, the response is not read. The method
    _read_response must be called manually later on.
    """
    sock = conn if conn else self._init_connection()
    if conf.history:
      history_lock.acquire()
      history.append(self)
      history_lock.release()
    _send_request(sock, self)
    self.sent_date = datetime.datetime.now()
    if complete:
      self._read_response(sock, chunk_func)

  def _read_response(self, sock, chunk_func):
    self.response = Response(sock.makefile('rb', 0), self, chunk_func=chunk_func)
    self.response.received_date = datetime.datetime.now()

  def edit(self):
    """Edit the request. The original request is modified.
    """
    if conf.update_content_length:
      self.remove_header("Content-Length")
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    ret = subprocess.call(shlex.split(conf.editor.format(fname)))
    if not ret:
      f = open(fname, 'r')
      self.__init__(f, self.hostname, self.port, self.use_ssl)
      if self.method in ('POST', 'PUT') and conf.update_content_length:
        self.update_content_length()
      os.remove(fname)

  def play(self, call_func=None, pre_func=None, post_func=None):
    """Start your editor with a dump of the Request and its Response.
    Every time the request file is saved, the request is made to the server and
    the response updated. When the editor terminates, the last valid request
    made is returned. The original request is not modified.

    If call_func is provided, it will be called every time the request is saved.
    The corresponding Request object is passed as an argument to this callback.

    If pre_func is provided, it will be called before the request is sent.
    A Request is passed as argument, it should return a Request.

    If post_func is provided, it will be called once the response has been read.
    A Response is passed as argument, it should return a Response.

    The behaviour of your editor can be modified via the conf.play_start
    parameters.
    """
    r_tmp = self.copy()
    if conf.update_content_length:
      r_tmp.remove_header("Content-Length")
    fdreq, freqname = tempfile.mkstemp(suffix=".http")
    fdrep, frepname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fdreq, 'w') as f:
      f.write(str(r_tmp))
    if self.response:
      with os.fdopen(fdrep, 'w') as f:
        f.write(str(self.response))
    last_access = os.stat(freqname).st_mtime
    ret = subprocess.Popen(shlex.split(conf.play_start.format(freqname,frepname)))
    r_new = None
    while ret.poll() != 0:
      if os.stat(freqname).st_mtime != last_access:
        play_notifier("Reading request...")
        freq = open(freqname, 'r')
        try:
          r_new = Request(freq, self.hostname, self.port, self.use_ssl)
          if r_new.method in ('POST', 'PUT') and conf.update_content_length:
            play_notifier("Updating Content Length...")
            r_new.update_content_length()
          freq.close()
          if pre_func:
            play_notifier("Calling pre_func...")
            r_new = pre_func(r_new)
          if call_func:
            play_notifier("Calling call_func...")
            call_func(r_new)
          else:
            play_notifier("Connecting...")
            c = r_new._init_connection()
            play_notifier("Sending request...")
            r_new(conn=c, complete=False)
            play_notifier("Reading response...")
            r_new._read_response(c, None)
          if post_func:
            play_notifier("Calling post_func...")
            res_text = post_func(r_new.response)
          else:
            res_text = r_new.response
          if res_text:
            frep = open(frepname, 'w')
            frep.write(str(res_text))
            frep.close()
          play_notifier("Time: " + str(r_new.response.time.total_seconds()))
          play_updater()
        except Exception, e:
          play_notifier("Exception: " + str(e))
        last_access = os.stat(freqname).st_mtime
      # hack to avoid 100% CPU usage. Should be replaced by pyinotify.
      time.sleep(0.1)
    os.remove(freqname)
    os.remove(frepname)
    return r_new

  def extract(self, arg, from_response=None):
    """Extract a particular field of the request.
    The field is looked up in:
      * attributes
      * headers
      * URL query
      * request body
      * cookies
      * response
    """
    if from_response:
      if self.response:
        return self.response.extract(arg)
      return None
    if hasattr(self, arg):
      return getattr(self, arg)
    h = self.get_header(arg)
    if h:
      return h[0]
    if self.query:
      query = parse_qs(self.query)
      if arg in query:
        return query[arg][0]
    if self.content:
      post = parse_qs(self.content)
      if arg in post:
        return post[arg][0]
    try:
      for c in self.cookies:
        if c.name == arg:
          return c.value
    except CookieException:
      pass
    if from_response is None and self.response:
      return self.response.extract(arg)

  def filter(self, predicate):
    """Filter the Request according to a predicate. This method is used by
    RequestSet.filter"""
    return bool(predicate(self))

  def follow(self):
    """Generate a new request based on the Location header."""
    if not self.response or not self.response.status in ('301', '302'):
      return
    else:
      to = self.response.get_header('Location')
      if to:
        url_p = urlparse.urlparse(to[0])
        if url_p.scheme in ('http', 'https'):
          return create(to[0])
        elif not url_p.scheme and url_p.path:
          nr = self.copy()
          n_path = urlparse.urljoin(self.url, to[0])
          nr.url = urlparse.urlunparse(urlparse.urlparse(self.url)[:2] +
                                       urlparse.urlparse(n_path)[2:])
          return nr
        else:
          raise BurstException("Unknown redirection, please add some code " \
                                  "in burst/http.py:Request.follow")

def create(url):
  """Create a request on the fly, based on a URL.
  The URL must contain the scheme."""
  p_url = urlparse.urlparse(url)
  if not p_url.scheme:
    raise BurstException("The scheme is required (http:// or https://)")
  host = p_url.hostname
  if not p_url.path:
    url += "/"
  return Request("""GET {} HTTP/1.1\r
Host: {}\r
User-Agent: Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 0.9; en-US)\r
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r
Accept-Language: en;q=0.5\r
Accept-Encoding: gzip, deflate\r
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\r
\r
""".format(url, host))

c = create

class Response():
  """A response object, always associated with a request.
  """
  def __init__(self, fd, request, chunk_func=None):
    if isinstance(fd, basestring):
      fd = StringIO(fd)
    try:
      banner = read_banner(fd)
      # ASSUMPTION: A response status line contains at least two elements
      #             seperated by a space
      self.http_version, self.status = banner[:2]
      self.reason = banner[2] if len(banner) == 3 else ""
    except ValueError:
      raise BadStatusLine(banner)
    self.raw_headers = read_headers(fd)
    self.request = request
    if request.method == "HEAD":
      self.raw_content = self.content = ""
    else:
      self.raw_content = read_content(fd, parse_headers(self.raw_headers), self.status,
                                      chunk_func=chunk_func)
      if self.raw_content:
        self.content = _clear_content(parse_headers(self.raw_headers), self.raw_content)
      else:
        self.content = ""

  def __repr__(self):
    return self.repr()

  @property
  def time(self):
    return self.received_date - self.request.sent_date

  @property
  def headers(self):
    return parse_headers(self.raw_headers)

  def repr(self, rl=False):
    flags = []
    if self.content: flags.append(str(len(self.content)))
    if self.has_header("Content-Type"):
      flags.append(",".join([x.split(";")[0] for x in
                                             self.get_header("Content-Type")]))
    if self.has_header("Location"):
      flags.append(",".join(self.get_header("Location")))
    if self.has_header("Transfer-Encoding", "chunked"): flags.append("chunked")
    if self.has_header("Content-Encoding", "gzip"): flags.append("gzip")
    if self.has_header("Content-Encoding", "deflate"): flags.append("deflate")
    for c in self.get_header("Set-Cookie"):
      flags.append("C:" + c)
    return "<" + color_status(self.status, rl) + " " + " ".join(flags) + ">"

  def has_header(self, name, value=None):
    """Test if the response contains a specific header (case insensitive).
    If value is supplied, it is matched (case insensitive) against the first
    header with the matching name.
    """
    return _has_header(parse_headers(self.raw_headers), name, value)

  def get_header(self, name):
    """Return the headers of the response matching name (case insensitive).
    This method always returns a list.
    """
    return _get_header(parse_headers(self.raw_headers), name)

  def edit(self):
    """Edit the response through your editor. The original response is modified.
    """
    fd, fname = tempfile.mkstemp(suffix=".http")
    if self.content != self.raw_content:
      print warning("The response is currently encoded. It will be decoded " \
                    "before edition."),
      raw_input()
      self.normalise()
    if conf.update_content_length:
      self.remove_header("Content-Length")
    with os.fdopen(fd, 'w') as f:
      f.write(self.raw())
    ret = subprocess.call(shlex.split(conf.editor.format(fname)))
    if not ret:
      f = open(fname, 'r')
      self.__init__(f, self.request)
      if self.content:
        self.update_content_length()
      os.remove(fname)

  def copy(self):
    """Copy a Response. Both response will have the same request."""
    res_new = copy.copy(self)
    return res_new

  def normalise(self):
    """Normalise the response content by dropping any extra encoding"""
    self.raw_content = self.content
    self.remove_header("Transfer-Encoding")
    self.remove_header("Content-Encoding")
    self.update_content_length()

  def add_header(self, name, value):
    new_headers = parse_headers(self.raw_headers)
    new_headers.append((name, value))
    self.raw_headers = build_headers(new_headers)

  def remove_header(self, name):
    """Remove all the headers matching the specified name"""
    new_headers = [ (h, v) for (h, v) in parse_headers(self.raw_headers) if not h.title() == name ]
    self.raw_headers = build_headers(new_headers)

  def update_content_length(self):
    """Update the Content-Length header according to the content of the
    response"""
    l = str(len(self.raw_content)) if self.raw_content else "0"
    self.remove_header('Content-Length')
    self.add_header('Content-Length', l)

  @property
  def cookies(self):
    cookies = []
    for h in self.get_header("Set-Cookie"):
      cookies.append(Cookie.parse(h, set_cookie=True))
    return cookies

  @property
  def is_javascript(self):
    if any(["javascript" in h for h in self.get_header("Content-Type")]):
      return True
    return False

  @property
  def is_html(self):
    if any(["html" in h for h in self.get_header("Content-Type")]):
      return True
    return False

  @property
  def closed(self):
    if self.has_header("Connection", "close") or self.http_version == "HTTP/1.0":
      return True
    return False

  @property
  def length(self):
    return len(self.content)

  @property
  def content_type(self):
    try:
      return self.get_header("Content-Type")[0]
    except IndexError:
      return None

  def __str__(self, headers_only=False):
    s = StringIO()
    s.write("{s.http_version} {s.status} {s.reason}\r\n".format(s=self))
    s.write(build_headers(parse_headers(self.raw_headers)))
    s.write("\r\n")
    if not headers_only and self.content:
      s.write(self.content)
    return s.getvalue()

  def raw(self):
    s = StringIO()
    s.write("{s.http_version} {s.status} {s.reason}\r\n".format(s=self))
    s.write(self.raw_headers)
    s.write("\r\n")
    if hasattr(self, "raw_content") and self.raw_content:
      s.write(self.raw_content)
    return s.getvalue()

  def preview(self):
    """Preview the reponse in your browser.
    """
    fd, fname = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
      f.write(self.content)
    webbrowser.open_new_tab(fname)

  def extract(self, arg):
    """Extract a particular field of the response.
    The field is looked up in:
      * attributes
      * headers
      * cookies
    """
    if hasattr(self, arg):
      return getattr(self, arg)
    h = self.get_header(arg)
    if h:
      return h[0]
    for c in self.cookies:
      if c.name == arg:
        return c.value

  def filter(self, predicate):
    return bool(predicate(self))

def compare(r1, r2):
  fd1, f1name = tempfile.mkstemp(suffix=".http")
  fd2, f2name = tempfile.mkstemp(suffix=".http")
  with os.fdopen(fd1, 'w') as f:
    f.write(str(r1))
  with os.fdopen(fd2, 'w') as f:
    f.write(str(r2))
  subprocess.call(conf.diff_editor.format(f1name, f2name), shell=True)
  os.remove(f1name)
  os.remove(f2name)

cmp = compare

class RequestSet():
  """Set of request. This object behaves like a list.
  """

  def __init__(self, reqs=None):
    self.reqs = reqs if reqs else []
    self.hostname = None

  def __getitem__(self, i):
    if isinstance(i, slice):
      return RequestSet(self.reqs[i])
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

  def filter(self, predicate):
    return RequestSet([r for r in self.reqs if r.filter(predicate)])

  def extract(self, arg, from_response=None):
    return [r.extract(arg, from_response) for r in self.reqs]

  def copy(self):
    return RequestSet([r.copy() for r in self.reqs])

  def cmp(self, i1, i2):
    compare(self[i1], self[i2])

  def cmp_response(self, i1, i2):
    compare(self[i1].response, self[i2].response)

  def diff(self, other, predicate):
    if len(self) != len(other):
      raise BurstException("A RequestSet of the same size is required")
    return RequestSet([self[i] for i in range(len(self))
            if predicate(self[i], other[i])])

  def expand_curl_ranges(self):
    """Expands curl range sequences in the RequestSet"""
    new_rs = RequestSet()
    for r in self.reqs:
      new_rs.extend(r.expand_curl_ranges())
    self.reqs = new_rs

  def __repr__(self):
    status = defaultdict(int)
    for r in self.reqs:
      if r.response:
        status[r.response.status] += 1
      else:
        status["unknown"] += 1
    status_flat = [color_status(x) + ":" + str(nb) for x, nb in sorted(status.items())]
    hostnames = set([r.hostname for r in self.reqs])
    return "{" + " ".join(status_flat) + " | " + ", ".join(hostnames) + "}"

  def __str__(self):
    return unicode(self).encode('utf-8')

  def __unicode__(self, width=None):

    def n_length(r, i):
      if r.response and r.response.content:
        p = str(len(r.response.content))
        if hasattr(r, "payload"):
          p += "(" + str(len(r.response.content)-len(encode(r.payload))) + ")"
        return p
      else:
        return "-"

    cols = [
            ("Method", lambda r, i: info(r.method), None),
            ("Path", lambda r, i: r.path, (9, smart_rsplit, "/")),
            ("Status", lambda r, i: color_status(r.response.status) if r.response else "-", None),
            ("Length", n_length, None)]

    if any([hasattr(x, "payload") for x in self.reqs]):
      cols.insert(2,
                  ("Point", lambda r, i: getattr(r, "injection_point", "-"),
                  (2, truncate)))
      cols.insert(3,
                  ("Payload", lambda r, i: getattr(r, "payload", "-").encode('string_escape'),
                  (3, truncate)))
      cols.append(("Time", lambda r, i: "{:.4f}".format(r.response.time.total_seconds()) if
                                        (r.response and hasattr(r.response, "time")) else "-", None))
    else:
      cols.insert(2, ("Query", lambda r, i: r.query, (3, smart_rsplit, "&")))
    if len(set([r.hostname for r in self.reqs])) > 1:
      cols.insert(1, ("Host", lambda r, i: r.hostname, (2, smart_rsplit, ".")))
    if len(self.reqs) > 5:
      cols.insert(0, ("Id", lambda r, i: str(i), None))
    return make_table(self.reqs, cols, console.term_width)

  def _summary_attr(self, rs, attr, p_str, indent):
    values = [ attr(r) for r in rs if r.response ]
    if not values:
      return False
    avg, bottom, top = stats(values)
    if indent:
      print " ",
    print p_str.format(bottom, avg, top)
    outsiders = [ r for r in rs if r.response and (attr(r) < bottom or  attr(r) > top)]
    if outsiders:
      if indent:
        bl = "    | "
      else:
        bl = " | "
      print "\n".join([bl + getattr(r, "payload", "-") + " " + error(str(attr(r))) for r in outsiders])
      return True
    return False

  def summary(self):
    sips = set([ x.injection_point for x in self.reqs if hasattr(x, "injection_point")])
    for ip in sips:
      if not ip and len(sips) == 1:
        ors = self
        split = False
      else:
        print "Injection point:", ip
        ors = self.filter(lambda x: hasattr(x, "injection_point") and x.injection_point == ip)
        split = True
      rs = ors
      if rs:
        if self._summary_attr(rs, lambda x: x.response.length, "Length: [{:.1f} {:.1f} {:.1f}]", split):
          print
      rs = ors.filter(lambda x: hasattr(x.response, "time"))
      if rs:
        if self._summary_attr(rs, lambda x: x.response.time.total_seconds(), "Time: [{:.3f} {:.3f} {:.3f}]", split):
          print

  def responded(self):
    return self.filter(lambda x: x.response)

  def by_length(self):
    return RequestSet(sorted(self.responded().reqs, key=operator.attrgetter("response.length")))

  def by_time(self):
    return RequestSet(sorted(self.responded().reqs, key=operator.attrgetter("response.time")))

  def by_status(self):
    return RequestSet(sorted(self.responded().reqs, key=operator.attrgetter("response.status")))

  def by_path(self):
    return RequestSet(sorted(self.reqs, key=operator.attrgetter("path")))

  def without_payloads(self):
    return RequestSet([x for x in self.reqs if not hasattr(x, "payload")])

  def _init_connection(self):
    return connect(self.hostname, self.port, self.use_ssl)

  def clear(self):
    for r in self.reqs:
      r.response = None

  def parallel(self, threads=4, verbose=True, **kw):
    stop = threading.Event()
    indices = range(len(self.reqs))
    jobs = []
    for ics in chunks(indices, threads):
      mkw = kw.copy()
      mkw.update({"indices":ics, "stop_event":stop, "verbose":False})
      t = threading.Thread(target=self.__call__, kwargs=mkw)
      jobs.append(t)
      t.start()
    try:
      for j in jobs:
        while j.is_alive():
          j.join(1)
          if verbose:
            done = len(self.filter(lambda x: x.response))
            print "Running {} requests... {:.2f}%".format(len(self), done * 100. / len(self)),
          clear_line()
    except KeyboardInterrupt:
      stop.set()
    if verbose:
      ## the two extra spaces in the end erase the left over "00%" from "100%"
      print "Running {} requests... done.  ".format(len(self))

  def __call__(self, force=False, randomised=False, verbose=1, retry=0,
               indices=None, stop_event=None, post_func=None, post_args=[]):
    if not self.reqs:
      raise Exception("No request to process")
    hostnames = set([r.hostname for r in self.reqs])
    ports = set([r.port for r in self.reqs])
    use_ssls = set([r.use_ssl for r in self.reqs])
    if len(hostnames) > 1 or len(ports) > 1 or len(use_ssls) > 1:
      raise Exception("Only one host per request set to run it")
    self.hostname = hostnames.pop()
    self.port = ports.pop()
    self.use_ssl = use_ssls.pop()
    if force:
      if verbose:
        print "Clearing previous responses..."
      self.clear()
    conn = self._init_connection()
    if verbose:
      print "Running {} requests...".format(len(self.reqs)),
      clear_line()
    indices = range(len(self.reqs)) if not indices else indices
    if randomised:
      random.shuffle(indices)
    done = 0
    failed = 0
    todo = len(self.reqs)
    for i in indices:
      if stop_event and stop_event.is_set():
        return
      r = self.reqs[i]
      if verbose:
        if failed:
          print "Running {} requests...{:.2f}% (failed: {})".format(todo,
                                                    done * 100. / todo, failed),
        else:
          print "Running {} requests...{:.2f}%".format(todo, done * 100. / todo),
        clear_line()
      next = False
      if r.response and not force:
        todo -= 1
        next = True
      retried = 0
      while not next:
        try:
          if verbose == 2: print repr(r)
          r(conn=conn)
          if post_func: post_func(r, *post_args)
          if verbose == 2: print repr(r.response)
          if r.response.closed:
            conn = self._init_connection()
          done += 1
          next = True
        except (socket.error, BadStatusLine):
          conn = self._init_connection()
          next = False
          retried += 1
          if retried > retry:
            failed += 1
            next = True
        if conf.delay:
          time.sleep(conf.delay)
    if verbose:
      print "Running {} requests...done.".format(len(self.reqs))
    conn.close()

class History(RequestSet):
  """History is a singleton class which contains all the
  requests made through Burst.
  """

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

history_lock = threading.RLock()
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
    if l == "\r\n" or l == "\n":
      break
    headers += l
  return headers

def parse_headers(raw_headers):
  headers = []
  # ASSUMPTION: Headers are seperated by a newline character
  for l in raw_headers.splitlines():
    if l:
      # ASSUMPTION: Each header is composed of two fields seperated by
      #             a colon.
      t, v = [q.strip() for q in l.split(":", 1)]
      headers.append((t, v))
  return headers

def build_headers(headers):
  return "\r\n".join(["{}: {}".format(h, v) for h, v in headers] + ["",])

def _has_header(headers, name, value=None):
  for h, v in headers:
    if h.lower() == name.lower():
      if value is None:
        return True
      elif v.lower() == value.lower():
        return True
      else:
        return False
  return False

def _get_header(headers, name):
  return [v for h, v in headers if h.lower() == name.lower()]

def read_content(fp, headers, status=None, method=None, chunk_func=None):
  if status == "304":
    return None
  elif _has_header(headers, "Transfer-Encoding", "chunked"):
    return _chunked_read_content(fp, chunk_func=chunk_func).getvalue()
  elif _has_header(headers, "Content-Length"):
    # ASSUMPTION: The first Content-Length header will be use to
    #             read the response
    length_str = _get_header(headers, "Content-Length")[0]
    # ASSUMPTION: The value of Content-Length can be converted to an integer
    length = int(length_str)
    if length < 0:
      raise BurstException("Invalid Content-Length")
    return _read_content(fp, length).getvalue()
  elif (status and status != "204") or method == "POST" or method == "PUT":
    # ASSUMPTION: In case we have no indication on what to read, if the method
    #             is POST or the status 200, we read until EOF
    return fp.read()
  return None

def _chunked_read_content(fp, chunk_func=None):
  buffer = StringIO()
  while True:
    diff = ""
    l = fp.readline()
    diff += l
    s = int(l, 16)
    if s == 0:
      diff += fp.readline()
      buffer.write(diff)
      if chunk_func:
        chunk_func(diff)
      return buffer
    diff += _read_content(fp, s).getvalue()
    diff += fp.readline()
    buffer.write(diff)
    if chunk_func:
      chunk_func(diff)

def _read_content(fp, length):
  buffer = StringIO()
  while True:
    l = len(buffer.getvalue())
    if l < length:
      buffer.write(fp.read(length - l))
    else:
      break
  return buffer

def _clear_content(headers, raw_content):
  if _has_header(headers, "Transfer-Encoding", "chunked"):
    content_io = StringIO(raw_content)
    buffer = StringIO()
    while True:
      s = int(content_io.readline(), 16)
      if s == 0:
        content = buffer.getvalue()
        break
      buffer.write(_read_content(content_io, s).getvalue())
      content_io.readline()
  else:
    content = raw_content
  if _has_header(headers, "Content-Encoding", "gzip"):
    cs = StringIO(content)
    gzipper = gzip.GzipFile(fileobj=cs)
    return gzipper.read()
  if _has_header(headers, "Content-Encoding", "deflate"):
    try:
      unzipped = StringIO(zlib.decompress(content))
    except zlib.error:
      unzipped = StringIO(zlib.decompress(content, -zlib.MAX_WBITS))
    return unzipped.read()
  return content

def _wrap_socket(sock):
  if conf.ssl_verify or conf.ssl_reverse:
    return ssl.wrap_socket(sock, ssl_version=conf._ssl_version,
                           cert_reqs=ssl.CERT_REQUIRED,
                           ca_certs=conf.ssl_verify)
  else:
    return ssl.wrap_socket(sock, ssl_version=conf._ssl_version)

def _socks5_connect(hostname, port, use_ssl):
  p_url = urlparse.urlparse(conf.proxy)
  p_hostname = p_url.hostname
  p_port = p_url.port
  sock = socket.create_connection((p_hostname, p_port))
  sock.sendall("\x05\x01\x00")
  auth = sock.recv(2)
  if auth != "\x05\x00":
    raise ProxyError("Authentication required for the proxy")
  p_r = "\x05\x01\x00"
  try:
    p_r += "\x01" + socket.inet_aton(hostname)
  except socket.error:
    p_r += "\x03" + chr(len(hostname)) + hostname
  p_r += struct.pack(">H", port)
  sock.sendall(p_r)
  p_res = sock.recv(4)
  if not p_res.startswith("\x05\x00"):
    raise ProxyError("Socks proxy returned: " + repr(p_res))
  if p_res[3] == "\x01":
    sock.recv(4)
  elif p_res[3] == "\x03":
    p_l = ord(sock.recv(1))
    sock.recv(p_l)
  sock.recv(2)
  if use_ssl:
    try:
      sock = _wrap_socket(sock)
    except socket.error, e:
      print e
      raise UnableToConnect("Unable to use SSL with the proxy")
  return sock

def _socks4_connect(hostname, port, use_ssl):
  p_url = urlparse.urlparse(conf.proxy)
  p_hostname = p_url.hostname
  p_port = p_url.port
  try:
    ipaddr = socket.inet_aton(hostname)
    resolv = False
  except socket.error:
    ipaddr = "\x00\x00\x00\x01"
    resolv = True
  p_r = "\x04\x01" + struct.pack(">H", port) + ipaddr + "\x00"
  if resolv:
    p_r += hostname + "\x00"
  sock = socket.create_connection((p_hostname, p_port))
  sock.sendall(p_r)
  p_res = sock.recv(8)
  if not p_res.startswith("\x00\x5A"):
    raise ProxyError("Socks proxy returned: " + repr(p_res))
  if use_ssl:
    try:
      sock = _wrap_socket(sock)
    except socket.error:
      raise UnableToConnect("Unable to use SSL with the proxy")
  return sock

def _http_connect(hostname, port, use_ssl):
  p_url = urlparse.urlparse(conf.proxy)
  p_hostname = p_url.hostname
  p_port = p_url.port
  p_use_ssl = True if p_url.scheme[-1] == 's' else False
  try:
    sock = socket.create_connection((p_hostname, p_port))
  except socket.error:
    raise ProxyError("Unable to connect to the proxy")
  if p_use_ssl:
    try:
      # No check is made to verify proxy certificate
      sock = ssl.wrap_socket(sock, ssl_version=conf._ssl_version)
    except socket.error:
      raise ProxyError("Unable to use SSL with the proxy")
  if use_ssl:
    f = sock.makefile("rwb", 0)
    f.write("CONNECT {}:{} HTTP/1.1\r\n\r\n".format(hostname, port))
    try:
      v, s, m = read_banner(f)
    except ValueError:
      raise BadStatusLine()
    if s != "200":
      raise ProxyError("Bad status " + s + " " + m)
    _ = read_headers(f)
    sock = _wrap_socket(sock)
  return sock

def _direct_connect(hostname, port, use_ssl):
  try:
    sock = socket.create_connection((hostname, port))
  except socket.error:
    raise UnableToConnect()
  if use_ssl:
    try:
      sock = _wrap_socket(sock)
    except socket.error, e:
      raise UnableToConnect("Unable to use SSL with the server")
  return sock

def connect(hostname, port, use_ssl):
  if conf.proxy:
    p_url = urlparse.urlparse(conf.proxy)
    if p_url.scheme.startswith("http"):
      return _http_connect(hostname, port, use_ssl)
    elif p_url.scheme.startswith("socks4"):
      return _socks4_connect(hostname, port, use_ssl)
    elif p_url.scheme.startswith("socks5"):
      return _socks5_connect(hostname, port, use_ssl)
    else:
      raise NotImplementedError("Available proxy protocols: http(s), socks4a, socks5")
  else:
    return _direct_connect(hostname, port, use_ssl)

def _send_request(sock, request):
  if conf.proxy and not request.use_ssl:
    p_url = urlparse.urlparse(conf.proxy)
    if p_url.scheme == "http":
      p_url = urlparse.urlparse(request.url)
      url = urlparse.urlunparse(("http", request.hostname + ":" + str(request.port)) + p_url[2:])
      buf = " ".join([request.method, url, request.http_version])
    else:
      buf = " ".join([request.method, request.url, request.http_version])
  else:
    buf = " ".join([request.method, request.url, request.http_version])
  data = "\r\n".join([buf, request.raw_headers, ""])
  if request.raw_content:
    data += request.raw_content
  # if request.footers:
  #   data += ["{}: {}".format (h, v) for h, v in request.footers] + ["",""]
  sock.sendall(data)
