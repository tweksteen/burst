import datetime
from burst.http import Request, RequestSet

try:
  import lxml.html
  import lxml.etree
  has_lxml = True
except ImportError:
  has_lxml = False

def import_from_burp(requests_file):
  if not has_lxml:
    raise Exception("To use the import, you need lxml")
  tree = lxml.etree.parse(requests_file)
  items = tree.getroot()
  rs = RequestSet()
  for item in items:
    r = Request(base64.decodestring(item.find("request").text),
                item.find("host").text,
                item.find("port").text,
                True if item.find("protocol").text == "https" else False)
    raw_date = item.find("time").text
    date_without_tz = " ".join([x for i,x in enumerate(raw_date.split(" ")) if i != 4])
    r.sent_date = datetime.datetime.strptime(date_without_tz, "%c")
    r.response = Response(base64.decodestring(item.find("response").text), r)
    rs.append(r)
    r.response.received_date = r.sent_date
  return rs

