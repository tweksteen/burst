

Web Application Penetration Framework. 
BSD Licensed. Based on Python>=2.6.

Quickstart
==========
::

  $ git clone git://github.com/SecurusGlobal/Abrupt.git abrupt
  $ cd abrupt
  $ sudo python setup.py install
  $ abrupt
  Generating SSL certificate...
  CA certificate : /home/tweksteen/.abrupt/ca.pem
  Abrupt v0.1
  >>>
  
The first time you start Abrupt, it will generate a CA certificate. This is 
useful to avoid the exception creation whenever you reach a HTTPS site with the
proxy enabled. You can install this certificate in your browser. However, no 
check is performed by Abrupt on the server side regarding ssl.

Proxy
-----

To start, let's grab some HTTP requests. To do so, use the proxy or :func:`p` function. It 
starts a new proxy server on port 8080. This server will catch every HTTP(S)
request and prompt the user for directions::

  >>> p()
  Running on port 8080
  Ctrl-C to interrupt the proxy...

You can now configure your browser to use http://localhost:8080 as your proxy.
All the requests will be captured by Abrupt::

  <GET www.phrack.org /> ? 

For each request, you can decide what to do:
 
  * (v)iew - print the full request
  * (e)dit - manually edit the request in your favorite $EDITOR
  * (d)rop - drop the request
  * (f)orward - Forward the request
  * (c)ontinue - Forward this request and the following

Forward is the default action if none is passed. Once a request has been made,
you can see the response status and length::

  <GET www.phrack.org /> ? f
  <200 Gzip 5419>

Once you're done with your requests, use Ctrl-C to exit. This function return
all the completed requests and associated responses in a :class:`RequestSet` object::

  1 request intercepted
  {200:1 | www.phrack.org}
  >>> requests = _
  >>> print requests
  Method Path Query Status Length 
  GET    /          200    5419   

  >>> requests[0]
  <GET www.phrack.org />

Not all the requests are shown. By default, a filter silently forward all the 
image files (.png, .jpg, .jpeg, .ico, .gif). To see them, you can use::

  >>> p(filter=None)

Some other functions exists : *w*, just display the requests, doesn't provided
any interaction. *p1* and *w1*, working as *p* and *w* but only intercept one 
request.

Request and Response
--------------------

Abrupt have its own representation of HTTP request and response based on 
httplib::
  
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

:class:`Request` objects have numerous attributes: hostname, port, headers, 
path, query, url, content. You can edit the request through your EDITOR 
(default is vim) to create a new request::

  >>> new_r = r.edit()
  
And execute the new request::

  >>> new_r()
  >>> new_r.response
  <200 Gzip 5419>

For more fun, try the :meth:`Request.play`. It will start your editor (which should 
be Vim) and display the request and the response in two different windows.
Every time you save the request file, the request is made to the server and
the response displayed. 
  
:class:`Response` objects have the attributes: status, reason, headers, content, 
readable_content. You can use the *preview* method to open a static dump of
the response in your favorite BROWSER and the *view* method to view the source
in your favorite EDITOR.

RequestSet
----------

A :class:`RequestSet` is just a set of requests. Usually, you'll have one from a proxy 
method. You can add more requests from another capture session::

  >>> w()
  Ctrl-C to interrupt the proxy...
  <GET www.cryptome.org />
  <200 49380>
  1 request intercepted

  >>> requests += _
  >>> requests
  {200:2 | phrack.org, www.cryptome.org}
  

You can filter the request by any request attributes::

  >>> requests.filter(hostname="phrack.org")
  {200:1 | phrack.org}

Injection
---------

From one request, it is possible to generate a batch of request where one or 
many parameters change using the injection or :func:`i` function ::

  >>> r
  <GET phrack.org /issues.html>

  >>> batch = i(r, issue="default")
  
  >>> batch
  {unknown:9 | phrack.org}

In this case, a RequestSet of 9 requests has been generated. *i* lookup for
arguments in the query string, the cookie and the post data. You should give 
the name and the list of payloads name as arguments. The list of payloads can
be found in the payloads/ directory. You can also get the keys of the :data:`payloads`
global variable. Before being injected, each payload is pass through the
*pre_func* function which is, by default, :func:`e`. 

Once the requests have been generated, you can send them::

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

Reference
=========

.. toctree:: 
  :maxdepth: 2

  http
  proxy
  injection
  real-world
  cheatsheet

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

