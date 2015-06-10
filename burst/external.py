import datetime
from burst.http import Request, RequestSet

## import_from_curl dependencies:
from shlex import split
from urlparse import urlparse
from base64 import b64encode
from hashlib import pbkdf2_hmac
from os import urandom
from re import VERBOSE, compile

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


## curl switches currently NOT supported ("gracefully" ignored)
__curl_unimplemented = {
  0: frozenset(( # takes 0 arguments
    '-#', '--progress-bar'
    ,'-0', '--http1.0'
    ,'-1','--tlsv1','--tlsv1.0','--tlsv1.1','--tlsv1.2'
    ,'-2','--sslv2','-3','--sslv3'
    ,'-4','--ipv4'
    ,'-6','--ipv6','-a','--append','--anyauth'
    ,'-B','--use-ascii','--basic','--compressed','--create-dirs','--crlf'
    ,'--digest','--disable-eprt','--disable-epsv','--environment'
    ,'-f','--fail','--ftp-create-dirs','--ftp-pasv','--ftp-skip-pasv-ip'
    ,'--ftp-pret','--ftp-ssl-ccc','--ftp-ssl-control','-g','--globoff'
    ,'--ignore-content-length','-i','--include','-I','--head'
    ,'-j','--junk-session-cookies','-J','--remote-header-name'
    ,'-k','--insecure','-l','--list-only','-L','--location','--location-trusted'
    ,'--metalink','-n','--netrc','-N','--no-buffer','--netrc-optional'
    ,'--negotiate','--no-keepalive','--no-sessionid','--ntlm'
    ,'-O','--remote-name','-p','--proxy-tunnel'
    ,'--post301','--post302','--post303','--proxy-anyauth','--proxy-basic'
    ,'--proxy-digest','--proxy-negotiate','--proxy-ntlm','-q'
    ,'-R','--remote-time','--raw','--remote-name-all','-s','--silent'
    ,'--sasl-ir','-S','--show-error','--ssl','--ssl-reqd','--ssl-allow-beast'
    ,'--tcp-nodelay','--tr-encoding','--trace-time','-v','--verbose','--xattr'
    ,'-h','--help','-M','--manual','-V','--version'
    )),
  1: frozenset(( # takes 1 argument
     '-c','--cookie-jar','-C','--continue-at'
    ,'--ciphers','--connect-timeout','--crlfile','-D','--dump-header'
    ,'--data-binary','--data-urlencode','--delegation'
    ,'-E','--cert','--engine','--egd-file','--cert-type','--cacert','--capath'
    ,'-F','--form','--ftp-account','--ftp-alternative-to-user','--ftp-method'
    ,'--ftp-ssl-ccc-mode','--form-string','--hostpubmd5','--interface'
    ,'-K','--config','--keepalive-time','--key','--key-type','--krb'
    ,'--libcurl','--limit-rate','--local-port','-m','--max-time','--mail-auth'
    ,'--mail-from','--max-filesize','--mail-rcpt','--max-redirs','--noproxy'
    ,'-o','--output','-P','--ftp-port','--pass','--proto','--proto-redir'
    ,'--proxy1.0','--pubkey','-Q','--quote','--random-file'
    ,'--resolve','--retry','--retry-delay','--retry-max-time'
    ,'--socks4','--socks4a','--socks5-hostname','--socks5','--socks5-gssapi-nec'
    ,'--stderr','-t','--telnet-option','-T','--upload-file','--tftp-blksize'
    ,'--tlsauthtype','--tlsuser','--tlspassword','--trace','--trace-ascii'
    ,'-U','--proxy-user','-w','--write-out'
    ,'-x','--proxy','-y','--speed-time','-Y','--speed-limit','-z','--time-cond'
    )) }

