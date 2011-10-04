abrupt.http - HTTP base classes
===============================

.. module:: http

.. class:: Request(fp, [hostname=None, port=80, use_ssl=False]) 

  The Request class is the base of Abrupt. To create an instance, you have 
  two options: either use a socket or a string representing the whole request 
  into the constructor or use the :func:`~http.create` function. 
  The two methods __repr__ and __str__ have been defined to provide
  user friendly interaction inside the interpreter.

  .. attribute:: method 
    
    Contains the HTTP method of the request. For instance, "GET".

  .. attribute:: url
    
    A 6-tuple result, see http://docs.python.org/library/urlparse.html

  .. attribute:: http_version

    The HTTP version. For instance, "HTTP/1.1".

  .. attribute:: hostname

    The hostname of the server. For instance, "phrack.org".

  .. attribute:: port

    The port used to connect to the server. By default, 80.

  .. attribute:: use_ssl

    A boolean indicating if SSL is used. By default, False.

  .. attribute:: headers 

    List of pairs containing the headers.

  .. attribute:: path

    The path of the request. For instance, "/index.html". This attribute is 
    defined as read-only. To modify the path, use the :attr:`url` attribute.

  .. attribute:: query 
    
    The query. For instance, "issue=32&debug=false". This attribute is 
    read-only. To modify the query, use :attr:`url`.

  .. attribute:: cookies

    A python cookie, see http://docs.python.org/library/cookie.html. This 
    attribute is read-only, based on the :attr:`headers`.

  .. attribute:: response

    The associated response, once the request has been made to the server.
    For more information, see :class:`~http.Response`.

  .. method:: ()
    
    Do the request. Includes connect to the server, send the request,
    read the response, create the corresponding :class:`~http.Response` 
    object and add itself to the :data:`~http.history`.

  .. method:: follow()
  
    If the request's response is a HTTP redirection, calling this function
    will return a request following the redirection. This function is still
    considered as experimental, please code your own and share it.

  .. method:: _update_content_length()

    In case you change the body of the request.

  .. method:: copy() 

    Create a new request based on the current, without the response.

  .. method:: edit()

    Start your editor to edit the request, the new request is returned. 
    See the configuration parameter :attr:`~conf.Configuration.editor`.

  .. method:: play(options)

    Start your editor with two windows. Each time the request file is saved,
    the request is made to the server and the response updated. When the 
    editor terminates, the last valid request made is returned.
    By default, `options` is set to configure ``vim``.

  .. method:: extract(field)

    Extract a particular field of the request. See 
    :meth:`~http.RequestSet.extract`.

  .. method:: i()

    Shortcut for :func:`~injection.inject`.

  .. method:: i_at()

    Shortcut for :func:`~injection.inject_at`.

.. class:: Response(fd)
    
  You will never use directly the constructor of Response, instead use
  the Request attribute :attr:`~http.Request.response`.

  .. attribute:: status

    The status of the response. For instance, "404" or "200".

  .. attribute:: reason

    The reason. For instance, "Not Found".

  .. attribute:: http_version
  
    The version. For instance, "HTTP/1.1".

  .. attribute:: headers 

    List of couple containing the headers.

  .. attribute:: raw_content
  
    The content returned by the server. It could be compressed or chunked.
  
  .. attribute:: content

    Decoded content, as displayed by your browser. 

  .. attribute:: cookies

    A python cookie, see http://docs.python.org/library/cookie.html. This 
    attribute is read-only, based on the :attr:`headers`

  .. method:: raw()

    Return the full response including headers and raw_content.

  .. method:: preview()

    Start your browser on a static dump of the response.

  .. method:: view()
    
    Start your editor on the response.

  .. method:: extract(field)

    Extract information on the request. See :func:`~http.RequestSet.extract`

.. class:: RequestSet([reqs=None])

  RequestSet is just an easy way to group some :class:`~http.Request`. It 
  behave like a list. You can access element at a specific index 
  with the `[]` operator. `append`, `extend`, `pop`, `+` will behave as   
  expected. 

  .. method:: filter(predicate)
    
    Filter the RequestSet according to the supplied predicate. For 
    instance, to filter by hostname, you can use 
    ``rs.filter(lambda x: x.hostname == "phrack.org")``.
    To filter the requests which response's content matches a 
    regular expression:
    ``rs.filter(lambda x: re.search(r'Error', x.response.content))``
    
  .. method:: extract(arg, from_response=None)
    
    Returns a specific attribute for all the requests. For instance, 
    ``rs.extract("hostname")``. It will look up the argument in the request's
    attribute, URL paramaters, POST content, cookies, response attributes and
    response cookies, in this order. If only the response should be looked
    up, set `from_response` to `True`.

  .. method:: ()
  
    Make all the requests contained in the RequestSet only if they are 
    all using the same host and port. An exception is raised if it is 
    not the case.

  .. method:: cmp(i1, i2)
    
    Start your :attr:`~conf.Configuration.diff_editor` with the two
    requests at index `i1` and `i2`.

  .. method:: cmp_response(i1, i2)

    Start your :attr:`~conf.Configuration.diff_editor` with the two
    responses of the requests at index `i1` and `i2`.

.. function:: create(url)
  
  aliased `c`

  Create a :class:`~http.Request` based on a URL. For instance 
  ``c("http://www.phrack.org")``. Some headers are automatically added 
  to the request (User-Agent, Accept, Accept-Encoding, Accept-Language, 
  Accept-Charset).

.. function:: compare(r1, r2)

  aliased `cmp`

  Start your :attr:`~conf.Configuration.diff_editor` with the two requests
  or responses side by side.

.. data:: history

  History is a :class:`RequestSet` which contains all the requests made through 
  Abrupt. To turn it off, set :attr:`~conf.Configuration.history` to False.
