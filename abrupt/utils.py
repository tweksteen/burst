import re
import os
import sys
import time
import math
import json
import base64
import urllib
import tempfile
import threading
import subprocess
import collections

try:
  import termios
  has_termios = True
except ImportError:
  has_termios = False

try:
  from lxml import etree
  has_lxml = True
except ImportError:
  import xml.dom
  import xml.dom.minidom
  has_lxml = False

re_space = re.compile(r'[ \t]+')
re_ansi_color = re.compile(r"(\x1b\[[;\d]*[A-Za-z])|\x01|\x02").sub

ellipsis = u"\u2026"

def bg(fct, *args, **kwds):
  t = threading.Thread(target=fct, args=args, kwargs=kwds)
  t.start()

def jobs():
  for t in threading.enumerate():
    print t.name

def pxml(r):
  if hasattr(r, "content"):
    s = r.content
  else:
    s = r
  if has_lxml:
    try:
      x = etree.fromstring(s)
      return etree.tostring(x, pretty_print = True)
    except ValueError:
      print "Shit Tyrone, get it together!"
    except etree.XMLSyntaxError:
      print "Unable to parse the XML. Looking for goat sex?"
  else:
    try:
      x = xml.dom.minidom.parseString(s)
      return x.toprettyxml()
    except TypeError:
      print "Shit Tyrone, get it together!"
    except (xml.dom.DOMException,xml.parsers.expat.ExpatError):
      print "Unable to parse the XML. Looking for goat sex?"

def pjson(r):
  if hasattr(r, "content"):
    s = r.content
  else:
    s = r
  try:
    j = json.loads(s)
    return json.dumps(j, sort_keys=True, indent=4)
  except ValueError:
      print "Unable to parse the JSON. Looking for octopus sex?"

def truncate(s, max_len):
  return s[:max_len]

def smart_rsplit(s, max_len, sep):
  if len(s) > max_len:
    if sep in s[:-1]:
      orig_len = len(s)
      prev_len = orig_len + 1
      while len(s) > max_len - 2:
        if prev_len == len(s):
          break
        prev_len = len(s)
        s = s.rsplit(sep, 1)[0]
      if len(s) != orig_len:
        s = s + sep + ellipsis
    if len(s) > max_len:
      return ellipsis + s[-max_len:]
  return s

def smart_split(s, max_len, sep):
  if len(s) > max_len:
    if sep in s[1:]:
      orig_len = len(s)
      prev_len = orig_len + 1
      while len(s) > max_len - 2:
        if prev_len == len(s):
          break
        prev_len = len(s)
        s = s.split(sep, 1)[-1]
      if len(s) != orig_len:
        s = ellipsis + sep + s
    if len(s) > max_len:
      return s[:max_len] + ellipsis
  return s

def flush_input():
  if has_termios:
    termios.tcflush(sys.stdin, termios.TCIOFLUSH)

def view(args):
  fd, fname = tempfile.mkstemp()
  with os.fdopen(fd, 'w') as f:
    f.write(str(args))
  subprocess.call(conf.viewer.format(fname), shell=True)
  os.remove(fname)

def external_view(args):
  fd, fname = tempfile.mkstemp()
  with os.fdopen(fd, 'w') as f:
    f.write(str(args))
  subprocess.Popen(conf.external_viewer.format(fname), shell=True, preexec_fn=os.setpgrp)
  #todo: cleanup

def idle(request, delay=60, predicate=None, verbose=False):
  if not predicate:
    predicate = lambda x, y: x.response.status == y.response.status
  x = request
  if not x.response:
    x()
  while True:
    y = x.copy()
    y()
    if verbose:
      print repr(y), repr(y.response)
    if not predicate(x, y):
      return
    x = y
    time.sleep(delay)

def stats(values):
  avg = sum(values) / float(len(values))
  variance = sum([x ** 2 for x in values]) / float(len(values)) - avg ** 2
  std = math.sqrt(variance)
  bottom = avg - 3 * std
  top = avg + 3 * std
  return avg, bottom, top

def urlencode(query):
  l = []
  for k, v in query.items():
    if isinstance(v, collections.Iterable):
      for elt in v:
        l.append(str(k) + '=' + str(elt))
    else:
      l.append(str(k) + '=' + str(v))
  return '&'.join(l)

