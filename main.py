import os
import glob
import logging
from threading import Thread
from kivy.garden.mapview import MapView, MapMarker, Coordinate
from kivy.garden.mapview.mapview.mbtsource import MBTilesMapSource
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ObjectProperty
from kivy.animation import Animation
from plyer import gps
from geopy.geocoders import Nominatim
from landez import MBTilesBuilder


__version__ = '0.1'
logging.basicConfig(level=logging.DEBUG)
app = None


class PopupMessage(Popup):
    title = StringProperty()
    body = StringProperty()


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


class GpsMarker(MapMarker):

    def update_position(self):
        """
        Updates marker position on map layer.
        """
        layer = self._layer
        if layer is None:
            return
        mapview = layer.parent
        marker = self
        layer.set_marker_position(mapview, marker)

    def on_lat(self, instance, value):
        self.update_position()

    def on_lon(self, instance, value):
        self.update_position()


class OfflineMapsScreen(Screen):

    offline_maps_spinner = ObjectProperty()

    def available_offline_maps(self):
        """
        Lists *.mbtiles files and returns their basename.
        """
        filepath = os.path.join(App.get_running_app().mbtiles_directory, '*.mbtiles')
        filepaths = glob.glob(filepath)
        filenames = [os.path.basename(x) for x in filepaths]
        return filenames


class CustomMapView(MapView):

    animated_latlon_property = ObjectProperty()

    def __init__(self, **kwargs):
        super(CustomMapView, self).__init__(**kwargs)
        self.animated_latlon_property = Coordinate(self.lat, self.lon)

    def animated_center_on(self, latitude, longitude):
        widget = self
        anim = Animation(
            animated_latlon_property=Coordinate(latitude, longitude))
        anim.start(widget)

    def on_animated_latlon_property(self, instance, coordinate):
        # coordinate somehow lost its type
        coordinate = Coordinate(coordinate[0], coordinate[1])
        latitude = coordinate.lat
        longitude = coordinate.lon
        self.center_on(latitude, longitude)

    def on_touch_down(self, touch):
        if touch.is_double_tap:
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
        latitude = location.latitude
        longitude = location.longitude
        # self.center_on(latitude, longitude)
        self.animated_center_on(latitude, longitude)

    def load_mbtiles(self, mbtiles):
        mbtiles_path = os.path.join(App.get_running_app().mbtiles_directory, mbtiles)
        map_source = MBTilesMapSource(mbtiles_path)
        self.map_source = map_source


class MapViewScreen(Screen):

    status_message = StringProperty()
    search_input_property = ObjectProperty()

    def update_status_message(self, text, lifetime=3):
        self.status_message = text
        # http://kivy.org/docs/api-kivy.clock.html
        # You cannot unschedule an anonymous function unless you keep
        # a reference to it.
        # It's better to add *args to your function definition
        # so that it can be called with an arbitrary number of parameters.
        Clock.unschedule(self.clean_status_message)
        Clock.schedule_once(self.clean_status_message, lifetime)

    def clean_status_message(self, dt):
        self.update_status_message("")


