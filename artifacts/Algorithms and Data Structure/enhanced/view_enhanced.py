from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from typing import Callable, List, Optional
from model_enhanced import Trip, Location

class TripMapView(Widget):
    """
    Custom widget to show a map view of trip locations.
    Implements a simple visualization of locations.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.locations = []
        self.selected_location = None
        self.bind(size=self._update_canvas, pos=self._update_canvas)
    
    def set_locations(self, locations: List[Location]):
        """Set the locations to display on the map."""
        self.locations = locations
        self._update_canvas()
    
    def _update_canvas(self, *args):
        """Update the canvas with the current locations."""
        self.canvas.clear()
        
        if not self.locations:
            return
        
        # Get min/max coordinates to scale the map
        min_lat = min(loc.latitude for loc in self.locations)
        max_lat = max(loc.latitude for loc in self.locations)
        min_lon = min(loc.longitude for loc in self.locations)
        max_lon = max(loc.longitude for loc in self.locations)
        
        # Add padding
        lat_padding = (max_lat - min_lat) * 0.1 if max_lat != min_lat else 0.1
        lon_padding = (max_lon - min_lon) * 0.1 if max_lon != min_lon else 0.1
        
        min_lat -= lat_padding
        max_lat += lat_padding
        min_lon -= lon_padding
        max_lon += lon_padding
        
        # Draw background
        with self.canvas:
            Color(0.9, 0.9, 0.9, 1)
            Rectangle(pos=self.pos, size=self.size)
        
        # Draw connections between points if multiple locations
        if len(self.locations) > 1:
            with self.canvas:
                Color(0.5, 0.5, 0.8, 0.7)
                for i in range(len(self.locations) - 1):
                    start = self._map_coords_to_pos(
                        self.locations[i].latitude,
                        self.locations[i].longitude,
                        min_lat, max_lat, min_lon, max_lon
                    )
                    end = self._map_coords_to_pos(
                        self.locations[i+1].latitude,
                        self.locations[i+1].longitude,
                        min_lat, max_lat, min_lon, max_lon
                    )
                    Line(points=[start[0], start[1], end[0], end[1]], width=2)
        
        # Draw points
        for i, location in enumerate(self.locations):
            x, y = self._map_coords_to_pos(
                location.latitude,
                location.longitude,
                min_lat, max_lat, min_lon, max_lon
            )
            
            with self.canvas:
                # Draw point
                if self.selected_location == location.id:
                    Color(0.9, 0.3, 0.3, 1)  # Selected location
                else:
                    Color(0.3, 0.3, 0.9, 1)  # Normal location
                
                point_size = 10
                Rectangle(
                    pos=(x - point_size/2, y - point_size/2),
                    size=(point_size, point_size)
                )
                
                # Draw label
                Color(0, 0, 0, 1)
                label = Label(
                    text=f"{i+1}. {location.name}",
                    font_size='10sp',
                    color=(0, 0, 0, 1),
                    pos=(x + 5, y - 5),
                    size_hint=(None, None),
                    size=(100, 20)
                )
                label.texture_update()
                Rectangle(
                    pos=label.pos,
                    size=label.texture_size,
                    texture=label.texture
                )
    
    def _map_coords_to_pos(self, lat, lon, min_lat, max_lat, min_lon, max_lon):
        """Map geographic coordinates to widget position."""
        # Flip latitude because screen coordinates go from top to bottom
        y_ratio = 1 - (lat - min_lat) / (max_lat - min_lat) if max_lat != min_lat else 0.5
        x_ratio = (lon - min_lon) / (max_lon - min_lon) if max_lon != min_lon else 0.5
        
        x = self.pos[0] + x_ratio * self.size[0]
        y = self.pos[1] + y_ratio * self.size[1]
        
        return x, y
    
    def on_touch_down(self, touch):
        """Handle touch events to select locations."""
        if self.collide_point(*touch.pos) and self.locations:
            # Get min/max coordinates
            min_lat = min(loc.latitude for loc in self.locations)
            max_lat = max(loc.latitude for loc in self.locations)
            min_lon = min(loc.longitude for loc in self.locations)
            max_lon = max(loc.longitude for loc in self.locations)
            
            # Add padding
            lat_padding = (max_lat - min_lat) * 0.1 if max_lat != min_lat else 0.1
            lon_padding = (max_lon - min_lon) * 0.1 if max_lon != min_lon else 0.1
            
            min_lat -= lat_padding
            max_lat += lat_padding
            min_lon -= lon_padding
            max_lon += lon_padding
            
            # Find closest location
            closest_location = None
            min_distance = float('inf')
            
            for location in self.locations:
                loc_x, loc_y = self._map_coords_to_pos(
                    location.latitude,
                    location.longitude,
                    min_lat, max_lat, min_lon, max_lon
                )
                
                distance = ((touch.x - loc_x) ** 2 + (touch.y - loc_y) ** 2) ** 0.5
                
                if distance < min_distance and distance < 20:  # 20 pixels threshold
                    min_distance = distance
                    closest_location = location
            
            if closest_location:
                self.selected_location = closest_location.id
                self._update_canvas()
                return True
        
        return super().on_touch_down(touch)


class TripItem(BoxLayout):
    """
    Widget for displaying a trip in the list.
    """
    
    def __init__(self, trip: Trip, on_edit: Callable[[Trip], None], 
                 on_delete: Callable[[Trip], None], on_show_details: Callable[[Trip], None],
                 on_optimize_route: Callable[[Trip], None], **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(70)
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)
        
        # Left column: Trip info
        info_layout = BoxLayout(orientation='vertical', size_hint_x=0.6)
        
        # Trip destination
        info_layout.add_widget(Label(
            text=trip.destination,
            size_hint_y=None,
            height=dp(25),
            font_size='16sp',
            bold=True,
            halign='left',
            text_size=(300, None)
        ))
        
        # Created date
        info_layout.add_widget(Label(
            text=f"Created: {trip.created_at.strftime('%Y-%m-%d %H:%M')}",
            size_hint_y=None,
            height=dp(20),
            font_size='12sp',
            halign='left',
            text_size=(300, None)
        ))
        
        # Location count
        location_count = len(trip.locations) if trip.locations else 0
        info_layout.add_widget(Label(
            text=f"Locations: {location_count}",
            size_hint_y=None,
            height=dp(20),
            font_size='12sp',
            halign='left',
            text_size=(300, None)
        ))
        
        self.add_widget(info_layout)
        
        # Right column: Buttons
        button_layout = BoxLayout(
            orientation='vertical',
            size_hint_x=0.4,
            spacing=dp(5)
        )
        
        # Top row buttons
        top_buttons = BoxLayout(
            size_hint_y=None,
            height=dp(30),
            spacing=dp(5)
        )
        
        edit_btn = Button(
            text='Edit',
            size_hint_x=0.5,
            font_size='12sp'
        )
        edit_btn.bind(on_press=lambda x: on_edit(trip))
        
        delete_btn = Button(
            text='Delete',
            size_hint_x=0.5,
            font_size='12sp'
        )
        delete_btn.bind(on_press=lambda x: on_delete(trip))
        
        top_buttons.add_widget(edit_btn)
        top_buttons.add_widget(delete_btn)
        button_layout.add_widget(top_buttons)
        
        # Bottom row buttons
        bottom_buttons = BoxLayout(
            size_hint_y=None,
            height=dp(30),
            spacing=dp(5)
        )
        
        details_btn = Button(
            text='Details',
            size_hint_x=0.5,
            font_size='12sp'
        )
        details_btn.bind(on_press=lambda x: on_show_details(trip))
        
        optimize_btn = Button(
            text='Optimize',
            size_hint_x=0.5,
            font_size='12sp'
        )
        optimize_btn.bind(on_press=lambda x: on_optimize_route(trip))
        
        bottom_buttons.add_widget(details_btn)
        bottom_buttons.add_widget(optimize_btn)
        button_layout.add_widget(bottom_buttons)
        
        self.add_widget(button_layout)


class TripPlannerView(BoxLayout):
    """
    Main view for the Trip Planner application.
    """
    
    def __init__(self, on_add_trip: Callable[[str], None], 
                 on_edit_trip: Callable[[Trip], None],
                 on_delete_trip: Callable[[Trip], None],
                 on_show_details: Callable[[Trip], None],
                 on_optimize_route: Callable[[Trip], None], **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.padding = dp(10)
        self.spacing = dp(10)
        
        # Store callbacks
        self.on_add_trip = on_add_trip
        self.on_edit_trip = on_edit_trip
        self.on_delete_trip = on_delete_trip
        self.on_show_details = on_show_details
        self.on_optimize_route = on_optimize_route
        
        # App title
        title_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50)
        )
        
        title_label = Label(
            text="Mobile Trip Planner",
            font_size='24sp',
            bold=True
        )
        title_layout.add_widget(title_label)
        self.add_widget(title_layout)
        
        # Input area
        input_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        self.destination_input = TextInput(
            hint_text='Enter destination',
            multiline=False,
            size_hint_x=0.7
        )
        
        add_button = Button(
            text='Add Trip',
            size_hint_x=0.3
        )
        add_button.bind(on_press=lambda x: self._handle_add_trip())
        
        input_layout.add_widget(self.destination_input)
        input_layout.add_widget(add_button)
        self.add_widget(input_layout)
        
        # Trip list
        list_label = Label(
            text="Your Trips:",
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(20), None)
        )
        self.add_widget(list_label)
        
        scroll_view = ScrollView()
        self.trip_list = GridLayout(
            cols=1,
            spacing=dp(5),
            size_hint_y=None,
            padding=[0, 0, 0, dp(10)]
        )
        self.trip_list.bind(minimum_height=self.trip_list.setter('height'))
        scroll_view.add_widget(self.trip_list)
        self.add_widget(scroll_view)
    
    def _handle_add_trip(self):
        """Handle add trip button press."""
        destination = self.destination_input.text.strip()
        if destination and self.on_add_trip:
            self.on_add_trip(destination)
    
    def update_trip_list(self, trips: List[Trip]):
        """Update the trip list with new data."""
        self.trip_list.clear_widgets()
        
        if not trips:
            self.trip_list.add_widget(Label(
                text="No trips found. Add a trip to get started!",
                size_hint_y=None,
                height=dp(50)
            ))
            return
        
        for trip in trips:
            trip_item = TripItem(
                trip=trip,
                on_edit=self.on_edit_trip,
                on_delete=self.on_delete_trip,
                on_show_details=self.on_show_details,
                on_optimize_route=self.on_optimize_route
            )
            self.trip_list.add_widget(trip_item) 
