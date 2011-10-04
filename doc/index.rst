

Web Application Penetration Framework. 
BSD Licensed. Based on Python>=2.6.

Quickstart
==========
::

  $ sudo pip install abrupt
  $ abrupt
  Generating SSL certificate...
  CA certificate : /home/tweksteen/.abrupt/ca.pem
  Abrupt 0.2
  >>>
  
The first time you start Abrupt, it will generate a CA certificate. This is 
useful to avoid the exception creation whenever you reach a HTTPS site with the
proxy enabled. You can install this certificate in your browser. However, no 
check is performed by Abrupt on the server side regarding ssl.

Proxy
-----

To start, let's grab some HTTP requests. To do so, use the :func:`~proxy.proxy` 
function or its alias `p`. It will start a new proxy server on port 8080. This 
server will catch every HTTP(S) request and prompt the user for directions::

  >>> p()
  Running on port 8080
  Ctrl-C to interrupt the proxy...

You can now configure your browser to use http://localhost:8080 as your proxy.
All the requests will be captured by Abrupt::

  <GET www.phrack.org /> ? 

For each request, you can decide what to do:
 
  * (v)iew - print the full request
  * (e)dit - manually edit the request in your text editor
  * (d)rop - drop the request
  * (f)orward - Forward the request
  * (c)ontinue - Forward this request and the followings

Forward is the default action if none is passed. Once a request has been made,
you can see the response status and length::

  <GET www.phrack.org /> ? f
  <200 Gzip 5419>

Once you're done with your requests, use Ctrl-C to exit. This function return
all the completed requests and associated responses in a 
:class:`~http.RequestSet` object::

  1 request intercepted
  {200:1 | www.phrack.org}
  >>> requests = _
  >>> print requests
  Method Path Query Status Length 
  GET    /          200    5419   

  >>> requests[0]
  <GET www.phrack.org />

The proxy comes with a powerful rules system to automatically process some 
requests according to used-defined criteria. For instance::

  >>> p(rules=((lambda x: x.hostname != "www.phrack.org", "d"),) )

will automatically drop any request which is not targeting "www.phrack.org".
If no rule is provided, it will forward image files (.png, .jpg, .jpeg, 
.ico, .gif) without prompting the user. To see these images, you can increase 
the verbosity level::

  >>> p(verbose=1)

To learn more about rules and how to make your own, see :func:`~proxy.proxy`. 

Request and Response
--------------------

Abrupt have its own representation of HTTP request and response::
  
  >>> r = requests[0]
  >>> print r
  GET / HTTP/1.1
  Accept-Language: en-us,en;q=0.5
  Accept-Encoding: gzip,deflate
  Keep-Alive: 115
  Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
  User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.15)
  Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
  Host: www.phrack.org
  Proxy-Connection: keep-alive

:class:`~http.Request` objects have numerous attributes: hostname, port, headers, 
path, query, url, content, etc. You can edit the request through your editor
(default is vim) to create a new request::

  >>> new_r = r.edit()
  
And execute the new request::

  >>> new_r()
  >>> new_r.response
  <200 Gzip 5419>

For interactive edition, see the :meth:`~http.Request.play` method. Amusement 
garanti! Abrupt also include a :func:`~http.create` function (aliased `c`) to 
quickly forge a Request based on a URL::

  >>> c("http://www.phrack.org")
  <GET www.phrack.org />
  >>> print c
  GET / HTTP/1.1
  Host: www.phrack.org
  User-Agent: Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 0.9; en-US)
  Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
  Accept-Language: en;q=0.5,fr;q=0.2
  Accept-Encoding: gzip, deflate
  Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
  
:class:`~http.Response` objects have the attributes: status, reason, headers, 
content, raw_content, etc. You can use the :meth:`~http.Response.preview` 
method to open a static dump of the response in your browser and the 
:meth:`~http.Response.view` method to view the source in your text editor.

RequestSet
----------

A :class:`~http.RequestSet` is a set of requests. Usually, you'll have one 
from the :func:`~proxy.proxy` method. You can add more requests from another
capture session::

  >>> p()
  Ctrl-C to interrupt the proxy...
  <GET www.cryptome.org />
  <200 49380>
  1 request intercepted
  >>> requests += _
  >>> requests
  {200:2 | phrack.org, www.cryptome.org}
  

You can filter the requests by any request attribute using the 
:meth:`~http.RequestSet.filter` method::

  >>> requests.filter(lambda x: x.hostname == "phrack.org")
  {200:1 | phrack.org}

Injection
---------

From one request, it is possible to generate a batch of requests where one or 
many parameters vary using the :func:`~injection.inject` function (aliased `i`)::

  >>> r
  <GET phrack.org /issues.html>
  >>> batch = i(r, issue="default")
  >>> batch
  {unknown:9 | phrack.org}

In this case, a :class:`~http.RequestSet` of 9 requests has been generated. 
`inject` lookup for the arguments in the query string, the cookies and the POST 
data. Then, it generates a new request where the value of this argument is 
replaced by each value of the corresponding payload list. The possible values 
for the payload list name are the keys of the :data:`~injection.payloads` 
global dictionnary, and Abrupt comes with some default ones::

  >>> payloads.keys()
  ['digits', 'lowercase', 'full', 'default', 'uppercase', 'sqli', 'hexdigits', 'printable']

You can add your own payload list to your Abrupt or also use a list generated 
on the fly. Once the requests have been generated, you can send them::

  >>> batch()
  Running 9 requests...done.
  >>> batch
  {200:9 | phrack.org}
  >>> print batch
  Id Method Path         Query                          Status Length 
  0  GET    /issues.html issue=%27                      200    2390   
  1  GET    /issues.html issue=abrupt_xss__             200    2390   
  2  GET    /issues.html issue=%3C%2Fabrupt%3E          200    2390   
  3  GET    /issues.html issue=%29%29%29%29%29%29%29... 200    2390   
  4  GET    /issues.html issue=..%2F..%2F..%2F..%2F.... 200    2390   
  5  GET    /issues.html issue=..%5C..%5C..%5C..%5C.... 200    2390   
  6  GET    /issues.html issue=%7C%7C+ping+-i+60+127... 200    2390   
  7  GET    /issues.html issue=%3Bid                    200    2390   
  8  GET    /issues.html issue=%3Becho+123456           200    2390

Read more about this function in the :mod:`injection` module.

Reference
=========

.. toctree:: 
  :maxdepth: 2

  http
  proxy
  injection
  session
  configuration
  real-world
  cheatsheet

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

