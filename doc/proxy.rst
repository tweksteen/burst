abrupt.proxy - HTTP(S) Proxy
============================

To start a proxy, you can use the intercept method also known as p:

.. function:: p([port=8080, prompt=True, nb=-1, filter=re_filter_images, verbose=False])

   Start a new proxy server on port *port*. If *prompt* is True, directions will be
   asked for every request. *nb* requests will be intercepted at most. The argument
   *filter* should be a regular expression on the urls to filter. By default, images
   are filtered. If *verbose* is True, the whole request is displayed instead of a 
   summary.
 
   This function return a :class:`RequestSet` of all the successful :class:`Request` made.

