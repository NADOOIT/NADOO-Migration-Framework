"""Token dialog for PyPI token input."""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import webbrowser
from typing import Optional
import asyncio

PYPI_TOKEN_URL = "https://pypi.org/manage/account/token/"


class TokenDialog(toga.App):
    def __init__(self):
        super().__init__('PyPI Token Input', 'org.nadoo.token_dialog')
        self.token_value = None

    def startup(self):
        """Build and show the token input dialog."""
        # Create main window
        self.main_window = toga.MainWindow(title='PyPI Token Input', size=(400, 200))

        # Create token input
        self.token_input = toga.PasswordInput(style=Pack(flex=1))

        # Create buttons
        get_token_button = toga.Button(
            'Get New Token', on_press=self.open_token_page, style=Pack(padding=5)
        )
        submit_button = toga.Button('Submit', on_press=self.submit_token, style=Pack(padding=5))
        cancel_button = toga.Button('Cancel', on_press=self.cancel_dialog, style=Pack(padding=5))

        # Create button box
        button_box = toga.Box(
            children=[get_token_button, submit_button, cancel_button],
            style=Pack(direction=ROW, padding=5),
        )

        # Create instructions
        self.message_label = toga.Label(
            'Please enter your PyPI token.\nYou can create a new token by clicking "Get New Token".',
            style=Pack(padding=(0, 5)),
        )

        # Create main box
        self.main_box = toga.Box(
            children=[self.message_label, self.token_input, button_box],
            style=Pack(direction=COLUMN, padding=10, alignment='center', flex=1),
        )

        # Add the content to the main window
        self.main_window.content = self.main_box
        self.main_window.show()

    def open_token_page(self, widget):
        """Open PyPI token creation page in browser."""
        webbrowser.open(PYPI_TOKEN_URL)

    async def delayed_close(self):
        """Close the window after a delay."""
        await asyncio.sleep(1.5)
        self.main_window.close()

    def show_success_and_close(self):
        """Show success message and close after delay."""
        self.message_label.text = ' Token accepted! Window will close shortly...'
        self.message_label.style.update(color='green')
        self.token_input.enabled = False

        # Create and schedule the delayed close task
        asyncio.create_task(self.delayed_close())

    def submit_token(self, widget):
        """Submit the token and close the dialog."""
        if self.token_input.value:
            self.token_value = self.token_input.value
            # Show success message and close after delay
            self.show_success_and_close()
        else:
            self.message_label.text = ' Please enter a token'
            self.message_label.style.update(color='red')

    def cancel_dialog(self, widget):
        """Cancel the dialog."""
        self.token_value = None
        self.main_window.close()


def get_token_via_dialog() -> Optional[str]:
    """Show token input dialog and return the entered token."""
    app = TokenDialog()
    app.main_loop()
    return app.token_value
