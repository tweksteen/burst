import re
import os
import sys
import math
import urllib
import tempfile
import subprocess
import collections

re_space = re.compile(r'[ \t]+')
re_ansi_color = re.compile(r"(\x1b\[[;\d]*[A-Za-z])|\x01|\x02").sub
re_images_ext = re.compile(r'\.(png|jpg|jpeg|ico|gif)$')

ellipsis = u"\u2026"

def smart_rsplit(s, max_len, sep):
  return smart_split(s, max_len, sep, reverse=True)

def smart_split(s, max_len, sep, reverse=False):
  i = 1
  prev_len = len(s) + 1
  while len(s) > max_len:
    if prev_len == len(s):
      break
    prev_len = len(s)
    if reverse:
      s = s.rsplit(sep, i)[0]
    else:
      s = s.split(sep, i)[-1]
  if reverse:
    return s[-max_len:]
  return s[:max_len]

def less(args):
  fd, fname = tempfile.mkstemp()
  with os.fdopen(fd, 'w') as f:
    f.write(str(args))
  subprocess.call('less' + ' -R ' + fname, shell=True)
  os.remove(fname)

def stats(values):
  avg = sum(values)/float(len(values))
  variance = sum([x**2 for x in values])/float(len(values)) - avg**2
  std = math.sqrt(variance)
  bottom = avg - 3*std
  top = avg + 3*std
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

def remove_color(s): 
  return  re_ansi_color("", s)

def _ljust(v, l):
  return v + " " *  (l - len(remove_color(v)))

def make_table(requests, fields):
  data = []
  fields_len = {}
  fields_names = zip(*fields)[0]
  for field_name, field_function in fields:
    fields_len[field_name] = len(field_name)
  for i, request in enumerate(requests):
    request_field = []
    for field_name, field_function in fields:
      v = field_function(request, i)
      request_field.append(v)
      if len(remove_color(v)) > fields_len[field_name]: 
        fields_len[field_name] = len(remove_color(v))
    data.append(request_field)
  output = u"".join([_ljust(n, fields_len[n] + 1) for n in fields_names]) + "\n"
  for r in data:
    output += u"".join([_ljust(c, fields_len[fields_names[i]] + 1) 
                              for i, c in enumerate(r)])
    output += u"\n"
  return output

def clear_line():
  print "\r",
  sys.stdout.flush() 

def test():
  from color import color_status
  reqs = [[ "/path1", "q=test&rap=4", "200", "4324"], 
          [ "/path2/testing", "q=t'--", "500", "0"],] 
  print make_table(reqs, [
      ("Path", lambda r: r[0]),
      ("Query", lambda r: r[1]),
      ("Status", lambda r: color_status(r[2])),
      ("Length", lambda r: r[3])
      ])


if __name__ == '__main__':
  test() 