class Controller(RelativeLayout):
    mapview_screen_property = ObjectProperty()
    mapview_property = ObjectProperty()

    def __init__(self, **kwargs):
        super(Controller, self).__init__(**kwargs)
        self.gps_marker = None
        self.mapview_property = self.mapview_screen_property.ids['mapview']
        self.bind_events()

    def bind_events(self):
        search_input = self.mapview_screen_property.search_input_property
        search_input.bind(
            on_text_validate=lambda obj: self.on_search(search_input.text))

    def start_gps_localize(self):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Waiting for GPS location...", 10)
        try:
            gps.configure(
                on_location=self.on_location, on_status=self.on_status)
            gps.start()
        except NotImplementedError:
            message = "GPS not found."
            mapview_screen.update_status_message(message)
            popup = PopupMessage(
                        title="Error",
                        body=message)
            popup.open()

    def stop_gps_localize(self):
        mapview = self.mapview_property
        gps.stop()
        # if self.gps_marker is None:
        mapview.remove_marker(self.gps_marker)
        self.gps_marker = None

    def toggle_gps_localize(self, start):
        if start:
            self.start_gps_localize()
        else:
            self.stop_gps_localize()

    def on_location(self, **kwargs):
        # gps.stop()
        mapview = self.mapview_property
        mapview_screen = self.mapview_screen_property
        latitude = kwargs['lat']
        longitude = kwargs['lon']
        if self.gps_marker is None:
            self.gps_marker = GpsMarker(lat=latitude, lon=longitude)
            mapview.add_marker(self.gps_marker)
        else:
            self.gps_marker.lat = latitude
            self.gps_marker.lon = longitude
        mapview.animated_center_on(latitude, longitude)
        mapview_screen.update_status_message(
            "Latitude: %s / Longitude: %s" %
            (round(latitude, 2), round(longitude, 2)), 10)

    def on_status(self, stype, status):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message(
            'type={}\n{}'.format(stype, status), 10)

    def on_search(self, text):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Looking for \"%s\"" % (text))

    def prepare_download_for_offline(self, text):
        geolocator = Nominatim()
        location = geolocator.geocode(text)
        if location is None:
            popup = PopupMessage(
                        title="Error",
                        body="Can't find location.")
            popup.open()
            return
        if location.raw['type'] != 'city':
            popup = PopupMessage(
                        title="Error",
                        body="Only cities are allowed.")
            popup.open()
            return
        # move to the downloading location
        mapview = self.mapview_property
        mapview.animated_center_on(location.latitude, location.longitude)
        # exctracts the city from the address string
        city = location.address.split(',')[0]
        if not os.path.exists(App.get_running_app().mbtiles_directory):
            os.makedirs(App.get_running_app().mbtiles_directory)
        filename = city + '.mbtiles'
        filepath = os.path.join(App.get_running_app().mbtiles_directory, filename)
        if os.path.exists(filepath):
            popup = ConfirmPopup(
                title="File already exists",
                text="File already exists.\nDo you want to override?")
            popup.bind(on_yes=lambda obj: self.download_for_offline(filepath, location, delete=True))
            popup.open()
            mapview_screen = self.mapview_screen_property
            mapview_screen.update_status_message("File already exists: %s" % (filename), 10)
            return
        self.download_for_offline(filepath, location)

    def download_for_offline(self, filepath, location, delete=False):
        if delete:
            os.remove(filepath)
        mb = MBTilesBuilder(filepath=filepath, cache=True)
        # changes geopy bounding box format to landez one
        (min_lat, max_lat, min_lon, max_lon) = \
            [float(x) for x in location.raw['boundingbox']]
        bbox = (min_lon, min_lat, max_lon, max_lat)
        mb.add_coverage(bbox=bbox,
                        zoomlevels=[12, 13, 14, 15])
        mb_run_thread = Thread(target=mb.run, kwargs={'force': False})
        mb_run_thread.start()
        Clock.schedule_interval(lambda dt: self.probe_mb_tiles_builder_thread(mb, mb_run_thread), 0.5)

    def probe_mb_tiles_builder_thread(self, mb, mb_run_thread):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Downloading tiles %s/%s" % (mb.rendered, mb.nbtiles), 10)
        if not mb_run_thread.is_alive():
            mapview_screen.update_status_message("Downloading tiles %s/%s" % (mb.nbtiles, mb.nbtiles), 10)
            return False

    def load_mbtiles(self, mbtiles):
        mapview = self.mapview_property
        mapview.load_mbtiles(mbtiles)


class MapViewApp(App):
    def build(self):
        global app
        app = self
        self.controller = Controller()
        return self.controller

    def on_pause(self):
        # do not be close the application completely
        return True

    @property
    def mbtiles_directory(self):
        return os.path.join(self.user_data_dir, 'mbtiles')

MapViewApp().run()
