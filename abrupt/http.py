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
import subprocess
import datetime
from collections import defaultdict
from StringIO import StringIO

from abrupt import console
from abrupt.conf import conf
from abrupt.cookie import Cookie
from abrupt.color import *
from abrupt.exception import *
from abrupt.utils import make_table, clear_line, \
                         re_space, smart_split, smart_rsplit, \
                         truncate, stats, parse_qs

class Request():
  """The Request class is the base of Abrupt. To create an instance, you have
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
      self.hostname = p_url.hostname
      if not self.hostname:
        raise AbruptException("No hostname: " + str(url))
      if p_url.scheme == 'https':
        self.use_ssl = True
        self.port = int(p_url.port) if p_url.port else 443
      else:
        self.port = int(p_url.port) if p_url.port else 80
        self.use_ssl = use_ssl
    self.set_headers(read_headers(fd))
    self.raw_content = read_content(fd, self.headers, method=self.method)
    if self.raw_content:
      self.content = _clear_content(self.headers, self.raw_content)
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

  def has_header(self, name, value=None):
    """Test if the request contains a specific header (case insensitive).
    If value is supplied, it is matched (case insensitive) against the first
    header with the matching name.
    """
    return _has_header(self.headers, name, value)

  def get_header(self, name):
    """Return the headers of the request matching name (case insensitive).
    This method always returns a list.
    """
    return _get_header(self.headers, name)

  def set_headers(self, headers):
    self.headers = []
    # ASSUMPTION: Headers are seperated by a newline character
    for l in headers.splitlines():
      if l:
        # ASSUMPTION: Each header is composed of two fields seperated by
        #             a colon.
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers.append((t, v))

  def update_content_length(self):
    """Update the Content-Length header according to the content of the
    request"""
    l = str(len(self.raw_content)) if self.raw_content else "0"
    for i, c in enumerate(self.headers):
      h, v = c
      if h.title() == "Content-Length":
        self.headers[i] = (h, l)
        # ASSUMPTION: There is only one Content-Length header per request
        break
    else:
      self.headers.append(("Content-Length", l))

  def remove_header(self, name):
    """Remove all the headers matching the specified name"""
    for i, c in enumerate(self.headers):
      h, v = c
      if h.title() == name:
        del self.headers[i]

  def bind(self, r):
    """Bind the Request to another one. This method will copy the supplied
    request's cookies and response set-cookies to the Request."""
    r_new = self.copy()
    for c in r.get_header('Cookie'):
      r_new.headers.append(('Cookie', c))
    if r.response:
      cookies = []
      for c in r.response.get_header('Set-Cookie'):
        cookies.append(Cookie.parse(c, set_cookie=True))
      r_new.headers.append(('Cookie', "; ".join([str(x) for x in cookies])))
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
    if self.use_ssl: fields.append(warning("SSL", rl=rl))
    return ("<" + " ".join(fields) + ">").encode("utf-8")

  def copy(self):
    """Copy a request. The response is not duplicated."""
    r_new = copy.copy(self)
    r_new.headers = copy.deepcopy(self.headers)
    r_new.response = None
    return r_new

  def __str__(self, headers_only=False):
    s = StringIO()
    if self.method == "CONNECT":
      s.write("{s.method} {s.hostname}:{s.port} {s.http_version}\r\n".format(s=self))
    else:
      s.write("{s.method} {s.url} {s.http_version}\r\n".format(s=self))
    for h, v in self.headers:
      s.write("{}: {}\r\n".format(h, v))
    s.write("\r\n")
    if not headers_only and self.content:
      s.write(self.content)
    return s.getvalue()

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

  def __call__(self, conn=None, chunk_func=None):
    """Make the request to the server. If conn is supplied, it will be used
    as connection socket. If chunk_func is supplied, it will be call for
    every chunk received, if appplicable.
    """
    if conn:
      sock = conn
    else:
      sock = connect(self.hostname, self.port, self.use_ssl)
    if conf.history:
      history_lock.acquire()
      history.append(self)
      history_lock.release()
    _send_request(sock, self)
    t_start = datetime.datetime.now()
    self.response = Response(sock.makefile('rb', 0), self, chunk_func=chunk_func)
    self.response.sent_date = t_start
    self.response.received_date = datetime.datetime.now()

  def edit(self):
    """Edit the request. The original request is modified.
    """
    if conf.update_content_length:
      self.remove_header("Content-Length")
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    ret = subprocess.call(conf.editor.format(fname), shell=True)
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

    The behaviour of your editor can be modified via the conf.editor_play
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
    ret = subprocess.Popen(conf.editor_play.format(freqname,frepname), shell=True)
    r_new = None
    while ret.poll() != 0:
      if os.stat(freqname).st_mtime != last_access:
        freq = open(freqname, 'r')
        try:
          r_new = Request(freq, self.hostname, self.port, self.use_ssl)
          if r_new.method in ('POST', 'PUT') and conf.update_content_length:
            r_new.update_content_length()
          freq.close()
          if pre_func:
            r_new = pre_func(r_new)
          if call_func:
            call_func(r_new)
          else:
            r_new()
          if post_func:
            res_text = post_func(r_new.response)
          else:
            res_text = r_new.response
          if res_text:
            frep = open(frepname, 'w')
            frep.write(str(res_text))
        except Exception, e:
          frep = open(frepname, 'w')
          frep.write("Error:\n")
          frep.write(str(e))
        frep.close()
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
      for h, v in self.response.headers:
        if h == "Location":
          url_p = urlparse.urlparse(v)
          if url_p.scheme in ('http', 'https'):
            return c(v)
          elif not url_p.scheme and url_p.path:
            nr = self.copy()
            n_path = urlparse.urljoin(self.url, v)
            nr.url = urlparse.urlunparse(urlparse.urlparse(self.url)[:2] +
                                         urlparse.urlparse(n_path)[2:])
            return nr
          else:
            raise AbruptException("Unknown redirection, please add some code " \
                                  "in abrupt/http.py:Request.follow")

