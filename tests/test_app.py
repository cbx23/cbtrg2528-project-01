import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_demo_and_parameters(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.metric[0].value, '5')
        app.sidebar.slider[0].set_value(99.0).run()
        self.assertFalse(app.exception)
        app.sidebar.number_input[0].set_value(96).run()
        self.assertEqual(len(app.error), 1)
        app.sidebar.number_input[0].set_value(80).run()
        app.sidebar.checkbox[0].uncheck().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.info), 1)
