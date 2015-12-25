from kivy.uix.popup import Popup
from kivy.properties import StringProperty


class PopupMessage(Popup):
    title = StringProperty()
    body = StringProperty()
