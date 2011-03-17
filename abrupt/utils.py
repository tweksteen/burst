import re
import string 
from collections import OrderedDict

def make_table(requests, fields, width=None):
  data = []
  fields_len = OrderedDict()
  for field in fields:
    fields_len[field] = len(field)
  for request in requests:
    request_field = []
    for field_name, field_function in fields.items():
      v = field_function(request)
      request_field.append(v)
      if len(remove_color(v)) > fields_len[field_name]: fields_len[field_name] = len(remove_color(v))
    data.append(request_field)
  if width:
    for k in width:
      fields_len[k] = width[k]
  output = ""
  for name, length in fields_len.items():
    output += string.ljust(name, length + 1)  
  output += "\n"
  for row in data:
    for i, cell in enumerate(row):
      output += cell + " " * (fields_len[fields_len.items()[i][0]] + 1 - len(remove_color(cell)))
    output += "\n"
  return output
 
strip_ANSI_color = re.compile(r"(\x1b\[[;\d]*[A-Za-z])|\x01|\x02").sub
def remove_color(s):
    return  strip_ANSI_color("", s)

def test():
  from color import color_status
  reqs = [[ "/path1", "q=test&rap=4", "200", "4324"], 
          [ "/path2/testing", "q=t'--", "500", "0"],] 
  print make_table(reqs, OrderedDict([
      ("Path", lambda r: r[0]),
      ("Query", lambda r: r[1]),
      ("Status", lambda r: color_status(r[2])),
      ("Length", lambda r: r[3])
      ]), width={"Status": 6})


if __name__ == '__main__':
  test() 