def import_from_curl(curl=None):
  """create() a Request object from a curl commandline.
     curl-style [start:stop:step] counters result in a RequestSet being returned

     Currently supported options (shorthand form also accepted):
     --header ; --cookie ; --data-ascii ; --request ; --user-agent; --referer ; --user ; --range
  """
  if curl is None:
      curl = raw_input('curl cmdline: ')

  if type(curl) != list:
    curl = split(curl)

  i = 0

  ## unique replacement value for this RequestSet used with inject()
  uniqueness = urandom(16)
  ## this is defined as a list because Python's scoping rules requires it. wtf.
  inject_counter = [0]

  re_curl_counter = re.compile(r"""
    \[
    (?P<start> [0-9]+ )
    -
    (?P<stop>  [0-9]+ )
    (?# optionally take a step argument: )
    :?
    (?P<step>  [0-9]* )
    \]""", re.VERBOSE)

  ## skip leading image name / path component
  if curl[0] == 'curl' or curl[0].startswith('/'):
    i = 1

  AUTH      = 'AUTH'
  HEADERS   = 'HEADERS'
  HOST      = 'HOST'
  URL       = 'URL'
  METHOD    = 'METHOD'
  USERAGENT = 'USERAGENT'
  BODY      = 'BODY'
  INJECTS   = 'INJECTS'

  o = { HEADERS   : []
      , METHOD    : 'GET'
      , BODY      : ''
      , USERAGENT : 'Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 0.9; en-US)'
      , INJECTS   : {}
      }

  def expand_injects(s):
    matches = []
    for m in re_curl_counter.finditer(s):
      inject_counter[0] += 1
      key = pbkdf2_hmac('sha256', uniqueness,
        '{}_{}'.format(inject_counter, m.start()),1).encode('hex')
      matches.append(key)
      values = [int(i or '1') for i in m.groups()]

      ## curl's ranges are inclusive; python's are not:
      values[1] += 1

      o[INJECTS][key] = {
        'at': key,
        'payloads': [str(i) for i in xrange(*values)]
        }
    for key in matches:
      s = re_curl_counter.sub(key, s, count=1)
    return s

  def set_url(o, url):
    p_url = urlparse(url)
    if p_url.scheme:
      o[URL] = url
    else:
      print 'no protocol supplied for URL "%s", defaulting to https' % url
      o[URL] = 'https://' + url
    o[HOST] = url
    if p_url.hostname:
      o[HOST] = p_url.hostname
    if not p_url.path or not '/' in p_url.path:
      o[URL] += '/'
    return o

  while i < len(curl):
    if curl[i].startswith('-'):
      this = curl[i]
      i   += 1
      arg  = expand_injects(curl[i])
      if this in __curl_unimplemented[0].union(__curl_unimplemented[1]):
        print 'not implemented: ignoring option "{}"'.format(this)
        if this in __curl_unimplemented[1]:
          i += 1
        continue
      elif this in ('-A', '--user-agent'):
        o[USERAGENT] = arg
      elif this in ('-b', '--cookie'):
        o[HEADERS].append('Cookie: {}'.format(arg))
      elif this in ('-d', '--data', '--data-ascii'):
        o[METHOD] = 'POST'
        o[BODY]   = arg
      elif this in ('-e', '--referer'):
        o[HEADERS].append('Referer: {}'.format(arg))
      elif this in ('-H', '--header'):
        o[HEADERS].append(arg)
      elif this in ('--url'):
        o = set_url(o, arg)
      elif this in ('u','--user'):
        if not ':' in arg:
          arg += ':'
        o[HEADERS].append('Authorization: Basic {}'.format(
          b64encode(arg) ))
      elif this in ('-r','--range'):
        o[HEADERS].append('Range: bytes={}'.format(arg))
      elif this in ('-X','--request'):
        o[METHOD] = arg
      else:
        raise Exception('not implemented and unknown option: "{}"'.format(this))
    else:
      o = set_url(o, expand_injects(curl[i]))
    i += 1
  if not URL in o:
    raise Exception('curl string must contain a URL')

  request = """{o[METHOD]} {o[URL]} HTTP/1.1\r
Host: {o[HOST]}\r
User-Agent: {o[USERAGENT]}\r
Accept-Encoding: gzip, deflate\r
{headers}\r
{o[BODY]}\r\n\r\n""".format( o = o
                       , headers = '\r\n'.join(o[HEADERS])
                       )
  request = Request(request)

  for params in o[INJECTS].values():
    ## turn the Request into a RequestSet object
    request = inject(request, **params)

  return request

