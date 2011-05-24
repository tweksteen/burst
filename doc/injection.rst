abrupt.injection - Request generator
====================================

The injection module provides two functions to "inject" a request (i.e.,
generate a :class:`RequestSet` from a Request using a list of payloads):

.. function:: i(request, param=payload_name, [pre_func=e])
  
  This function will try to find the value `param` at the following locations:

    * URL parameters
    * Cookies
    * Content for a POST or PUT request

  Then, for each payload contained in `payloads[payload_name]`, it
  will generate a request, based on `request`
  payload_name should be a key of the :attr:`payloads` dictionnary.

.. function:: i_at(request, offset, payload=payload_name, [pre_func=e])

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

Some handy functions are also defined:

.. function:: e(x)

  urlquote(x)

.. function:: d(x)

  urlunquote(x)

