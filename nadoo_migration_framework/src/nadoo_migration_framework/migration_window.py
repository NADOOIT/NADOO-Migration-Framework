import toga
from toga.style import Pack
from toga.style.pack import COLUMN

class MigrationWindow(toga.App):
    def startup(self):
        # Create a main window with a title
        self.main_window = toga.MainWindow(title='NADOO Migration Framework')

        # Create a box to hold things
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Create a label
        label = toga.Label('Welcome to the NADOO Migration Framework')

        # Add the label to the box
        box.add(label)

        # Set the content of the main window
        self.main_window.content = box

        # Show the main window
        self.main_window.show()
