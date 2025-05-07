from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
import sqlite3

class TripPlannerApp(App):
    def build(self):
        # Initialize database
        self.conn = sqlite3.connect('trips.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trips 
                             (id INTEGER PRIMARY KEY, destination TEXT)''')
        self.conn.commit()

        # Create main layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Add destination input
        self.destination_input = TextInput(
            hint_text='Enter destination',
            multiline=False,
            size_hint_y=None,
            height=40
        )
        layout.add_widget(self.destination_input)
        
        # Add trip button
        add_button = Button(
            text='Add Trip',
            size_hint_y=None,
            height=50
        )
        add_button.bind(on_press=self.add_trip)
        layout.add_widget(add_button)
        
        # Add trip list
        self.trip_list = Label(text='Trips:')
        layout.add_widget(self.trip_list)
        
        # Load existing trips
        self.load_trips()
        
        return layout

    def add_trip(self, instance):
        destination = self.destination_input.text
        if destination:
            self.cursor.execute(
                "INSERT INTO trips (destination) VALUES (?)",
                (destination,)
            )
            self.conn.commit()
            self.destination_input.text = ''
            self.load_trips()

    def load_trips(self):
        self.cursor.execute("SELECT destination FROM trips")
        trips = self.cursor.fetchall()
        trip_text = "Trips:\n" + "\n".join(trip[0] for trip in trips)
        self.trip_list.text = trip_text

    def on_stop(self):
        self.conn.close()

if __name__ == '__main__':
    TripPlannerApp().run() 