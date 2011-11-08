abrupt.session - Session handler
================================

.. module:: session

Abrupt comes with a powerful session handler. Within a session, you can keep 
track of your data, the history of the requests made and the associated 
configuration. By default, your session will be automatically saved whenever 
you exit Abrupt or switch to a new one. When using a session, Abrupt will 
change the prompt ``>>>`` to ``session_name >>>``. To remind you to save the 
session from time to time, the color of the prompt will automatically change 
to red if no save point has been made for the last twenty minutes.

.. function:: switch_session(session_name='default')
  
  aliased `ss`

  Session switch. Save the current session (if 
  :attr:`~conf.Configuration.autosave` is on), close it and load the session
  `session_name`. If `session_name` already exists, the last valid save is 
  restored, otherwise a new session is created.

.. function:: save()
  
  Save the current session.

.. function:: list_sessions()

  aliased `lss`  

  List the existing sessions.

.. function:: archive(name=None)

  When calling the :func:`save` function, Abrupt uses the Python pickle format
  to quickly store your session data (which includes requests, response or any
  pickable python object you used). This format is appropriate for everyday
  use but not for long term storage. In this purpose, the archive function
  enables you to store all the requests made through Abrupt with their
  associated responses in a compressed human-readable file. Upon call, an
  archive will be create in ``~/.abrupt/archives``. If name is supplied,
  it is used as prefix for the archive name.