def create(url):
  """Create a request on the fly, based on a URL"""
  p_url = urlparse.urlparse(url)
  host = p_url.hostname
  if not p_url.path:
    url += "/"
  return Request("""GET {} HTTP/1.1
Host: {}
User-Agent: Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 0.9; en-US)
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en;q=0.5
Accept-Encoding: gzip, deflate
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7

""".format(url, host))

c = create

class Response():
  """A response object, always associated with a request.
  """
  def __init__(self, fd, request, chunk_func=None):
    try:
      banner = read_banner(fd)
      # ASSUMPTION: A response status line contains three elements
      #             seperated by a space
      self.http_version, self.status, self.reason = banner
    except ValueError:
      raise BadStatusLine(banner)
    self.set_headers(read_headers(fd))
    self.request = request
    if request.method == "HEAD":
      self.raw_content = self.content = ""
    else:
      self.raw_content = read_content(fd, self.headers, self.status,
                                      chunk_func=chunk_func)
      if self.raw_content:
        self.content = _clear_content(self.headers, self.raw_content)
      else:
        self.content = ""

  def __repr__(self):
    return self.repr()

  @property
  def time(self):
    return self.received_date - self.sent_date

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
    return _has_header(self.headers, name, value)

  def get_header(self, name):
    """Return the headers of the response matching name (case insensitive).
    This method always returns a list.
    """
    return _get_header(self.headers, name)

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
    ret = subprocess.call(conf.editor.format(fname), shell=True)
    if not ret:
      f = open(fname, 'r')
      self.__init__(f, self.request)
      if self.content:
        self.update_content_length()
      os.remove(fname)

  def copy(self):
    """Copy a Response. Both response will have the same request."""
    res_new = copy.copy(self)
    res_new.headers = copy.deepcopy(self.headers)
    return res_new

  def normalise(self):
    """Normalise the response content by dropping any extra encoding"""
    self.raw_content = res_new.content
    self.remove_header("Transfer-Encoding")
    self.remove_header("Content-Encoding")
    self.update_content_length()

  def remove_header(self, name):
    """Remove all the headers matching the specified name"""
    for i, c in enumerate(self.headers):
      h, v = c
      if h.title() == name:
        del self.headers[i]

  def update_content_length(self):
    """Update the Content-Length header according to the content of the
    response"""
    l = str(len(self.raw_content)) if self.raw_content else "0"
    for i, c in enumerate(self.headers):
      h, v = c
      if h.title() == "Content-Length":
        self.headers[i] = (h, l)
        break
    else:
      self.headers.append(("Content-Length", l))

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
    for h, v in self.headers:
      s.write("{}: {}\r\n".format(h, v))
    s.write("\r\n")
    if not headers_only and self.content:
      s.write(self.content)
    return s.getvalue()

  def raw(self):
    s = StringIO()
    s.write("{s.http_version} {s.status} {s.reason}\r\n".format(s=self))
    for h, v in self.headers:
      s.write("{}: {}\r\n".format(h, v))
    s.write("\r\n")
    if hasattr(self, "raw_content") and self.raw_content:
      s.write(self.raw_content)
    return s.getvalue()

  def set_headers(self, headers):
    self.headers = []
    for l in headers.splitlines():
      if l:
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers.append((t, v))

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
      cols.insert(2, ("Point", lambda r, i: getattr(r, "injection_point", "-"), (2, truncate)))
      cols.insert(3, ("Payload", lambda r, i: getattr(r, "payload", "-").decode("utf8"), (3, truncate)))
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

  def by_length(self):
    return RequestSet(sorted(self.reqs, key=operator.attrgetter("response.length")))

  def by_status(self):
    return RequestSet(sorted(self.reqs, key=operator.attrgetter("response.status")))

  def by_path(self):
    return RequestSet(sorted(self.reqs, key=operator.attrgetter("path")))

  def without_payloads(self):
    return RequestSet([x for x in self.reqs if not hasattr(x, "payload")])

  def _init_connection(self):
    return connect(self.hostname, self.port, self.use_ssl)

  def clear(self):
    for r in self.reqs:
      r.response = None

  def __call__(self, force=False, randomised=False, verbose=1,
               post_func=None, post_args=[]):
    if not self.reqs:
      raise Exception("No request to proceed")
    hostnames = set([r.hostname for r in self.reqs])
    ports = set([r.port for r in self.reqs])
    use_ssls = set([r.use_ssl for r in self.reqs])
    if len(hostnames) > 1 or len(ports) > 1 or len(use_ssls) > 1:
      raise Exception("Only one host per request set to run it")
    self.hostname = hostnames.pop()
    self.port = ports.pop()
    self.use_ssl = use_ssls.pop()
    if force and verbose:
      print "Clearing previous responses..."
      self.clear()
    conn = self._init_connection()
    if verbose:
      print "Running {} requests...".format(len(self.reqs)),
      clear_line()
    indices = range(len(self.reqs))
    if randomised: random.shuffle(indices)
    done = 0
    todo = len(self.reqs)
    for i in indices:
      r = self.reqs[i]
      if verbose:
        print "Running {} requests...{:.2f}%".format(todo, done * 100. / todo),
        clear_line()
      next = False
      if r.response and not force:
        todo -= 1
        next = True
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
        if conf.delay:
          time.sleep(conf.delay)
    if verbose:
      print "Running {} requests...done.".format(len(self.reqs))
    conn.close()

class History(RequestSet):
  """History is a singleton class which contains all the
  requests made through Abrupt.
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
    headers += l
    if l == "\r\n" or l == "\n":
      break
  return headers

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
      raise AbruptException("Invalid Content-Length")
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
      buf = [" ".join([request.method, url, request.http_version]), ]
    else:
      buf = [" ".join([request.method, request.url, request.http_version]), ]
  else:
    buf = [" ".join([request.method, request.url, request.http_version]), ]
  buf += ["{}: {}".format(h, v) for h, v in request.headers] + ["", ""]
  data = "\r\n".join(buf)
  if request.raw_content:
    data += request.raw_content
  # if request.footers:
  #   data += ["{}: {}".format (h, v) for h, v in request.footers] + ["",""]
  sock.sendall(data)
