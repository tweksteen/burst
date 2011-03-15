Abrupt's documentation
======================

Abrupt is a web app penetration framework. You can use it as a stand-alone 
application or use the provided library at your own convenience.


Quickstart
----------

You can start using abrupt right now, just by starting the interpreter::

  $ python abrupt.py
  ~~--[ Abrupt 0.1 ]--~~

  In [1]: 

.. note::
  
  It's  highly recommended but not mandatory to install IPython for a better 
  experience with Abrupt.

Proxy
^^^^^

To start, let's grab some HTTP request. To do so, use the *p* function.
It starts a new proxy server on port 8080. This server will catch every HTTP(S)
request and prompt the user for directions::

  In [1]: p()
  Ctrl-C to interrupt the proxy...

You can now configure your browser to use http://localhost:8080 as your proxy.
All the request will be captured by Abrupt::

  <GET www.phrack.com /> ? 

For each request, you can decide what to do:
 
  * (v)iew - print the full request
  * (e)dit - manually edit the request in your favorite $EDITOR
  * (d)rop - drop the request
  * (f)orward - Forward the request

Forward is the default action if none is passed. 
Once a request has been made, you can see the response status and length::

  <GET www.phrack.com /> ? f
  <200 Gzip 5419>

Once you're done with your requests, use Ctrl-C to exit. This function returned
all the completed requests and associated responses. You can replay them, 
modify them or create an injection based on them::

  KeyboardInterrupt
  1 request intercepted
  Out[1]: [<GET www.phrack.com />]

  In [2]: requests = _
  
  In [3]: requests[0]
  Out[3]: <GET www.phrack.com /> 

Some other functions exists : *w*, just display the requests, doesn't provided
any interaction. *p1* and *w1*, working as *p* and *w* but only intercept
one request.

Request and Response
^^^^^^^^^^^^^^^^^^^^

Abrupt have its own representation of HTTP request and response::
  
  In [4]: r = requests[0]
  In [5]: print r
  GET / HTTP/1.1
  Accept-Language: en-us,en;q=0.5
  Accept-Encoding: gzip,deflate
  Keep-Alive: 115
  Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
  User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.15) Gecko/20110304 Firefox/3.6.15
  Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
  Host: www.phrack.com
  Proxy-Connection: keep-alive

Request objects have numerous attributes: hostname, port, headers, path, query, url, content.
You can create a new request based on another with::

  In [6]: new_r = r.edit()
  
And execute the new request::

  In [7]: new_r()

  In [8]: new_r.response
  Out[8]: <200 Gzip 5419>
  
If you want to filter some request in a list, you can use the static method *filter*::

  In [9]: from abrupt.http import Request

  In [10]: wiki_reqs = Request.filter(requests, hostname="en.wikipedia.org")


Injection
^^^^^^^^^

From one request, it is possible to generate a batch of request where one or many parameters
change::

  In [11]: r.inject(id=payload.all_injection)
  Out[11]: [ ... ]


Sequence Analyser
^^^^^^^^^^^^^^^^^

TBA






