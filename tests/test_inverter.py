import unittest

from objects import Inverter


class TestInverter(unittest.TestCase):
    def test_create(self):
        inverter = Inverter(dict())

        self.assertEqual(len(inverter.states), 0)
        self.assertEqual(len(inverter.device), 0)

    def test_update_states(self):
        inverter = Inverter(dict())
        inverter.update_states({"state1": 2, "state2": "test", "state3": 25.3})

        self.assertEqual(inverter.states.get("state1", None), 2)
        self.assertEqual(inverter.states.get("state2", None), "test")
        self.assertEqual(inverter.states.get("state3", None), 25.3)
        self.assertIsNone(inverter.states.get("state4", None))

    def test_get_value_for_state(self):
        inverter = Inverter(dict())
        inverter.update_states({"state1": "test", "state2": 6.3, "state3": -23})

        self.assertEqual(inverter.get_value_for_state("state1"), "test")
        self.assertEqual(inverter.get_value_for_state("state2"), 6.3)
        self.assertEqual(inverter.get_value_for_state("state3"), -23)
        self.assertIsNone(inverter.get_value_for_state("state4"))
