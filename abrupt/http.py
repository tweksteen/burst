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
import subprocess
import datetime
import Cookie
from collections import defaultdict
from StringIO import StringIO

from abrupt.conf import conf
from abrupt.color import *
from abrupt.utils import make_table, clear_line, \
                         re_space, smart_split, smart_rsplit, \
                         stats, parse_qs
class AbruptException(Exception):
  def __repr__(self):
    return "<{}: {}>".format(error(self.__class__.__name__), str(self))
class UnableToConnect(AbruptException):
  def __init__(self, message="Unable to connect to the server"):
    AbruptException.__init__(self, message)
class NotConnected(AbruptException):
  def __init__(self, junk):
    self.junk = junk
    AbruptException.__init__(self, "Unable to read the request from the client")
  def __str__(self):
    return self.message + " [" + str(self.junk) + "]"
class BadStatusLine(AbruptException):
  def __init__(self, junk):
    self.junk = junk
    AbruptException.__init__(self, "They host did not return a correct banner")
  def __str__(self):
    return self.message + " [" + str(self.junk) + "]"
class ProxyError(AbruptException):
  pass

class Request():
  """The Request class is the base of Abrupt. To create an instance, you have
  two options: either use a socket or a string representing the whole request
  into the constructor or use the 'create' function.

  The two methods __repr__ and __str__ have been defined to provide
  user friendly interaction inside the interpreter.
  """

  def __init__(self, fd, hostname=None, port=80, use_ssl=False):
    """Create a request. fd should be either a socket descriptor
       or a string. In both case, it should contain a full request.
       To generate a request from a URL, see c()"""
    if isinstance(fd, basestring):
      fd = StringIO(fd)
    try:
      banner = read_banner(fd)
      self.method, url, self.http_version = banner
    except ValueError:
      raise NotConnected(' '.join(banner))
    if self.method.upper() == "CONNECT":
      self.hostname, self.port = url.split(":", 1)
    else:
      p_url = urlparse.urlparse(url)
      self.url = urlparse.urlunparse(("", "") + p_url[2:])
      self.hostname = p_url.hostname or hostname
      if not self.hostname:
        raise AbruptException("No hostname: " + str(url))
      else:
        if p_url.scheme == 'https':
          self.use_ssl = True
          self.port = int(p_url.port) if p_url.port else 443
        else:
          self.port = int(p_url.port) if p_url.port else port
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
    b = Cookie.SimpleCookie()
    for v in self.get_header("Cookie"):
      try:
        b.load(v)
      except Cookie.CookieError:
        print "TODO: fix the default cookie library"
    return b

  def has_header(self, name, value=None):
    """Test if the request contained a specific headers (case insensitive).
    If value is supplied, it is matched (case insensitive) against the first
    header with the matching name.
    """
    return _has_header(self.headers, name, value)

  def get_header(self, name):
    """Return the first header of the request matching name (case insensitive).
    """
    return _get_header(self.headers, name)

  def set_headers(self, headers):
    self.headers = []
    # ASSUMPTION: Headers are seperated by a newline character
    for l in headers.splitlines():
      if l:
        # ASSUMPTION: Each header is composed of two fields seperated by
        #             a semi-colon.
        t, v = [q.strip() for q in l.split(":", 1)]
        self.headers.append((t, v))

  def _update_content_length(self):
    l = str(len(self.content)) if self.content else "0"
    for i, c in enumerate(self.headers):
      h, v = c
      if h.title() == "Content-Length":
        self.headers[i] = (h, l)
        # ASSUMPTION: There is only one Content-Length header per request
        break
    else:
      self.headers.append(("Content-Length", l))

  def _remove_content_length(self):
    for i, c in enumerate(self.headers):
      h, v = c
      if h.title() == "Content-Length":
        del self.headers[i]

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
    s.write("{s.method} {s.url} {s.http_version}\r\n".format(s=self))
    for h, v in self.headers:
      s.write("{}: {}\r\n".format(h, v))
    s.write("\r\n")
    if not headers_only and self.content:
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

  def __call__(self, conn=None, chunk_callback=None):
    """Make the request to the server.
    If conn is supplied, it will be used as connection socket. If
    chunk_callback is supplied, it will be call for every chunk
    received, if appplicable.
    """
    if conn:
      sock = conn
    else:
      sock = connect(self.hostname, self.port, self.use_ssl)
    if conf.history:
      history.append(self)
    _send_request(sock, self)
    n1 = datetime.datetime.now()
    self.response = Response(sock.makefile('rb', 0), self,
                             chunk_callback=chunk_callback)
    n2 = datetime.datetime.now()
    self.response.time = n2 - n1

  def edit(self):
    """Edit the request. The original request is not modified, a new
    one is returned.
    """
    options = conf.editor_args if conf.editor_args else ""
    r_tmp = self.copy()
    if conf.update_content_length:
      r_tmp._remove_content_length()
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(str(r_tmp))
      f.write("\n")
    ret = subprocess.call(conf.editor + " " + fname + " " + options, shell=True)
    if not ret:
      f = open(fname, 'r')
      r_new = Request(f, self.hostname, self.port, self.use_ssl)
      if r_new.method in ('POST', 'PUT'):
        r_new._update_content_length()
      os.remove(fname)
      return r_new

  def play(self):
    """Start your editor with two windows. Each time the request file is saved,
    the request is made to the server and the response updated. When the editor
    terminates, the last valid request made is returned.
    """
    options = conf.editor_args if conf.editor_args else ""
    options += " "
    options += conf.editor_play_args if conf.editor_play_args else ""
    r_tmp = self.copy()
    if conf.update_content_length:
      r_tmp._remove_content_length()
    fdreq, freqname = tempfile.mkstemp(suffix=".http")
    fdrep, frepname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fdreq, 'w') as f:
      f.write(str(r_tmp))
      f.write("\n")
    if self.response:
      with os.fdopen(fdrep, 'w') as f:
        f.write(str(self.response))
    ret = subprocess.Popen(conf.editor + " " + freqname + " " +
                           frepname + " " + options, shell=True)
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

  def extract(self, arg, from_response=None):
    """Extract a particular field of the request.
    The field is looked up in:
      * attributes
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
    if self.query:
      query = parse_qs(self.query)
      if arg in query:
        return query[arg][0]
    if self.content:
      post = parse_qs(self.content)
      if arg in post:
        return post[arg][0]
    c = self.cookies
    if c:
      if arg in c:
        return c[arg].value
    if from_response is None and self.response:
      return self.response.extract(arg)

  def filter(self, predicate):
    return bool(predicate(self))

  def follow(self):
    """Try to follow the request (i.e., generate a new request based
    on redirection information).
    """
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
            raise Exception("Unknown redirection, please add some code " \
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
  def __init__(self, fd, request, chunk_callback=None):
    try:
      banner = read_banner(fd)
      self.http_version, self.status, self.reason = banner
    except ValueError:
      raise BadStatusLine(banner)
    self.set_headers(read_headers(fd))
    self.request = request
    if request.method == "HEAD":
      self.raw_content = self.content = ""
    else:
      self.raw_content = read_content(fd, self.headers, self.status,
                                      chunk_callback=chunk_callback)
      if self.raw_content:
        self.content = _clear_content(self.headers, self.raw_content)
      else:
        self.content = ""

  def __repr__(self):
    return self.repr()

  def repr(self, rl=False):
    flags = []
    if self.content: flags.append(str(len(self.content)))
    if self.has_header("Content-Type"):
      flags.append(",".join([x.split(";")[0] for x in
                                             self.get_header("Content-Type")]))
    if self.has_header("Transfer-Encoding", "chunked"): flags.append("chunked")
    if self.has_header("Content-Encoding", "gzip"): flags.append("gzip")
    if self.has_header("Content-Encoding", "deflate"): flags.append("deflate")
    for c in self.get_header("Set-Cookie"):
      flags.append("C:" + c)
    return "<" + color_status(self.status, rl) + " " + " ".join(flags) + ">"

  def has_header(self, name, value=None):
    """Test if the response contained a specific headers (case insensitive).
    If value is supplied, it is matched (case insensitive) against the first
    header with the matching name.
    """
    return _has_header(self.headers, name, value)

  def get_header(self, name):
    """Return the first header of the response matching name (case insensitive).
    """
    return _get_header(self.headers, name)

  def view(self):
    """Start your editor on a dump of the response
    """
    options = conf.editor_args if conf.editor_args else ""
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(str(self))
    subprocess.call(conf.editor + " " + fname + " " + options, shell=True)
    os.remove(fname)

  def edit(self):
    """Edit the response through your editor. A new reponse is
    returned.
    """
    options = conf.editor_args if conf.editor_args else ""
    fd, fname = tempfile.mkstemp(suffix=".http")
    with os.fdopen(fd, 'w') as f:
      f.write(self.raw())
    ret = subprocess.call(conf.editor + " " + fname + " " + options, shell=True)
    if not ret:
      f = open(fname, 'r')
      res_new = Response(f, self.request)
      if res_new.content:
        res_new._update_content_length()
      os.remove(fname)
      return res_new

  def _update_content_length(self):
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
    b = Cookie.SimpleCookie()
    for v in self.get_header("Set-Cookie"):
      try:
        b.load(v)
      except Cookie.CookieError:
        print "TODO: fix the default cookie library"
    return b

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
      * cookies
    """
    if hasattr(self, arg):
      return getattr(self, arg)
    c = self.cookies
    if arg in c:
      return c[arg].value

  def filter(self, predicate):
    return bool(predicate(self))

