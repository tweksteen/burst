abrupt.injection - Request generator
====================================

.. module:: injection

The injection module provides two functions to "inject" a request (i.e.,
generate a :class:`RequestSet` from a Request using a list of payloads):

.. function:: inject(request, **kwds, [pre_func=e])
  
  aliased `i`
  
  For each keyword, this function will try to find the key in the request
  at the following locations:

    * URL parameters
    * Cookies
    * Content for a POST or PUT request

  Then, each value will be injected at the parameter location and a set
  of request returned. The values could be either a list of payload
  (e.g., id=[1,2,3]) or a key of the global dictionnary :data:`payloads`
  (e.g., name="default").

  Some examples::

    In [1]: print r
    GET /issues.html?issue=59&id=5 HTTP/1.1
    Host: www.phrack.com
    Cookie: PHPSESSID=4592a21fc9fd6b1e0afcc931eb74b28a

    In [2]: i(r, id="default")  
    Out[2]: {unknown:9 | www.phrack.com}

    In [3]: i(r, PHPSESSID=["1234","0000","31337-abcd"])
    Out[3]: {unknown:3 | www.phrack.com}    

    In [4]: i(r, issue="sqli")
    Out[4]: {unknown:106 | www.phrack.com}    


  The *pre_func* parameter is a function to apply to each payload before
  being injected. By default, it urlencode the payload.
  
.. function:: inject_at(request, offset, payload, [pre_func=e])
  
  aliased i_at

  This function inject the request at a specific offset, between
  two offset position or instead a token. 
  If *offset* is an integer, the payload will be inserted
  at this position. If *offset* is a range (e.g., (23,29)) this range will
  be erased with the payload. If *offset* is a string, it will be replaced
  by the payloads. In the latter scenario, if the string is not found or
  if more than one occurrence exists, an exception will be raised.

Once the RequestSet has been generated, you can execute it. The payloads
are available in a global dictionnary:

.. data:: payloads

  Dictionnary containing all the payloads. Each value is a list of
  string. When started, Abrupt load all the files under the directory
  "payloads" and create the corresponding key.

  By default, it contains:
    * default, a minimal list of standard payload, targetting classic web
      app vulnerabilities.
    * full, a larger list of standard payload.
    * sqli, targetting SQL injection. 

Some handy functions are also defined:

.. function:: e(x)

  urlquote(x)

.. function:: d(x)

  urlunquote(x)

