from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from typing import Callable, List
from model import Trip

class TripItem(BoxLayout):
    def __init__(self, trip: Trip, on_edit: Callable[[Trip], None], on_delete: Callable[[Trip], None], **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)

        # Trip info
        info_layout = BoxLayout(orientation='vertical')
        info_layout.add_widget(Label(
            text=trip.destination,
            size_hint_y=None,
            height=dp(25)
        ))
        info_layout.add_widget(Label(
            text=f"Created: {trip.created_at.strftime('%Y-%m-%d %H:%M')}",
            size_hint_y=None,
            height=dp(20),
            font_size='12sp'
        ))
        self.add_widget(info_layout)

        # Buttons
        button_layout = BoxLayout(size_hint_x=None, width=dp(100), spacing=dp(5))
        
        edit_btn = Button(
            text='Edit',
            size_hint_x=None,
            width=dp(45)
        )
        edit_btn.bind(on_press=lambda x: on_edit(trip))
        
        delete_btn = Button(
            text='Delete',
            size_hint_x=None,
            width=dp(45)
        )
        delete_btn.bind(on_press=lambda x: on_delete(trip))
        
        button_layout.add_widget(edit_btn)
        button_layout.add_widget(delete_btn)
        self.add_widget(button_layout)

class TripPlannerView(BoxLayout):
    def __init__(self, on_add_trip: Callable[[str], None], on_edit_trip: Callable[[Trip, str], None],
                 on_delete_trip: Callable[[Trip], None], **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.padding = dp(10)
        self.spacing = dp(10)

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
        add_button.bind(on_press=lambda x: self._handle_add_trip(on_add_trip))
        
        input_layout.add_widget(self.destination_input)
        input_layout.add_widget(add_button)
        self.add_widget(input_layout)

        # Trip list
        scroll_view = ScrollView()
        self.trip_list = GridLayout(
            cols=1,
            spacing=dp(5),
            size_hint_y=None
        )
        self.trip_list.bind(minimum_height=self.trip_list.setter('height'))
        scroll_view.add_widget(self.trip_list)
        self.add_widget(scroll_view)

        # Store callbacks
        self.on_add_trip = on_add_trip
        self.on_edit_trip = on_edit_trip
        self.on_delete_trip = on_delete_trip

    def _handle_add_trip(self, callback: Callable[[str], None]):
        destination = self.destination_input.text.strip()
        if destination:
            callback(destination)
            self.destination_input.text = ''

    def update_trip_list(self, trips: List[Trip]):
        self.trip_list.clear_widgets()
        for trip in trips:
            trip_item = TripItem(
                trip=trip,
                on_edit=self.on_edit_trip,
                on_delete=self.on_delete_trip
            )
            self.trip_list.add_widget(trip_item) 