abrupt.http - HTTP base classes
===============================

.. class:: Request(fp, [hostname=None, port=80, use_ssl=False]) 

  The Request class is the base of Abrupt. To create an instance, you have 
  two options: either use a socket or a string representing the whole request 
  into the constructor or use the :fun:c function. 
  Once created, the Request object have the following attributes:

  .. attribute:: method 
    
    Contains the HTTP method of the request. For instance, "GET"

  .. attribute:: url
    
     A 6-tuple result, see http://docs.python.org/library/urlparse.html

  .. attribute:: http_version

     The HTTP version. For instance, "HTTP/1.1"

  .. attribute:: hostname

     The hostname of the server. For instance, "phrack.org"

  .. attribute:: port

     The port used to connect to the server. By default "80".

  .. attribute:: use_ssl

     A boolean indicating if SSL is used. By default, False

  .. attribute:: headers 

     List of couple containing the headers.

  .. attribute:: path

     The path of the request. For instance, "/index.html". This attribute is 
     defined as read-only. To modify the path, use the :attr:`url` attribute.

  .. attribute:: query 
    
    The query. For instance, "issue=32". This attribute is read-only. To modify
    the query, use :attr:`url`.

  .. attribute:: cookies

     A python cookie, see http://docs.python.org/library/cookie.html. This 
     attribute is read-only, based on the :attr:`headers`

  .. attribute:: response

     The associated response, once the request has been made to the server.
     For more information, see :class:`Response`

  The Request class define both __repr__ and __str__ for a different behavior
  when called using the interpreter. The other methods available are:

  .. method:: __call__()
    
     make the request

  .. method:: _update_content_length()

    in case you change the body of the request

  .. method:: copy() 

    create a new request based on the current, without the response

  .. method:: edit()

    start your favorite $EDITOR to edit the request, the new request is returned

  .. method:: extract(field)

     extract information on the request. See RequestSet.extract

.. function:: c(url)

  Create a Request based on a URL. For instance `c("http://www.phrack.org")`

.. class:: Response(fd)
    
  You will never use directly the constructor of Response, instead reference
  a response object as a request results.

  .. attribute:: status

  .. attribute:: reason

  .. attribute:: http_version




  
