Welcome to Abrupt's documentation!
==================================

Abrupt is a web app penetration framework. You can use it as a stand-alone 
application or use the provided library to quickly forge your own tool.

Description
===========

Abrupt integrate all the tools you may need during a penetration testing on a 
web application like a proxy, a request repeater or a fuzzer. This tool is
largely inspired by the best python tools: scapy for the interactive prompt,
django model's query for extracting and filtering request, etc. If you are a 
python adept, welcome home! 

Of course, Abrupt is open source. Released under the BSD license. For more
information, see COPYING.

Requirements
============

Abrupt is based on python>=2.6. It is not python3 compatible for now. Also to
have a real experience with it, we highly recommend you to install IPython. By
default, Abrupt is compatible with HTTPS. For an easier use, we recommend to
have openssl installed and the openssl command available in the path.

Abrupt adopt the UNIX philosophy, so set you EDITOR and BROWSER environment
variables buddy.

Quickstart
==========

To have a quick view of the power of Abrupt, we have made this quickstart which
will show you the main functionalities. To start, clone the git repository::

  $ git clone git://github.com/SecurusGlobal/Abrupt.git abrupt
  $ cd abrupt
  $ python bin/abrupt

  Generating SSL certificate...
  CA certificate : /home/tweksteen/.abrupt/ca.pem
  In [1]: 
  
The first time you start Abrupt, it will generate a CA certificate. This is 
useful to avoid the exception creation whenever you reach a HTTPS site with the
proxy enabled. You can install this certificate in your browser. However, no 
check is performed by Abrupt on the server side regarding ssl.

Proxy
-----

To start, let's grab some HTTP request. To do so, use the *p* function. It 
starts a new proxy server on port 8080. This server will catch every HTTP(S)
request and prompt the user for directions::

  In [1]: p()
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
all the completed requests and associated responses in a RequestSet object::

  KeyboardInterrupt
  1 request intercepted
  Out[1]: {200:1 | phrack.org}

  In [2]: requests = _

  In [3]: print requests
  Path Query Status Length 
  /    -     200    5419
  
  In [4]: requests[0]
  Out[4]: <GET www.phrack.org />

Not all the requests are shown. By default, a filter silently forward all the 
image files (.png, .jpg, .jpeg, .ico, .gif). To see them, you can use::

  In [1]: p(filter=None)

Some other functions exists : *w*, just display the requests, doesn't provided
any interaction. *p1* and *w1*, working as *p* and *w* but only intercept one 
request.

Request and Response
--------------------

Abrupt have its own representation of HTTP request and response based on 
httplib::
  
  In [5]: r = requests[0]
  In [6]: print r
  GET / HTTP/1.1
  Accept-Language: en-us,en;q=0.5
  Accept-Encoding: gzip,deflate
  Keep-Alive: 115
  Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
  User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.15)
  Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
  Host: www.phrack.org
  Proxy-Connection: keep-alive

Request objects have numerous attributes: hostname, port, headers, path, 
query, url, content. You can create a new request based on another with::

  In [7]: new_r = r.edit()
  
And execute the new request::

  In [8]: new_r()

  In [9]: new_r.response
  Out[9]: <200 Gzip 5419>
  
Response objects have the attributes: status, reason, headers, content, 
readable_content. You can use the *preview* method to open a static dump of
the response in your favorite $BROWSER.

RequestSet
----------

A RequestSet is just a set of requests. Usually, you'll have one from a proxy 
method. You can add more requests from another capture session::

  In [10]: w()
  Ctrl-C to interrupt the proxy...
  <GET www.cryptome.org />
  <200 49380>
  1 request intercepted

  In [11]: requests += _
  
  In [12]: requests
  Out[12]: {200:2 | phrack.org, www.cryptome.org}
  

You can filter the request by any request attributes::

  In [13]: requests.filter(hostname="phrack.org")
  Out[13]: {200:1 | phrack.org}

Injection
---------

From one request, it is possible to generate a batch of request where one or 
many parameters change using the *i* function ::

  In [14]: r
  Out[14]: <GET phrack.org /issues.html>

  In [15]: batch = i(r, issue="default")
  
  In [16]: r
  Out[16]: {unknown:5 | phrack.org}

In this case, a RequestSet of 5 requests has been generated. *i* lookup for
arguments in the query string, the cookie and the post data. You should give 
the name and the list of payloads name as arguments. The list of payloads can
be found in the payloads/ directory. You can also get the keys of the payloads
global variables.Before being injected, each payload is pass through the
*pre_func* function which is, by default, *e*. 

Once the requests have been generated, you can send them::

  In [17]: batch()
  ...
  
  In [18]: batch
  Out[18]: {200:5 | phrack.org}

  In [19]: print batch
  Path         Query                                  Status Length 
  /issues.html issue=%2527                            200    2390   
  /issues.html issue=%2527%2B--                       200    2390   
  /issues.html issue=%253E%253Cscript%253Ealert%25... 200    2390   
  /issues.html issue=-1                               200    2390   
  /issues.html issue=2-1                              200    1948 

If you want to inject all the undefined parameter with a default value, 
*default_value* can be set. A shortcut for *i(default_value="default")* is *f*. 

Reference
=========

.. toctree:: 
  :maxdepth: 2

  http
  proxy
  cheatsheet


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

