abrupt.injection - Request generator
====================================

.. module:: injection

.. function:: inject(request, to=None, at=None, payload="default")
  
  aliased `i`
  
  This function will create a RequestSet from a Request where a part
  of the latter is replaced with some payload. There is two way to use
  this function, either to inject the value of a parameter or to inject
  at a specific location.

  When used with the `to` parameter, Abrupt will look up the value
  in the query string, the request content and the cookies. It will
  then replace the value of the parameter with the payloads. If no
  valid injection point is found, an error is raised.

  When used with the `at` parameter, Abrupt will look up the string in the 
  whole request text and replace it with the payloads. If no valid injection
  point is found, an error is raised. If the string is found more than
  once, the function will suggest to provide the 'choice' integer keyword.

  `payload` could either be a list of the payloads to inject or a key
  of the global dictionary :data:`payloads`.

  Some examples::

    >>> print r
    GET /issues.html?issue=59&id=5 HTTP/1.1
    Host: www.phrack.com
    Cookie: PHPSESSID=4592a21fc9fd6b1e0afcc931eb74b28a

    >>> i(r, to="id")  
    {unknown:9 | www.phrack.com}

    >>> i(r, to="PHPSESSID", payload=["1234","0000","31337-abcd"])
    {unknown:3 | www.phrack.com}    

    >>> i(r, to="issue", payload="sqli")
    {unknown:106 | www.phrack.com}    

    >>> i(r, at="4592a21fc9fd6b1e0afcc931eb74b28a", payload="sqli")
    {unknown:106 | www.phrack.com}    

  The `pre_func` parameter is a function to apply to each payload before
  being injected. By default, it urlencode the payload.
  
.. data:: payloads

  Dictionary containing all the payloads. Each value is a list of
  string. When started, Abrupt load all the files under the directory
  "payloads" and create the corresponding key.

  By default, it contains:
    * xss, a small list of xss payload.
    * sqli, targeting SQL injection. 
    * cmd, command execution.
    * default, the compilation of all the above payloads.

.. function:: encode(x)

  aliased `e`  

  urlquote(x)

.. function:: decode(x)

  aliased `d` 

  urlunquote(x)

