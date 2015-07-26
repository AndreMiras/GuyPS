__version__ = '0.1'
from kivy.garden.mapview import MapView, MapMarker, Coordinate
from kivy.app import App
from geopy.geocoders import Nominatim


app = None

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
        # location.raw['boundingbox']
        latitude = location.latitude
        longitude = location.longitude
        self.center_on(latitude, longitude)



class MapViewApp(App):
    def build(self):
        # mapview = CustomMapView(zoom=11, lat=50.6394, lon=3.057)
        # return mapview
        global app
        app = self

MapViewApp().run()
