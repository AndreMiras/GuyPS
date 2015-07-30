__version__ = '0.1'
from kivy.garden.mapview import MapView, MapMarker, Coordinate
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ObjectProperty
from plyer import gps
from geopy.geocoders import Nominatim


app = None

class PopupMessage(Popup):
    title = StringProperty()
    body = StringProperty()

class CustomMapView(MapView):

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            latlon = self.get_latlon_at(touch.pos[0], touch.pos[1])
            self.animated_diff_scale_at(1, *touch.pos)
        return super(CustomMapView, self).on_touch_down(touch)

    def search(self, text):
        geolocator = Nominatim()
        location = geolocator.geocode(text)
        if location is None:
            popup = PopupMessage(
                        title="Error",
                        body="Can't find location.")
            popup.open()
            return
        # location.raw['boundingbox']
        latitude = location.latitude
        longitude = location.longitude
        self.center_on(latitude, longitude)

class MapViewScreen(Screen):

    status_message = StringProperty()
    search_input_property = ObjectProperty()

    def update_status_message(self, text, lifetime=3):
        self.status_message = text
        Clock.schedule_once(lambda dt: self.clean_status_message(), lifetime)

    def clean_status_message(self):
        self.update_status_message("")

class Controller(RelativeLayout):
    mapview_screen_property = ObjectProperty()
    mapview_property = ObjectProperty()

    def __init__(self, **kwargs):
        super(Controller, self).__init__(**kwargs)
        self.mapview_property = self.mapview_screen_property.ids['mapview']
        self.bind_events()

    def bind_events(self):
        search_input = self.mapview_screen_property.search_input_property
        search_input.bind(on_text_validate=lambda instance: self.on_search(search_input.text))

    def gps_localize(self):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Waiting for GPS location...", 10)
        try:
            gps.configure(on_location=self.on_location, on_status=self.on_status)
            gps.start()
        except NotImplementedError:
            message = "GPS not found."
            mapview_screen.update_status_message(message)
            popup = PopupMessage(
                        title="Error",
                        body=message)
            popup.open()

    def toggle_gps_localize(self, start):
        if start:
            self.gps_localize()
        else:
            gps.stop()

    def on_location(self, **kwargs):
        # gps.stop()
        mapview = self.mapview_property
        mapview_screen = self.mapview_screen_property
        latitude = kwargs['lat']
        longitude = kwargs['lon']
        mapview.center_on(latitude, longitude)
        mapview_screen.update_status_message(
            "Latitude: %s / Longitude: %s" % (round(latitude, 2), round(longitude, 2)), 10)

    def on_status(self, stype, status):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message(
            'type={}\n{}'.format(stype, status), 10)

    def on_search(self, text):
        mapview_screen= self.mapview_screen_property
        mapview_screen.update_status_message("Looking for \"%s\"" % (text))


class MapViewApp(App):
    def build(self):
        global app
        app = self
        self.controller = Controller()
        return self.controller

MapViewApp().run()
