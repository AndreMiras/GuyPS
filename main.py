__version__ = '0.1'
from kivy.garden.mapview import MapView, MapMarker, Coordinate
from kivy.app import App
from kivy.uix.popup import Popup
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
            # latlon = self.get_latlon_at(touch.pos[0], touch.pos[1])
            # m1 = MapMarker(lat=latlon.lat, lon=latlon.lon)
            # self.add_marker(m1)
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

class Controller(RelativeLayout):
    mapview_screen_property = ObjectProperty()

    def gps_localize(self):
        print "gps_localize"
        # TODO: loading status
        self.gps = gps
        try:
            self.gps.configure(on_location=self.on_location, on_status=self.on_status)
            self.gps.start()
        except NotImplementedError:
            popup = PopupMessage(
                        title="Error",
                        body="GPS not found.")
            popup.open()

    def on_location(self, **kwargs):
        # TODO: close loading status
        self.gps_location = '\n'.join(['{}={}'.format(k, v) for k, v in kwargs.items()])
        # map_screen = self.manager.get_screen('map')
        mapview = self.mapview_screen_property.ids['mapview']
        latitude = kwargs['lat']
        longitude = kwargs['lon']
        mapview.center_on(latitude, longitude)

    def on_status(self, stype, status):
        # TODO: use the status bar
        self.gps_status = 'type={}\n{}'.format(stype, status)


class MapViewApp(App):
    def build(self):
        global app
        app = self
        self.controller = Controller()
        return self.controller

MapViewApp().run()
