abrupt.conf - Configuration
===========================

.. module:: conf

.. class:: Configuration

  This class should not be instantiated. Instead, use
  the :data:`~conf.conf` instance, described below.

  .. method:: save()

    Save the current configuration. This method should only be called
    within the default session. Otherwise, simply call :func:`session.save()`.

  .. attribute:: autosave

    Autosave the session when terminating Abrupt or switching to a
    new one. By default, True.

  .. attribute:: color_enabled

    Boolean to activate or deactivate the colors in the console.
    By default, True.

  .. attribute:: delay

    Delay between requests when a :class:`~http.RequestSet` is executed.
    By default, 0.

  .. attribute:: diff_editor

    Default editor to use when comparing requests or responses.
    By default, ``/usr/bin/vimdiff``.

  .. attribute:: editor

    Default editor to use when editing a request or viewing a response.
    By default, ``/usr/bin/vim``.

  .. attribute:: editor_args

    Arguments for your editor when using the :meth:`~http.Request.edit` method.

  .. attribute:: editor_play_args

    Extra arguments when using the :meth:`~http.Request.play` method.

  .. attribute:: history

    Keep a copy of all the requests made in the global :mod:`history`.
    By default, True.

  .. attribute:: ip

    Default proxy ip. Default IP address on which Abrupt will listen. If None,
    will only listen on 127.0.0.1. By default, None.

  .. attribute:: port

    Default proxy port. See also the `port` parameter of the :func:`proxy.proxy`
    function. By default, 8080.

  .. attribute:: proxy

    Upstream proxy. Abrupt supports HTTP(S), Socks4a and Socks5 proxys, without
    authentication. By default, None.

  .. attribute:: ssl_hostname

    When using the :attr:`target` attribute, it is possible to set the expected
    hostname of the SSL certificate through this attribute.

  .. attribute:: ssl_reverse

    If True, the proxy will use the SSL hostname gathered by contacting the
    target server. The server certificate will be validated before being used.
    Therefore, :attr:`~conf.Configuration.ssl_verify` should be properly
    configured.

  .. attribute:: ssl_verify

    Path to the CA chain. If empty, no verification or validation is made
    on the server SSL certificate. By default, /etc/pki/tls/cert.pem.
    Under Ubuntu/Debian, you may use /etc/ssl/certs/ca-certificates.crt.

  .. attribute:: ssl_version

    SSL version to use when connecting to the server. Possible values
    are: SSLv2, SSLv3, TLSv1 and SSLv23.

  .. attribute:: target

    Set a target in case of transparent proxying. If your application is not
    proxy-aware, use this parameter to set a target. By default, None.

  .. attribute:: term_width

    Expected width of the terminal. Abrupt tries to optimise the output
    whenever possible in regards to the current terminal width. The
    default "auto" will try to get this information from the system. You
    can set any arbitrary integer. The value 0 will consider the width
    as unlimited.

  .. attribute:: update_content_length

    When editing a Request, Abrupt will automatically update any
    `Content-Length` header. To disable this feature, set this
    option to False. By default, True.

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
    >>> conf.proxy = "http://127.0.0.1:8081"
    >>> conf.save()
    >>> conf
    autosave: False
    diff_editor: /usr/bin/vimdiff
    editor: /usr/bin/vim
    history: True
    port: 8080
    proxy: http://127.0.0.1:8081
    ssl_version: SSLv3

