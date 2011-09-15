import re
import sys
import urllib

re_space = re.compile(r'[ \t]+')
re_ansi_color = re.compile(r"(\x1b\[[;\d]*[A-Za-z])|\x01|\x02").sub
re_filter_images = re.compile(r'\.(png|jpg|jpeg|ico|gif)$')

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
