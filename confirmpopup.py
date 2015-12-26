"""
Makes it easy to create simple confirmation dialog.
The dialog contains title, message body and yes/no button.
"""
from kivy.uix.popup import Popup
from kivy.properties import StringProperty


class ConfirmPopup(Popup):
    title = StringProperty()
    text = StringProperty()

    def __init__(self,**kwargs):
        self.register_event_type('on_answer')
        self.register_event_type('on_yes')
        self.register_event_type('on_no')
        super(ConfirmPopup, self).__init__(**kwargs)

    def on_answer(self, *args):
        pass

    def on_yes(self, *args):
        pass

    def on_no(self, *args):
        pass
