import unittest

from objects import Inverter, InverterToInverterAggregation


class TestInverterToInverterAggregation(unittest.TestCase):
    def setUp(self):
        self.inverter1 = Inverter(dict())
        self.inverter2 = Inverter(dict())

        self.inverter1.update_states({"state1": "test1", "state2": 5})
        self.inverter2.update_states({"state1": "test2", "state2": 15})

    def test_create_sum(self):
        aggregation = InverterToInverterAggregation(dict(), self.inverter1, "state2", self.inverter2, "state2", "sum")

        self.assertEqual(len(aggregation.device), 0)
        self.assertEqual(aggregation.inverter1, self.inverter1)
        self.assertEqual(aggregation.inverter2, self.inverter2)
        self.assertEqual(aggregation.inverter1_state, "state2")
        self.assertEqual(aggregation.inverter2_state, "state2")
        self.assertEqual(aggregation.operation, "sum")
        self.assertEqual(aggregation.value, 0)

    def test_create_average(self):
        aggregation = InverterToInverterAggregation(dict(), self.inverter1, "state2", self.inverter2, "state2", "average")

        self.assertEqual(len(aggregation.device), 0)
        self.assertEqual(aggregation.inverter1, self.inverter1)
        self.assertEqual(aggregation.inverter2, self.inverter2)
        self.assertEqual(aggregation.inverter1_state, "state2")
        self.assertEqual(aggregation.inverter2_state, "state2")
        self.assertEqual(aggregation.operation, "average")
        self.assertEqual(aggregation.value, 0)

    def test_calculate_value_sum(self):
        aggregation = InverterToInverterAggregation(dict(), self.inverter1, "state2", self.inverter2, "state2", "sum")

        aggregation.calculate_value()
        self.assertEqual(aggregation.value, 20)
        aggregation.calculate_value()
        self.assertEqual(aggregation.value, 20)

    def test_calculate_value_average(self):
        aggregation = InverterToInverterAggregation(dict(), self.inverter1, "state2", self.inverter2, "state2",
                                                    "average")

        aggregation.calculate_value()
        self.assertEqual(aggregation.value, 10)
        aggregation.calculate_value()
        self.assertEqual(aggregation.value, 10)

    def test_get_value_sum(self):
        aggregation = InverterToInverterAggregation(dict(), self.inverter1, "state2", self.inverter2, "state2", "sum")

        aggregation.calculate_value()
        self.assertEqual(aggregation.get_value(), 20)
        aggregation.calculate_value()
        self.assertEqual(aggregation.get_value(), 20)

    def test_get_value_average(self):
        aggregation = InverterToInverterAggregation(dict(), self.inverter1, "state2", self.inverter2, "state2",
                                                    "average")

        aggregation.calculate_value()
        self.assertEqual(aggregation.get_value(), 10)
        aggregation.calculate_value()
        self.assertEqual(aggregation.get_value(), 10)
