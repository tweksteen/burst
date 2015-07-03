import re
import burst.http
from hashlib import sha256

re_curl_counter = re.compile(r"""
    (?# ignore patterns with leading unbalanced backslashes )
      (?P<escaped> \x5c ?  )
      (?P<leading_escapes> (?: \x5c\x5c )* )
    \[
      (?P<start> [0-9]+ )
      -
      (?P<stop>  [0-9]+ )
      (?# optionally take a step argument: )
        :?
        (?P<step>  [0-9]* )
    \]  """, re.VERBOSE)

re_curl_characters = re.compile(r"""
    (?# ignore patterns with leading unbalanced backslashes )
      (?P<escaped> \x5c ?  )
      (?P<leading_escapes> (?: \x5c\x5c )* )
    \[
      (?P<start> [^-\n] )
      -
      (?P<stop>  [^-\n] )
      (?# optionally take a step argument: )
        :?
        (?P<step> [0-9]* )
    \]  """, re.VERBOSE)

re_curl_brace_set = re.compile(r"""
    (?# ignore patterns with leading unbalanced backslashes )
      (?P<escaped> \x5c ?  )
      (?P<leading_escapes> (?: \x5c\x5c )* )
    \{
      (?P<first> ( [^\n,]* ,)* )
      (?P<last>    [^\n,]* )
    \} """, re.VERBOSE)


def expand_curl_ranges(r):
  """Expands curl range sequences in the Request, returning a new RequestSet"""
  matches = {}

  def param_inject(s):
    def _param_inject(generator):
      ## can't come up with a better/faster way to generate unique keys in a thread-safe fashion :-(
      key = sha256('{}_{}'.format(len(matches), str(r))).hexdigest()[:20]
      matches[key] = {
        'at': key,
        'payloads': generator }
      return key

    def _param_inject_counter(m):
      escapes = m.expand(m.group('leading_escapes'))
      if m.group('escaped'):
        ret = escapes + m.string[m.end('leading_escapes') : m.end(0)]
        return _param_inject( [ ret ] )

      values = [int(i or '1') for i in m.group(3, 4)]
      ## NOTE: curl's ranges are inclusive; python's are not, account for that:
      values[1] += 1
      return _param_inject( (escapes + str(i) for i in xrange(*values)) )

    def _param_inject_characters(m):
      escapes = m.expand(m.group('leading_escapes'))
      start = ord(m.group('start'))
      ## NOTE: curl's ranges are inclusive; python's are not, account for that:
      stop  = ord(m.group('stop')) + 1
      if m.group('escaped'):
        ret = escapes + m.string[m.end('leading_escapes') : m.end(0)]
        return _param_inject( [ ret ] )
      step  = int( m.group('step') or '1' )
      return _param_inject(
        (escapes + chr(c) for c in xrange(start, stop, step)) )

    def _param_inject_brace_set(m):
      escapes = m.expand(m.group('leading_escapes'))
      first = m.group('first') or ''
      last  = [m.group('last') or '']
      if m.group('escaped'):
        ret = escapes + m.string[m.end('leading_escapes') : m.end(0)]
        return _param_inject( [ret] )
      intermediary = first.split(',')[:-1]
      return _param_inject( (escapes + g for g in intermediary + last) )

    ## replace the patterns with the corresponding hashes:
    ret = re_curl_counter.sub(_param_inject_counter, s)
    ret = re_curl_characters.sub(_param_inject_characters, ret)
    ret = re_curl_brace_set.sub(_param_inject_brace_set, ret)
    return ret

  ## Configure the prototype and set up sequence hooks
  proto = r.copy()
  proto.url         = param_inject( proto.url )
  proto.content     = param_inject( proto.content )
  proto.raw_headers = param_inject( proto.raw_headers )

  rs = burst.http.RequestSet([proto,])
  for params in matches.values():
    rs = inject(rs, at=params['at'], payloads=params['payloads'])
  return rs
