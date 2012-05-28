

Web Application Testing Framework. 
BSD Licensed. Based on Python 2.7.

Quick start
===========
::

  $ git clone git://github.com/securusglobal/abrupt.git
  $ cd abrupt
  $ export PYTHONPATH=$PWD
  $ ./bin/abrupt
  Generating SSL certificate...
  CA certificate : ~/.abrupt/ca.pem
  Abrupt 0.5
  >>>
  
.. note:: The first time you start Abrupt, it will generate a CA certificate.
  This is useful to avoid the exception creation whenever you reach a HTTPS
  site with the proxy enabled. You can install this certificate in your
  browser.

Abrupt tries to make all day-to-day actions as fast as possible. Most of the
core functions have an alias (first letter). It is possible to retrieve the
list of aliases in the :doc:`cheatsheet <cheatsheet>`.

Proxy
-----

To start, let's grab some HTTP requests. To do so, use the :func:`~proxy.proxy` 
function or its alias `p`. It will start a new proxy server on the port 8080. 
This server will intercept every HTTP(S) request and prompt for directions::

  >>> p()
  Running on port 8080
  Ctrl-C to interrupt the proxy...

You can now configure your browser to use http://localhost:8080 as your proxy.
All the requests will be captured by Abrupt and displayed::

  [1] <GET www.phrack.org /> ? 

In this case, a GET request targeted at www.phrack.org arrived. (The number 
at the beggining of each line represents the thread which is processing the 
request). You can now decide what to do:
 
  * (v)iew - print the full request
  * (h)eaders - print the headers
  * (e)dit - manually edit the request in your text editor
  * (d)rop - drop the request
  * (f)orward - forward the request
  * (c)ontinue - forward this request and the followings
  * (n)ext - put this request on the side and process another one

Forward is the default action if none is passed. Once a request has been made,
you can see the response::

  [1] <GET www.phrack.org /> ? f
  [1] <200 7468 text/html gzip>

The response status, length, content-type and flag are displayed. Once you're 
done with your requests, use Ctrl-C to exit. The proxy function returns all 
the completed requests and associated responses in a 
:class:`~http.RequestSet` object::

  Waiting for the threads to stop
  {200:1 | www.phrack.org}
  >>> requests = _
  >>> print requests
  Method Path Query Status Length 
  GET    /          200    7468

  >>> requests[0]
  <GET www.phrack.org />

.. note:: Inside the Python interpreter, the underscore variable ("_") holds 
   the result of the previous command.

The proxy comes with a powerful rules system to automatically process some 
requests according to user-defined criteria. For instance::

  >>> p(rules=((lambda x: x.hostname != "www.phrack.org", "d"),) )

will automatically drop any request which is not targeting www.phrack.org.
If no rule is provided, it will forward image files (.png, .jpg, .jpeg, 
.ico, .gif) without prompting the user. To see these images, you can increase 
the verbosity level::

  >>> p(verbose=1)

Or disable the default rules::

  >>> p(rules=None)

To learn more about rules, how to make your own and how to configure the 
proxy, see :func:`~proxy.proxy`. 

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

:class:`~http.Request` objects have numerous attributes: hostname, port,
headers, path, query, url, content, etc. You can edit the request through your
editor (default is vim) to create a new request::

  >>> new_r = r.edit()

The request can then be executed and the new response displayed::

  >>> new_r()
  >>> new_r.response
  <200 7468 text/html gzip>

For interactive edition, see the :meth:`~http.Request.play` method. 
:class:`~http.Response` objects have the attributes: status, reason, headers, 
content, raw_content, etc. You can use the :meth:`~http.Response.preview` 
method to open a static dump of the response in your browser and the 
:meth:`~http.Response.view` method to view the source in your text editor.

Abrupt also includes a :func:`~http.create` function (aliased `c`) to 
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
  

RequestSet
----------

A :class:`~http.RequestSet` is a set of requests. Usually, you'll have one 
from the :func:`~proxy.proxy` method. You can add more requests from another
capture session::

  >>> p()
  Ctrl-C to interrupt the proxy...
  <GET www.cryptome.org /> ? f
  <200 64184 text/html> ? f
  Waiting for the threads to stop
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

  >>> print r
  GET /issues.html?issue=66 HTTP/1.1
  Host: www.phrack.org

  >>> batch = i(r, to="issue", payload="sqli")
  >>> batch
  {unknown:106 | phrack.org}

In this case, a :class:`~http.RequestSet` of 106 requests has been generated. 
`inject` look up for the `to` parameter in the query string, the cookies and 
the POST data. Then, it generates new requests where the value of this 
parameter is replaced by each value of the corresponding payload list. The 
possible values for the payload list name are the keys of the 
:data:`~injection.payloads` global dictionary, and Abrupt comes with some 
default ones::

  >>> payloads.keys()
  ['xss', 'sqli', 'default', 'cmd', 'misc', 'printable', 'email', 'dir']

You can add your own payload list to your Abrupt or also use a list generated 
on the fly. Read more about this function in the :mod:`injection` module.
Once the requests have been generated, you can send them::

  >>> batch()
  Running 106 requests...done.
  >>> batch
  {200:106 | phrack.org}
  >>> print batch
  Id  Method Path         Payload          Query                           Status Length Time   
  0   GET    /issues.html '                issue=%27                       200    11026  0.5913 
  1   GET    /issues.html ' --             issue=%27+--+                   200    11026  0.1318 
  2   GET    /issues.html a' or 1=1 --     issue=a%27+or+1%3D1+--+         200    11026  0.1064 
  3   GET    /issues.html "a"" or 1=1 -- " issue=%22a%22%22+or+1%3D1+-%22… 200    11026  0.1281 
  4   GET    /issues.html  or a = a        issue=+or+a+%3D+a               200    11026  0.0973 
  5   GET    /issues.html a' or 'a' = 'a   issue=a%27+or+%27a%27+%3D+%27a  200    11026  0.0998 
  ...

This is the end of the quick start. But it only shows the basic functionalities
of Abrupt. To discover more about it, just follow one of these links:

Reference
=========

.. toctree:: 
  :maxdepth: 2

  http
  proxy
  injection
  session
  configuration
  faq
  cheatsheet

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

