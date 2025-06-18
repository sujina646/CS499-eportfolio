from typing import List, Optional, Dict, Any
from model_enhanced import TripModel, Trip, Location, DatabaseError
from view import TripPlannerView
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.metrics import dp
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import threading
import time
import traceback

class TripController:
    def __init__(self, model: TripModel, view: TripPlannerView):
        self.model = model
        self.view = view
        
        # Set event handlers
        self.view.on_add_trip = self.add_trip
        self.view.on_edit_trip = self.edit_trip
        self.view.on_delete_trip = self.delete_trip
        self.view.on_show_details = self.show_trip_details
        self.view.on_optimize_route = self.optimize_route
        
        # Initialize view
        self._load_trips()
    
    def _load_trips(self):
        """Load trips from model and update view."""
        try:
            trips = self.model.get_all_trips()
            self.view.update_trip_list(trips)
        except DatabaseError as e:
            self._show_error("Failed to load trips", str(e))
    
    def add_trip(self, destination: str):
        """Add a new trip."""
        try:
            if not destination.strip():
                self._show_error("Invalid Input", "Destination cannot be empty")
                return
                
            self.model.add_trip(destination)
            self._load_trips()
            self.view.destination_input.text = ""
        except DatabaseError as e:
            self._show_error("Failed to add trip", str(e))
    
    def edit_trip(self, trip: Trip):
        """Edit an existing trip."""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Edit input
        edit_input = TextInput(
            text=trip.destination,
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(edit_input)
        
        # Buttons
        button_layout = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(10)
        )
        
        save_btn = Button(text='Save')
        cancel_btn = Button(text='Cancel')
        
        popup = Popup(
            title='Edit Trip',
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        def save_trip(instance):
            try:
                new_destination = edit_input.text.strip()
                if new_destination:
                    self.model.update_trip(trip.id, new_destination)
                    self._load_trips()
                popup.dismiss()
            except DatabaseError as e:
                self._show_error("Failed to update trip", str(e))
        
        save_btn.bind(on_press=save_trip)
        cancel_btn.bind(on_press=popup.dismiss)
        
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)
        
        popup.open()
    
    def delete_trip(self, trip: Trip):
        """Delete a trip."""
        try:
            if self.model.delete_trip(trip.id):
                self._load_trips()
        except DatabaseError as e:
            self._show_error("Failed to delete trip", str(e))
    
    def show_trip_details(self, trip: Trip):
        """Show trip details and locations."""
        # Create content layout
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Trip info
        info_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60))
        info_layout.add_widget(Label(
            text=f"Destination: {trip.destination}",
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(400, None)
        ))
        info_layout.add_widget(Label(
            text=f"Created: {trip.created_at.strftime('%Y-%m-%d %H:%M')}",
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(400, None)
        ))
        content.add_widget(info_layout)
        
        # Add location section
        add_location_layout = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(5)
        )
        
        location_name_input = TextInput(
            hint_text='Location name',
            multiline=False,
            size_hint_x=0.3
        )
        
        lat_input = TextInput(
            hint_text='Latitude',
            multiline=False,
            size_hint_x=0.2,
            input_filter='float'
        )
        
        lon_input = TextInput(
            hint_text='Longitude',
            multiline=False,
            size_hint_x=0.2,
            input_filter='float'
        )
        
        add_location_btn = Button(
            text='Add Location',
            size_hint_x=0.3
        )
        
        add_location_layout.add_widget(location_name_input)
        add_location_layout.add_widget(lat_input)
        add_location_layout.add_widget(lon_input)
        add_location_layout.add_widget(add_location_btn)
        content.add_widget(add_location_layout)
        
        # Locations list
        locations_label = Label(
            text="Trip Locations:",
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(400, None)
        )
        content.add_widget(locations_label)
        
        # Create scrollview for locations
        scroll_view = ScrollView(
            size_hint=(1, None),
            height=dp(200)
        )
        
        locations_grid = GridLayout(
            cols=1,
            spacing=dp(2),
            size_hint_y=None
        )
        locations_grid.bind(minimum_height=locations_grid.setter('height'))
        
        # Add locations to grid
        if trip.locations:
            for location in trip.locations:
                location_item = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(40),
                    spacing=dp(5)
                )
                
                location_item.add_widget(Label(
                    text=f"{location.name} ({location.latitude}, {location.longitude})",
                    size_hint_x=0.7,
                    halign='left',
                    text_size=(300, None)
                ))
                
                remove_btn = Button(
                    text='Remove',
                    size_hint_x=0.3
                )
                remove_btn.bind(
                    on_press=lambda btn, loc_id=location.id: self._remove_location(trip.id, loc_id, locations_grid)
                )
                
                location_item.add_widget(remove_btn)
                locations_grid.add_widget(location_item)
        else:
            locations_grid.add_widget(Label(
                text="No locations added to this trip yet.",
                size_hint_y=None,
                height=dp(40)
            ))
        
        scroll_view.add_widget(locations_grid)
        content.add_widget(scroll_view)
        
        # Optimize route button
        optimize_btn = Button(
            text='Optimize Route',
            size_hint_y=None,
            height=dp(50)
        )
        optimize_btn.bind(on_press=lambda x: self.optimize_route(trip))
        content.add_widget(optimize_btn)
        
        # Cache statistics button
        cache_stats_btn = Button(
            text='View Cache Statistics',
            size_hint_y=None,
            height=dp(50)
        )
        cache_stats_btn.bind(on_press=lambda x: self._show_cache_stats())
        content.add_widget(cache_stats_btn)
        
        # Close button
        close_btn = Button(
            text='Close',
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(close_btn)
        
        # Create popup
        popup = Popup(
            title=f'Trip Details: {trip.destination}',
            content=content,
            size_hint=(0.9, 0.9)
        )
        
        # Set button actions
        close_btn.bind(on_press=popup.dismiss)
        
        def add_location(instance):
            try:
                name = location_name_input.text.strip()
                lat_text = lat_input.text.strip()
                lon_text = lon_input.text.strip()
                
                if not name or not lat_text or not lon_text:
                    self._show_error("Invalid Input", "All fields are required")
                    return
                
                try:
                    latitude = float(lat_text)
                    longitude = float(lon_text)
                except ValueError:
                    self._show_error("Invalid Input", "Latitude and longitude must be valid numbers")
                    return
                
                # Add location to database
                location = self.model.add_location(name, latitude, longitude)
                
                # Add location to trip
                self.model.add_location_to_trip(trip.id, location.id)
                
                # Reload popup content to show new location
                popup.dismiss()
                self.show_trip_details(self.model.get_trip_by_id(trip.id))
                
            except DatabaseError as e:
                self._show_error("Failed to add location", str(e))
        
        add_location_btn.bind(on_press=add_location)
        
        # Show popup
        popup.open()
    
    def _remove_location(self, trip_id: int, location_id: int, grid_layout: GridLayout):
        """Remove a location from a trip and update the UI."""
        try:
            if self.model.remove_location_from_trip(trip_id, location_id):
                # Reload trip details
                trip = self.model.get_trip_by_id(trip_id)
                if trip:
                    # Clear and rebuild locations grid
                    grid_layout.clear_widgets()
                    
                    if trip.locations:
                        for location in trip.locations:
                            location_item = BoxLayout(
                                orientation='horizontal',
                                size_hint_y=None,
                                height=dp(40),
                                spacing=dp(5)
                            )
                            
                            location_item.add_widget(Label(
                                text=f"{location.name} ({location.latitude}, {location.longitude})",
                                size_hint_x=0.7,
                                halign='left',
                                text_size=(300, None)
                            ))
                            
                            remove_btn = Button(
                                text='Remove',
                                size_hint_x=0.3
                            )
                            remove_btn.bind(
                                on_press=lambda btn, loc_id=location.id: self._remove_location(trip_id, loc_id, grid_layout)
                            )
                            
                            location_item.add_widget(remove_btn)
                            grid_layout.add_widget(location_item)
                    else:
                        grid_layout.add_widget(Label(
                            text="No locations added to this trip yet.",
                            size_hint_y=None,
                            height=dp(40)
                        ))
        except DatabaseError as e:
            self._show_error("Failed to remove location", str(e))
    
    def optimize_route(self, trip: Trip):
        """Optimize the route for a trip using pathfinding algorithm."""
        if not trip.locations or len(trip.locations) < 2:
            self._show_error("Cannot Optimize", "Trip needs at least 2 locations to optimize route")
            return
        
        # Create progress popup
        content = BoxLayout(orientation='vertical', padding=dp(20))
        progress_label = Label(
            text="Optimizing route...\nThis may take a moment.",
            halign='center'
        )
        content.add_widget(progress_label)
        
        popup = Popup(
            title='Optimizing Route',
            content=content,
            size_hint=(0.7, 0.3),
            auto_dismiss=False
        )
        popup.open()
        
        # Run optimization in background thread to keep UI responsive
        def optimize_thread():
            try:
                # Optimize route
                optimized_route = self.model.optimize_trip_route(trip.id)
                
                # Update UI on main thread
                def update_ui(dt):
                    popup.dismiss()
                    if optimized_route:
                        # Show success message
                        self._show_info(
                            "Route Optimized",
                            f"Trip route has been optimized to minimize travel distance.\n"
                            f"New route order: {', '.join(loc.name for loc in optimized_route)}"
                        )
                        # Refresh trip details
                        updated_trip = self.model.get_trip_by_id(trip.id)
                        if updated_trip:
                            self.show_trip_details(updated_trip)
                    else:
                        self._show_error("Optimization Failed", "Could not optimize the route")
                
                # Schedule UI update on main thread
                from kivy.clock import Clock
                Clock.schedule_once(update_ui, 0)
                
            except Exception as e:
                # Show error on main thread
                def show_error(dt):
                    popup.dismiss()
                    self._show_error("Optimization Error", str(e))
                
                from kivy.clock import Clock
                Clock.schedule_once(show_error, 0)
        
        # Start optimization thread
        threading.Thread(target=optimize_thread).start()
    
    def _show_cache_stats(self):
        """Show cache statistics in a popup."""
        try:
            stats = self.model.get_cache_stats()
            
            # Create content
            content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
            
            # Trip cache stats
            trip_cache = stats.get("trip_cache", {})
            content.add_widget(Label(
                text="Trip Cache Statistics:",
                size_hint_y=None,
                height=dp(30),
                halign='left',
                text_size=(400, None),
                bold=True
            ))
            
            content.add_widget(Label(
                text=f"Size: {trip_cache.get('size', 0)} / {trip_cache.get('capacity', 0)} items",
                size_hint_y=None,
                height=dp(25),
                halign='left',
                text_size=(400, None)
            ))
            
            content.add_widget(Label(
                text=f"Utilization: {trip_cache.get('utilization', 0) * 100:.1f}%",
                size_hint_y=None,
                height=dp(25),
                halign='left',
                text_size=(400, None)
            ))
            
            if "oldest_item_age" in trip_cache:
                content.add_widget(Label(
                    text=f"Oldest item age: {trip_cache['oldest_item_age']:.1f} seconds",
                    size_hint_y=None,
                    height=dp(25),
                    halign='left',
                    text_size=(400, None)
                ))
            
            # Location cache stats
            location_cache = stats.get("location_cache", {})
            content.add_widget(Label(
                text="Location Cache Statistics:",
                size_hint_y=None,
                height=dp(30),
                halign='left',
                text_size=(400, None),
                bold=True
            ))
            
            content.add_widget(Label(
                text=f"Size: {location_cache.get('size', 0)} / {location_cache.get('capacity', 0)} items",
                size_hint_y=None,
                height=dp(25),
                halign='left',
                text_size=(400, None)
            ))
            
            content.add_widget(Label(
                text=f"Utilization: {location_cache.get('utilization', 0) * 100:.1f}%",
                size_hint_y=None,
                height=dp(25),
                halign='left',
                text_size=(400, None)
            ))
            
            if "oldest_item_age" in location_cache:
                content.add_widget(Label(
                    text=f"Oldest item age: {location_cache['oldest_item_age']:.1f} seconds",
                    size_hint_y=None,
                    height=dp(25),
                    halign='left',
                    text_size=(400, None)
                ))
            
            # Cache actions
            action_layout = BoxLayout(
                size_hint_y=None,
                height=dp(50),
                spacing=dp(10)
            )
            
            clear_cache_btn = Button(text="Clear Caches")
            clear_cache_btn.bind(on_press=lambda x: self._clear_caches())
            
            close_btn = Button(text="Close")
            
            action_layout.add_widget(clear_cache_btn)
            action_layout.add_widget(close_btn)
            content.add_widget(action_layout)
            
            # Create popup
            popup = Popup(
                title="Cache Statistics",
                content=content,
                size_hint=(0.8, 0.7)
            )
            
            close_btn.bind(on_press=popup.dismiss)
            popup.open()
            
        except Exception as e:
            self._show_error("Error", f"Failed to get cache statistics: {str(e)}")
    
    def _clear_caches(self):
        """Clear all caches and show confirmation."""
        try:
            self.model.clear_caches()
            self._show_info("Caches Cleared", "All caches have been cleared successfully.")
        except Exception as e:
            self._show_error("Error", f"Failed to clear caches: {str(e)}")
    
    def _show_error(self, title: str, message: str):
        """Show an error popup."""
        content = BoxLayout(orientation='vertical', padding=dp(10))
        content.add_widget(Label(text=message))
        
        button = Button(
            text='OK',
            size_hint=(1, None),
            height=dp(50)
        )
        content.add_widget(button)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4)
        )
        
        button.bind(on_press=popup.dismiss)
        popup.open()
    
    def _show_info(self, title: str, message: str):
        """Show an information popup."""
        content = BoxLayout(orientation='vertical', padding=dp(10))
        content.add_widget(Label(text=message))
        
        button = Button(
            text='OK',
            size_hint=(1, None),
            height=dp(50)
        )
        content.add_widget(button)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4)
        )
        
        button.bind(on_press=popup.dismiss)
        popup.open()


class TripPlannerApp(App):
    def build(self):
        # Create view with placeholder callbacks
        view = TripPlannerView(
            on_add_trip=lambda x: None,
            on_edit_trip=lambda x: None,
            on_delete_trip=lambda x: None,
            on_show_details=lambda x: None,
            on_optimize_route=lambda x: None
        )
        
        # Create model and controller
        model = TripModel('trips.db')
        controller = TripController(model, view)
        
        return view


if __name__ == '__main__':
    TripPlannerApp().run() 
