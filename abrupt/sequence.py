import re
import math

from abrupt.color import *

def binary_frequency_test(s):
  """
  Frequency Entropy Test
  As described in NIPS800-22 2.1
  """
  nb_1 = s.count("1")
  l = len(s)
  s_n = nb_1 + (-1) * (l - nb_1) 
  s_obs = abs(s_n) / float(math.sqrt(l))
  p_value = math.erfc(s_obs/math.sqrt(2))
  return p_value
 

def binary_run_test(s):
  """
  Run Test
  As described in NIPS800-22 2.3
  """
  nb_1 = s.count("1")
  l = len(s)
  pi = float(nb_1) / float(l)
  c = 0
  for k in range(len(s)-1):
    if s[k] != s[k+1]: c += 1
  v_obs = c
  num = abs(v_obs - 2*l*pi*(1-pi))
  den = 2*math.sqrt(2*l)*pi*(1-pi)
  p_value = math.erfc(num/den)
  return p_value

def char_size(s):
  return len(set(list(s)))

def char_frequency(s):
  d = set(list(s))
  n = len(s)
  e = 0
  for c in d:
    p = s.count(c) / float(n)
    e -= p * math.log(p, 2)   
  return e

 
def test_bin():
  c = [l[:-2] for l in open("tokens.txt").readlines()]
  d = [[str(bin(ord(q))[2:]).zfill(8) for q in o] for o in c] 
  ds = ["".join(x) for x in d]
  if len(set([len(q) for q in ds])) != 1:
    raise Exception("Different length !")
  r = []
  for k in range(len(ds[0])):
    s = "".join([ds[u][k] for u in range(len(ds))])
    r.append(frequency_test(s))
  
  s = ""
  for i, k in enumerate(r):
    if k<0.01:
      s += error("X")
    else: 
      b = "".join([ds[u][i] for u in range(len(ds))])
      p_v = run_test(b)
      if p_v < 0.01:
        s+= warning("?")
      else:
        s+= success("?")
    if i % 8 == 7:
      s+=" "
  print s
  print c[0]
  print c[1]

def test_char():
  c = [l[:-2] for l in open("tokens.txt").readlines()]
  p = 1
  cs = []
  cf = []
  for k in range(len(c[0])):
    s = "".join([c[u][k] for u in range(len(c))])
    p *= char_size(s)
    cs.append(char_size(s))
    cf.append(char_frequency(s))
  print "Combinaison:", p
  tcs = "".join([ success("?") if i > 4 else error("!") for i in cs])
  print "Alphabet length\t\t", tcs
  tcf = "".join([ success("?") if i > 4 else error("!") for i in cf])
  print "Entropy\t\t\t", tcf
  print c[:3]

test_char()
test_bin()
from IPython.Shell import IPShellEmbed
IPShellEmbed()()