def parse_qsl(qs):
  pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
  r = []
  for name_value in pairs:
    nv = name_value.split('=', 1)
    if len(nv) != 2:
      nv.append('')
    name = nv[0]
    value = nv[1]
    r.append((name, value))
  return r

def parse_qs(qs):
  d = {}
  for name, value in parse_qsl(qs):
    if name in d:
      d[name].append(value)
    else:
      d[name] = [value]
  return d

def encode(s, **kwds):
  return urllib.quote_plus(s, **kwds)

e = encode

def ee(s):
  return e(e(s))

def decode(s):
  return urllib.unquote_plus(s)

d = decode

def dd(s):
  return d(d(s))

def d64(s):
  return base64.standard_b64decode(s)

def e64(s):
  return base64.standard_b64encode(s)

def remove_color(s):
  return  re_ansi_color("", s)

def _ljust(v, l):
  return v + " " * (l - len(remove_color(v)))

def make_table(requests, fields, width=80):
  data = []
  fields_len = {}
  fields_names = zip(*fields)[0]
  for name, fct, elasticity in fields:
    fields_len[name] = len(name)
  for i, request in enumerate(requests):
    request_field = []
    for name, fct, elasticity in fields:
      v = fct(request, i)
      request_field.append(v)
      if len(remove_color(v)) > fields_len[name]:
        fields_len[name] = len(remove_color(v))
    data.append(request_field)

  to_adjust = dict([(name, elasticity) for name,_,elasticity in fields if elasticity])

  done = False
  while not done and to_adjust:
    final_len = {}
    remaining_width = width - sum([(fields_len[name]+1) for name,_,_ in fields if name not in to_adjust])
    total_weight = sum(zip(*to_adjust.values())[0])
    for name, params in to_adjust.items():
      elasticity = params[0]
      fl = int(remaining_width * (float(elasticity)/total_weight)) - 1
      if fl < fields_len[name]:
        final_len[name] = fl
      else:
        del to_adjust[name]
        break
    else:
      done = True
  for n in fields_len:
    if n not in final_len:
      final_len[n] = fields_len[n]
  output = u"".join([_ljust(n, final_len[n] + 1) for n in fields_names]) + "\n"
  line = []
  for row in data:
    for i, column in enumerate(row):
      cname = fields_names[i]
      if cname in to_adjust:
        trim_fct = to_adjust[cname][1]
        v = trim_fct(column, final_len[cname], *to_adjust[cname][2:])
      else:
        v = column
      v = _ljust(v, final_len[cname] + 1)
      line.append(v)
    line.append("\n")
  output += u"".join(line)
  return output

def clear_line():
  print "\r",
  sys.stdout.flush()

def test_make_table():
  import termios
  import fcntl
  import struct
  for i in range(3):
    try:
      bin_size = fcntl.ioctl(i, termios.TIOCGWINSZ, '????')
      _, width = struct.unpack('hh', bin_size)
    except:
      width = 80
  reqs = [["/path1/blah/test/1/2/application.aspx", "q=test&rap=4", "200", "4324"],
          ["/path3/blah/test/4/5/my_favorite_applet.jsp", "q=test&rap=admin", "200", "4324"],
          ["/path2/testing", "q=t&mytoken=1AB20C2E1F99275F28A39757B", "500", "0"]]
  print make_table(reqs, [
      ("Id", lambda r,i: str(i), None),
      ("Path", lambda r,i: r[0], (9, smart_split, "/")),
      ("Query", lambda r,i: r[1], (4, smart_rsplit, "&")),
      ("Status", lambda r,i: r[2], None),
      ("Length", lambda r,i: r[3], None)], width)

def test_smart_split():
  exs = ( (u"/blah/test", u"/blah/test", 10, "/"),
          (u"/blah/test22", u"\u2026/test22", 10, "/"),
          (u"/blah/test23", u"\u2026/test23", 9, "/"),
          (u"/blah/test24", u"\u2026/test24", 11, "/"),
          (u"/blah/test26", u"/blah/test26", 12, "/"),
          (u"/blah/test25", u"\u2026/tes\u2026", 5, "/"),
          (u"test2222", u"test2\u2026", 5, "/"),
          (u"/test4444", u"/test\u2026", 5, "/"),
        )
  for o, e, si, sep in exs:
    if smart_split(o, si, sep) != e:
      print o, si, " -> ", smart_split(o, si, sep), " != ", e

if __name__ == '__main__':
  test_make_table()
