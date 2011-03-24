Abrupt's documentation
======================

Abrupt is a web app penetration framework. You can use it as a stand-alone 
application or use the provided library to make your own tool.

Quickstart
----------

You can start using abrupt right now, just by cloning the git repository::

  $ git clone ssh://opium/home/tweek/abrupt.git
  $ cd abrupt
  $ python abrupt.py
  ~~--[ Abrupt 20110318 ]--~~

  In [1]: 

.. note::
  
  You **need** python >=2.7 to run it. Also it's  highly recommended but not 
  mandatory to install IPython for a better experience.

Proxy
^^^^^

To start, let's grab some HTTP request. To do so, use the *p* function.
It starts a new proxy server on port 8080. This server will catch every HTTP(S)
request and prompt the user for directions::

  In [1]: p()
  Ctrl-C to interrupt the proxy...

You can now configure your browser to use http://localhost:8080 as your proxy.
All the request will be captured by Abrupt::

  <GET www.phrack.org /> ? 

For each request, you can decide what to do:
 
  * (v)iew - print the full request
  * (e)dit - manually edit the request in your favorite $EDITOR
  * (d)rop - drop the request
  * (f)orward - Forward the request
  * (c)ontinue - Forward this request and the following

Forward is the default action if none is passed. 
Once a request has been made, you can see the response status and length::

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

Some other functions exists : *w*, just display the requests, doesn't provided
any interaction. *p1* and *w1*, working as *p* and *w* but only intercept one 
request.

Request and Response
^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^

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
^^^^^^^^^

From one request, it is possible to generate a batch of request where one or 
many parameters change with the *i* function ::

  In [14]: r
  Out[14]: <GET phrack.org /issues.html>

  In [15]: attack = i(r, issue="default")
  
  In [16]: r
  Out[16]: {unknown:5 | phrack.org}

In this case, a RequestSet of 5 requests has been generated. *i* lookup for
arguments in the query string, the cookie and the post data. You should give 
the name and the list of payloads name as arguments. Before being injected,
each payload is pass through the *pre_func* function which is, by default, *e*. 

Once the requests have been generated, you can send them::

  In [17]: attack()
  ...
  
  In [18]: attack
  Out[18]: {200:5 | phrack.org}

  In [19]: print attack
  Path         Query                                                            Status Length 
  /issues.html issue=%2527                                                      200    2390   
  /issues.html issue=%2527%2B--                                                 200    2390   
  /issues.html issue=%253E%253Cscript%253Ealert%25281%2529%253C%252Fscript%253E 200    2390   
  /issues.html issue=-1                                                         200    2390   
  /issues.html issue=2-1                                                        200    1948 

If you want to inject all the undefined parameter with a default value, *default_value*
can be set. A shortcut for *i(default_value="default")* is *f*. 

Sequence Analyser
^^^^^^^^^^^^^^^^^

TBA


CheatSheet
----------

* (p)roxy   - run a proxy, default on port 8080
* (w)atch   - run a passive proxy
* (i)nject  - inject a Request
* (f)uzz    - inject all params with default payload
* (e)ncode  - urlencode a string
* (d)ecode  - urldecode a string

