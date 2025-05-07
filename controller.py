from typing import List, Optional
from model import TripModel, Trip, DatabaseError
from view import TripPlannerView
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.metrics import dp

class TripController:
    def __init__(self, model: TripModel, view: TripPlannerView):
        self.model = model
        self.view = view
        self._load_trips()

    def _load_trips(self):
        try:
            trips = self.model.get_all_trips()
            self.view.update_trip_list(trips)
        except DatabaseError as e:
            self._show_error("Failed to load trips", str(e))

    def add_trip(self, destination: str):
        try:
            self.model.add_trip(destination)
            self._load_trips()
        except DatabaseError as e:
            self._show_error("Failed to add trip", str(e))

    def edit_trip(self, trip: Trip):
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
        try:
            if self.model.delete_trip(trip.id):
                self._load_trips()
        except DatabaseError as e:
            self._show_error("Failed to delete trip", str(e))

    def _show_error(self, title: str, message: str):
        content = BoxLayout(orientation='vertical', padding=dp(10))
        content.add_widget(Button(
            text=message,
            size_hint_y=None,
            height=dp(40)
        ))
        content.add_widget(Button(
            text='OK',
            size_hint_y=None,
            height=dp(40)
        ))
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4)
        )
        content.children[0].bind(on_press=popup.dismiss)
        popup.open()

class TripPlannerApp(App):
    def build(self):
        model = TripModel('trips.db')
        view = TripPlannerView(
            on_add_trip=lambda x: None,  # Will be set by controller
            on_edit_trip=lambda x, y: None,  # Will be set by controller
            on_delete_trip=lambda x: None  # Will be set by controller
        )
        controller = TripController(model, view)
        
        # Set callbacks
        view.on_add_trip = controller.add_trip
        view.on_edit_trip = controller.edit_trip
        view.on_delete_trip = controller.delete_trip
        
        return view 