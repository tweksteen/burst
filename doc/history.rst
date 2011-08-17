abrupt.history - Global history
===============================

By default, Abrupt keep track of all the requests made:

.. data:: history
   
  History is a :class:`RequestSet` which contains all the requests
  made through Abrupt. To turn it off, set `conf.history` to False.

  Example::

    >>> history
    {200:3 404:2 | www.phrack.org}
    >>> p history
    Method Path                 Query Status Length 
    GET    /                          200    6174   
    GET    /style.css                 200    4406   
    GET    /img/phrack-logo.jpg       200    82036  
    GET    /favicon.ico               404    183    
    GET    /favicon.ico               404    183    

