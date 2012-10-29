abrupt.utils - Miscellaneous functions
======================================

.. function:: idle(request, delay=60, predicate=None, verbose=False)

  Call a request on regular interval until a condition is reached.
  The predicate parameter should be a function which takes two
  requests (old, new) and returns a boolean if the idle should terminate.
  If not supplied, the predicate will validate that the response status
  code remains the same.

.. function:: pxml(x)

  Pretty-print XML.
  If x is a request or a response, its content is pretty-printed.

.. function:: pjson(x)

  Pretty-print JSON.
  If x is a request or a response, its content is pretty-printed.

.. function:: e64(x)

  base 64 encode

.. function:: d64(x)

  base 64 decode

.. function:: encode(x)

  aliased `e`

  urlquote(x)

.. function:: decode(x)

  aliased `d`

  urlunquote(x)
