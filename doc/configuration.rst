abrupt.conf - Configuration
===========================

.. data:: conf

  Global object used to configure Abrupt. It is automatically
  loading when Abrupt starts, based on ~/.abrupt/abrupt.conf.

  It is *NOT* saved whenever a modification is made. You should
  manually call the :func:`save` function to make the modifications persistents.
  
  .. function:: save()
  
  Save the current configuration. 

  
  .. attribute:: proxy
  
  Upstream proxy. By default, None.

  .. attribute:: autosave 

  Autosave the session when terminating Abrupt or opening a new one. 
  By default, True.

  .. attribute:: history
  
  Keep a copy of all the requests made in the global :mod:`history`. 
  By default, True.


  Example::
    
    >>> conf
    proxy: None
    autosave: True
    history: True
    >>> conf.autosave = False
    >>> conf.save()
    >>> conf
    proxy: None
    autosave: False
    history: True



