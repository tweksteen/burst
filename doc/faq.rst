FAQ
===

I found a bug
-------------

Before reporting it, please make sure you're using the version 2.7
of Python. If so, please email tw@securusglobal.com with the details
of the bugs. If you feel you can patch it yourself, pull requests on 
github are welcomed.

Can I script Abrupt?
--------------------

If you would like to script Abrupt (which is really easy,
since based on Python), you only need to import it. Once imported,
you can load a previously saved session. For instance::

  #!/usr/bin/env python2.7

  from abrupt.all import * 

  switch_session('my_test')

  irs = inject(r, to="param1", payload="sqli")
  print irs

Is there any HTTP syntax file for Vim?
--------------------------------------

Sure. On https://github.com/tweksteen/vim-http-syntax, grab
`http.vim` and put it in your `.vim/syntax/` directory. Then add
the following line to your `.vimrc`::

  au BufNewFile,BufRead *.http setf http


How can I see the list of existing sessions?
--------------------------------------------

If you are within Abrupt::
  
 >>> lss()

Otherwise, you can use the `-l` command line option::

 $ abrupt -l

What is the content of ``~/.abrupt``?
-------------------------------------

Abrupt creates a sub-directory to store its configuration, the certificates used
when connected via SSL and the sessions dumps. In this directory,
you will find:

  - ``abrupt.conf``, the default configuration.  
  - ``archives/``, archived Requests. See :meth:`~session.archive`.
  - ``certs/``, the CA certificate and the generated ones.
  - ``sessions/``, the sessions dump.

How can I set up an upstream proxy?
-----------------------------------
 
Simply set the configuration attribute :attr:`~conf.Configuration.proxy` to 
your HTTP(S) proxy address::

  >>> conf.proxy = "http://127.0.0.1:8081"


Abrupt does not respond after editing a Request
-----------------------------------------------

Once you've edited your Request (with :meth:`~http.Request.edit` or 
:meth:`~http.Request.play`), Abrupt try to recreate a new one based on the
file. If you have edited a POST request and changed the length of the body,
the `Content-Length` header might not match the real length. Therefore, Abrupt
can't properly parse your new Request. To avoid that, simply delete the 
`Content-Length` header, Abrupt will append a new one if it cannot be found. 


I'm confused, how do I execute a Request/RequestSet?
----------------------------------------------------

Simple call the __call__() method of your Request/RequestSet. In Python, this
method is used when you append `()` to your object::

  >>> r
  <GET www.example.org />
  >>> r()
  >>> r.response
  <200 1200>

I think I've just lost my last proxy capture, what can I do?
------------------------------------------------------------

Abrupt keep track of every Request made in: :data:`~http.history`. Try::

  >>> print history

I'm tired of typing 'print' all the time
----------------------------------------

Try::
  
  >>> p "test"

This RequestSet is gigantic! How can I have a better overview of it?
--------------------------------------------------------------------

There are few options to solve this issue. If you want, you could
start a pager on the represenation of the RequestSet::

  >>> less rs

You could also filter the RequestSet::

  >>> tiny_rs = rs.filter(lambda x: x.response.status == "500")

Or sort the RequestSet by length or by status::

  >>> rs.by_length()

Finally, you could use the experimental :meth:`~http.RequestSet.summary`
method to have a quick statistical overview of the responses.

