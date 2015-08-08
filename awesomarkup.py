FONT_PATH = 'static/fonts/fontawesome-4.4.0-webfont.ttf'

class_unicode = {
    'fa-map-marker': u'\uf041',
    'fa-bars': u'\uf0c9',
    'fa-map-pin': u'\uf276',
    'fa-map-o': u'\uf278',
    'fa-map': u'\uf279',
}

def awesomarkup(klass):
    code = class_unicode[klass]
    markup = u'[font=%s]%s[/font]' % (FONT_PATH, code)
    return markup
