import urlparse
from BeautifulSoup import BeautifulSoup

from abrupt.http import RequestSet

def get_links(content):
  soup = BeautifulSoup(content)  
  links = [ x["href"] for x in  soup.findAll('a')]
  return links
  
def spider(requests):
  new_reqs = []
  for r in requests:
    if not r.response: continue
    if not r.response.readable_content: continue
    links = get_links(r.response.readable_content)
    for l in links:
      url_p = urlparse.urlparse(l)
      if url_p.scheme == 'http':
        new_reqs.append(c(l))
      elif url_p.scheme == 'javascript': 
        continue
      elif url_p.scheme == '':
        if url_p.path:
          nr = r.copy()
          n_path = urlparse.urljoin(r.url, l)
          nr.url = urlparse.urlunparse(urlparse.urlparse(r.url)[:2] + urlparse.urlparse(n_path)[2:])
          new_reqs.append(nr)
      else:
        raise Exception("Miam!?:" + l)
  return RequestSet(new_reqs)

def s(r):
  return spider([r,]) 

