abrupt.proxy - HTTP(S) Proxy
============================

.. module:: proxy

To start a proxy, you can use the intercept method also known as p:

.. function:: proxy(port=conf.port, nb=-1, rules=None, default_action='a', alerter=None, persistent=False, verbose=False])
  
  aliased `p`

  Start a new proxy server on port `port`. At most, `nb` requests will be 
  served. If `nb` is `-1`, the proxy will process requests until stopped.
  
  `rules` is a list of pair where the first element is a predicate and the
  second a rule to execute when the predicate is true. If no rules applies,
  the `default_action` will be executed.
  For instance:
    
    >>> p(rules = ((lambda x: x.hostname != "www.lemonde.fr", "d"),))

  will (d)rop any requests which hostname is not equal to "www.lemonde.fr".

    >>> p(rules = ((lambda x: x.method == "GET", "f"), (lambda x: x.method == "POST", "d")))

  will drop any POST requests, forward GET requests and ask the user for any other method.

  `alerter` should be an object from derived from :class:`alert.Generic`. It will be called
  after each requests to look up trivial outstanding responses. If `None` is supplied,
  an instance of :class:`alerter.Generic` will be used.
    
  To keep the connection alive with your client, set `persistent` to `True`. This will
  increase the performance of the proxy but it is only useful if your client is aware that 
  only one connection can be establish with the proxy.
  In Firefox, set ``network.http.max-persistent-connections-per-proxy`` to 1.
  
  `verbose` determine the verbosity degree. If `False`, only the requests undergoing
  the `default_action` will be displayed. If equals to `1`, all the requests,
  including the one automatically processed will be displayed. If `2`, all the requests
  will be displayed, including their full content. If `3`, all the requests and responses
  will be displayed, including their full content.
 
  This function return a :class:`RequestSet` of all the successful :class:`Request` made.

