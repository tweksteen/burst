#!/usr/bin/python
#
# abrupt.target
# tw@securusglobal.com
#

from http import Request, Response

class Target():

  def __init__(self):
    self.scope = []

  def spider(self):
    pass


def generate_scope(requests):
  t = Target()
  ignored = []
  for r in requests:
    print r.hostname, r.url