def compare(r1, r2):
  fd1, f1name = tempfile.mkstemp(suffix=".http")
  fd2, f2name = tempfile.mkstemp(suffix=".http")
  with os.fdopen(fd1, 'w') as f:
    f.write(str(r1))
  with os.fdopen(fd2, 'w') as f:
    f.write(str(r2))
  subprocess.call(conf.diff_editor + " " + f1name + " " + f2name, shell=True)
  os.remove(f1name)
  os.remove(f2name)

cmp = compare

class RequestSet():
  """Set of request. This object behave like a list.
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

  def __unicode__(self):

    def n_length(r, i):
      if r.response and r.response.content:
        p = str(len(r.response.content))
        if hasattr(r, "payload"):
          p += "(" + str(len(r.response.content)-len(encode(r.payload))) + ")"
        return p
      else:
        return "-"

    cols = [
            ("Method", lambda r, i: info(r.method)),
            ("Path", lambda r, i: smart_split(r.path, 30, "/")),
            ("Status", lambda r, i: color_status(r.response.status) if r.response else "-"),
            ("Length", n_length)]

    if any([hasattr(x, "payload") for x in self.reqs]):
      cols.insert(2, ("Injection Point", lambda r, i: getattr(r, "injection_point", "-")[:20]))
      cols.insert(3, ("Payload", lambda r, i: getattr(r, "payload", "-")[:20]))
      cols.append(("Time", lambda r, i: "{:.4f}".format(r.response.time.total_seconds()) if
                                        (r.response and hasattr(r.response, "time")) else "-"))
    else:
      cols.insert(2, ("Query", lambda r, i: smart_rsplit(r.query, 30, "&")))
    if len(set([r.hostname for r in self.reqs])) > 1:
      cols.insert(1, ("Host", lambda r, i: smart_rsplit(r.hostname, 20, ".")))
    if len(self.reqs) > 5:
      cols.insert(0, ("Id", lambda r, i: str(i)))
    return make_table(self.reqs, cols)

  def summary(self):
    lengths = [r.response.length for r in self.reqs if r.response]
    avg, bottom, top = stats(lengths)
    print "Length: {:.2f} {:.2f} {:.2f}".format(bottom, avg, top)
    outsiders = [(i, r) for i, r in enumerate(self.reqs)
                       if r.response and (r.response.length < bottom or r.response.length > top)]
    if outsiders:
      print "\n".join([" |" + str(i) + " " + getattr(r, "payload", "-") + " " + error(str(r.response.length)) for i, r in outsiders])

    print
    times = [r.response.time.total_seconds() for r in self.reqs if r.response]
    avg, bottom, top = stats(times)
    print "Time: {:.2f} {:.2f} {:.2f}".format(bottom, avg, top)
    outsiders = [(i, r) for i, r in enumerate(self.reqs)
                        if r.response and (r.response.time.total_seconds() < bottom or
                         r.response.time.total_seconds() > top)]
    if outsiders:
      print "\n".join([" |" + str(i) + " " + getattr(r, "payload", "-") + " " + error(str(r.response.time)) for i, r in outsiders])


  def by_length(self):
    return RequestSet(sorted(self.reqs, key=operator.attrgetter("response.length")))

  def by_status(self):
    return RequestSet(sorted(self.reqs, key=operator.attrgetter("response.status")))

  def _init_connection(self):
    return connect(self.hostname, self.port, self.use_ssl)

  def clear(self):
    for r in self.reqs:
      r.response = None

  def __call__(self, post_callback=None, force=False, randomised=False, verbose=False):
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
    if force:
      print "Clearing previous responses..."
      self.clear()
    conn = self._init_connection()
    print "Running {} requests...".format(len(self.reqs)),
    clear_line()
    indices = range(len(self.reqs))
    if randomised: random.shuffle(indices)
    done = 0
    todo = len(self.reqs)
    for i in indices:
      r = self.reqs[i]
      if not verbose:
        print "Running {} requests...{}%".format(todo, done * 100 / todo),
        clear_line()
      next = False
      if r.response and not force:
        todo -= 1
        next = True
      while not next:
        try:
          if verbose: print repr(r)
          r(conn=conn)
          if post_callback: post_callback(r)
          if verbose: print repr(r.response)
          if r.response.closed:
            conn = self._init_connection()
          done += 1
          next = True
        except (socket.error, BadStatusLine):
          conn = self._init_connection()
          next = False
        if conf.delay:
          time.sleep(conf.delay)
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

def read_content(fp, headers, status=None, method=None, chunk_callback=None):
  if status == "304":
    return None
  elif _has_header(headers, "Transfer-Encoding", "chunked"):
    return _chunked_read_content(fp, chunk_callback=chunk_callback).getvalue()
  elif _has_header(headers, "Content-Length"):
    # ASSUMPTION: The first Content-Length header will be use to
    #             read the response
    length_str = _get_header(headers, "Content-Length")[0]
    # ASSUMPTION: The value of Content-Length can be converted to an integer
    length = int(length_str)
    if length < 0:
      raise AbruptException("Invalid Content-Length")
    return _read_content(fp, length).getvalue()
  elif status == "200" or method == "POST":
    # ASSUMPTION: In case we have no indication on what to read, if the method
    #             is POST or the status 200, we read until EOF
    return fp.read()
  return None

def _chunked_read_content(fp, chunk_callback=None):
  buffer = StringIO()
  while True:
    diff = ""
    l = fp.readline()
    diff += l
    s = int(l, 16)
    if s == 0:
      diff += fp.readline()
      buffer.write(diff)
      if chunk_callback:
        chunk_callback(diff)
      return buffer
    diff += _read_content(fp, s).getvalue()
    diff += fp.readline()
    buffer.write(diff)
    if chunk_callback:
      chunk_callback(diff)

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
    sock.recv(5)
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
      sock = ssl.wrap_socket(sock, ssl_version=conf._ssl_version)
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
    sock = ssl.wrap_socket(sock, ssl_version=conf._ssl_version)
  return sock

def _direct_connect(hostname, port, use_ssl):
  try:
    sock = socket.create_connection((hostname, port))
  except socket.error:
    raise UnableToConnect()
  if use_ssl:
    try:
      sock = ssl.wrap_socket(sock, ssl_version=conf._ssl_version)
    except socket.error:
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
  if request.content:
    data += request.content
  sock.sendall(data)
