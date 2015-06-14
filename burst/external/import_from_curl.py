from burst.http import Request, RequestSet

from shlex import split
from base64 import b64encode
from ..http import parse_headers

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
  """create() a RequestSet object from a curl commandline.

     curl-style [start:stop:step] and {a,b,c} counters are supported.
     See http://curl.haxx.se/docs/manpage.html#URL for examples.

     Currently supported options (shorthand form also accepted):
     --header ; --cookie ; --data-ascii ; --request ; --user-agent; --referer ; --user ; --range
  """
  if curl is None:
    curl = raw_input('curl cmdline: ')

  if type(curl) != list:
    curl = split(curl)

  # index counter used for variable parsing
  i = 0

  ## The returned RequestSet():
  rs = RequestSet()

  ## skip leading image name / path component
  if curl[0] == 'curl' or curl[0].startswith('/'):
    i = 1

  HEADERS   = 'HEADERS'
  METHOD    = 'METHOD'
  CONTENT   = 'CONTENT'

  o = { HEADERS   : [] }

  def add_url(url):
    rs.append(create(url.replace(' ','%20')))

  while i < len(curl):
    if curl[i].startswith('-'):
      this = curl[i]
      i   += 1
      arg  = None
      if i < len(curl):
        arg  = curl[i]

      if this in __curl_unimplemented[0].union(__curl_unimplemented[1]):
        print 'not implemented: ignoring option "{}"'.format(this)
        if this in __curl_unimplemented[1]:
          i += 1
        continue

      ## options that require an argument, check that we have one
      elif arg:
        if this in ('-A', '--user-agent'):
          o[HEADERS].append(('User-Agent', arg))
        elif this in ('-b', '--cookie'):
          o[HEADERS].append(arg)
        elif this in ('-d', '--data', '--data-ascii'):
          o[METHOD]  = 'POST'
          o[CONTENT] = arg
        elif this in ('-e', '--referer'):
          o[HEADERS].append(('Referer' , arg))
        elif this in ('-H', '--header'):
          o[HEADERS].append(parse_headers(arg)[0])
        elif this in ('--url'):
          add_url(arg)
        elif this in ('u','--user'):
          if not ':' in arg:
            arg += ':'
          ## TODO this should probably be a first class citizen in Request:
          o[HEADERS].append(('Authorization', 'Basic {}'.format( b64encode(arg) )))
        elif this in ('-r','--range'):
          o[HEADERS].append(('Range', 'bytes={}'.format(arg)))
        elif this in ('-X','--request'):
          o[METHOD] = arg
        else:
          raise Exception('not implemented and unknown option: "{}"'.format(this))

    ## not a --switch, and not an argument, so parse it as a URL:
    else:
      add_url(curl[i])
    i += 1

  if [] == rs.reqs:
    raise Exception('curl string must contain at least one URL')

  ## apply options
  for i in xrange(0,len(rs)):
    rs[i].method  = o.get(METHOD, rs[i].method)
    rs[i].content = o.get(CONTENT, rs[i].content)
    for hd , val in o[HEADERS]:
      if hd not in ('Cookie',):
        ## replace unique headers
        rs[i].remove_header(hd)
      rs[i].add_header(hd, val)

  rs.expand_curl_ranges()

  return rs

