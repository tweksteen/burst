abrupt.conf - Configuration
===========================

.. module:: conf

.. class:: Configuration
  
  This class should not be instanciated itself. Instead, use
  the :data:`~conf.conf` instance, described below.
  
  .. method:: save()
  
  Save the current configuration. This method should only be called
  outside a session. Inside a session, simply call :func:`session.save()`.
  
  .. attribute:: proxy
  
  Upstream proxy. By default, None.

  .. attribute:: port

  Default proxy port. See also the `port` parameter of the :func:`proxy.proxy`
  function. By default, 8080.

  .. attribute:: autosave 

  Autosave the session when terminating Abrupt or switching to a 
  new one. By default, True.

  .. attribute:: history
  
  Keep a copy of all the requests made in the global :mod:`history`. 
  By default, True.

  .. attribute:: ssl_version
  
  SSL version to use when connecting to the server. Possible values 
  are: SSLv2, SSLv3, TLSv1 and SSLv23.

  .. attribute:: editor
    
  Default editor to use when editing a request or viewing a response.
  By default, ``/usr/bin/vim``.


  .. attribute:: diff_editor
    
  Default editor to use when comparing requests or responses.
  By default, ``/usr/bin/vimdiff``.

.. data:: conf

  Global object used to configure Abrupt. It is automatically
  loading when Abrupt starts, based on ~/.abrupt/abrupt.conf.
  When a session is loaded, the configuration included inside 
  the session is used.

  By default, it is *NOT* saved whenever a modification is made. 
  You should manually call the :func:`~conf.Configuration.save` function 
  to make the modifications persistents. When a new session is started, 
  the current configuration is cloned into it. When the session is 
  saved, the associated configuration is included.

  Example::
    
    >>> conf
    autosave: True
    diff_editor: /usr/bin/vimdiff
    editor: /usr/bin/vim
    history: True
    port: 8080
    proxy: None
    ssl_version: SSLv3
    >>> conf.autosave = False
    >>> conf.save()
    >>> conf
    autosave: False
    diff_editor: /usr/bin/vimdiff
    editor: /usr/bin/vim
    history: True
    port: 8080
    proxy: None
    ssl_version: SSLv3

