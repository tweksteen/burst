from pygments.lexer import RegexLexer, bygroups
from pygments.token import *

class AbruptProxyLexer(RegexLexer):
    name = 'abrupt-proxy'
    aliases = ['abr-proxy']
    filenames = ['']

    tokens = {
        'root': [
            (r'^(\[[0-9]\]\s+<)(GET)(.*)$', bygroups( Text, String, Text)),
            (r'^(\[[0-9]\]\s+<)(200)(.*)$', bygroups( Text, String.Symbol, Text)),
            (r'.*\n', Text),
        ]
    }


def setup(app):
  app.add_lexer("abrupt-proxy", AbruptProxyLexer())


