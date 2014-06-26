import os
import re
import shlex
import random
import subprocess

from burst.conf import CERT_DIR
from burst.exception import CertError

RE_DOMAIN = re.compile(r'^\[?[0-9A-Za-z*-.:]*\]?$')

def extract_name(cert):
  if "subject" in cert and len(cert["subject"]) >= 0:
    s = cert["subject"]
    for x in s:
      if x[0][0] == "commonName":
        return x[0][1]

def generate_serial():
  return hex(random.getrandbits(64))[:-1]

def get_key_file():
  return os.path.join(CERT_DIR, "key.pem")

def generate_ssl_cert(domain):
  if not RE_DOMAIN.match(domain):
    raise CertError("Domain name contains unexpected characters")
  domain_cert = os.path.join(CERT_DIR, "sites", domain + ".pem")
  gen_req_cmd = "openssl req -new -out {0}/req{1}.pem -key {0}/key.pem " \
                "-subj '/O=Burst/CN={1}'".format(CERT_DIR, domain)
  sign_req_cmd = "openssl x509 -req -in {0}/req{3}.pem -CA {0}/ca.pem -CAkey" \
                 " {0}/key.pem -out {1} -set_serial {2}" \
                 "".format(CERT_DIR, domain_cert, generate_serial(), domain)
  if not os.path.exists(domain_cert):
    p_req = subprocess.Popen(shlex.split(gen_req_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ss, se = p_req.communicate()
    if p_req.returncode:
      raise CertError("Error while creating the certificate request:" + se)
    p_sign = subprocess.Popen(shlex.split(sign_req_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ss, se = p_sign.communicate()
    if p_sign.returncode:
      raise CertError("Error while signing the certificate:" + se)
    os.remove(os.path.join(CERT_DIR, "req{0}.pem".format(domain)))
  return domain_cert

def generate_ca_cert():
  gen_key_cmd = "openssl genrsa -out {0}/key.pem 2048".format(CERT_DIR)
  gen_ca_cert_cmd = "openssl req -new -x509 -extensions v3_ca -days 3653 " + \
                    "-subj '/O=Burst/CN=Burst Proxy' " + \
                    "-out {0}/ca.pem -key {0}/key.pem".format(CERT_DIR)
  p_key = subprocess.Popen(shlex.split(gen_key_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ss, se = p_key.communicate()
  if p_key.returncode:
    raise CertError("Error while creating the key:" + se)
  p_cert = subprocess.Popen(shlex.split(gen_ca_cert_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ss, se = p_cert.communicate()
  if p_cert.returncode:
    raise CertError("Error while creating the certificate:" + se)
  print "CA certificate: " + CERT_DIR + "/ca.pem"
