import os
import yaml
try:
    # uses LibYAML bindings (faster parser) when available
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


FONT_DIRECTORY = 'static/fontawesome/'
FONT_PATH = os.path.join(FONT_DIRECTORY, 'fontawesome-webfont.ttf')
YAML_PATH = os.path.join(FONT_DIRECTORY, 'icons.yml')

with open(YAML_PATH) as icons_file:
    icons_obj = yaml.load(icons_file, Loader=Loader)

# creates a dictionary of {class: unicode} like so:
# {
# 'fa-glass': u'\uf000',
# 'fa-music': u'\uf001',
# ...
# 'fa-percent': u'\uf295',
# }
class_unicode = dict(
        [('fa-' + x['id'], x['unicode']) for x in icons_obj['icons']])


def awesomarkup(klass):
    code = class_unicode[klass]
    uni_code = unichr(int(code, 16))
    markup = u'[font=%s]%s[/font]' % (FONT_PATH, uni_code)
    return markup
