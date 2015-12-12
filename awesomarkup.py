import os
import xstatic.pkg.font_awesome


FONT_PATH = os.path.join(
        xstatic.pkg.font_awesome.BASE_DIR,
        'fonts/fontawesome-webfont.ttf')
class_unicode = {
    'fa-download': u'\uf019',
    'fa-map-marker': u'\uf041',
    'fa-cogs': u'\uf085',
    'fa-bars': u'\uf0c9',
    'fa-map-pin': u'\uf276',
    'fa-map-o': u'\uf278',
    'fa-map': u'\uf279',
}

def awesomarkup(klass):
    code = class_unicode[klass]
    markup = u'[font=%s]%s[/font]' % (FONT_PATH, code)
    return markup
