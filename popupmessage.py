"""
Reusable PopupMessage class.
Makes it easy to create simple popup messages with title and message body.
The popup discarts when clicking on it or anywhere.
"""
from kivy.uix.popup import Popup
from kivy.properties import StringProperty


class PopupMessage(Popup):
    title = StringProperty()
    body = StringProperty()
