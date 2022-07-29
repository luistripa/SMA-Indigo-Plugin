

class Inverter:
    def __init__(self, device):
        self.device = device
        self.states = dict()

    def update_states(self, states):
        self.states = states

    def get_value_for_state(self, state_name):
        return self.states.get(state_name, None)


class Aggregation(object):
    def __init__(self, device):
        self.device = device
        self.value = 0

    def get_value(self):
        return self.value

    def calculate_value(self):
        raise NotImplementedError


class InverterListAggregation(Aggregation):
    def __init__(self, device, inverter_list, state, operation):
        super(InverterListAggregation, self).__init__(device)
        self.inverter_list = inverter_list
        self.state = state
        self.operation = operation

    def calculate_value(self):
        value = 0
        for inverter in self.inverter_list:
            value += inverter.get_value_for_state(self.state)

        if self.operation == "sum":
            self.value = value
        else:
            self.value = value / len(self.inverter_list)


class AggregationListAggregation(Aggregation):
    def __init__(self, device, aggregation_list, operation):
        super(AggregationListAggregation, self).__init__(device)
        self.aggregation_list = aggregation_list
        self.operation = operation

    def calculate_value(self):
        value = 0
        for aggregation in self.aggregation_list:
            value += aggregation.get_value()

        if self.operation == "sum":
            self.value = value
        else:
            self.value = value / len(self.aggregation_list)


class InverterToInverterAggregation(Aggregation):
    def __init__(self, device, inverter1, inverter1_state, inverter2, inverter2_state, operation):
        super(InverterToInverterAggregation, self).__init__(device)
        self.inverter1 = inverter1
        self.inverter1_state = inverter1_state
        self.inverter2 = inverter2
        self.inverter2_state = inverter2_state
        self.operation = operation

    def calculate_value(self):
        if self.operation == "sum":
            self.value = self.inverter1.get_value_for_state(self.inverter1_state) + \
                         self.inverter2.get_value_for_state(self.inverter2_state)
        elif self.operation == "subtraction":
            self.value = self.inverter1.get_value_for_state(self.inverter1_state) - \
                         self.inverter2.get_value_for_state(self.inverter2_state)
        elif self.operation == "division":
            self.value = self.inverter1.get_value_for_state(self.inverter1_state) / \
                         self.inverter2.get_value_for_state(self.inverter2_state)
        elif self.operation == "multiplication":
            self.value = self.inverter1.get_value_for_state(self.inverter1_state) * \
                         self.inverter2.get_value_for_state(self.inverter2_state)
        elif self.operation == "average":
            self.value = (self.inverter1.get_value_for_state(self.inverter1_state) +
                          self.inverter2.get_value_for_state(self.inverter2_state)) / 2
        elif self.operation == "min":
            self.value = min(self.inverter1.get_value_for_state(self.inverter1_state),
                             self.inverter2.get_value_for_state(self.inverter2_state))
        elif self.operation == "max":
            self.value = max(self.inverter1.get_value_for_state(self.inverter1_state),
                             self.inverter2.get_value_for_state(self.inverter2_state))


class AggregationToAggregationAggregation(Aggregation):
    def __init__(self, device, aggregation1, aggregation2, operation):
        super(AggregationToAggregationAggregation, self).__init__(device)
        self.aggregation1 = aggregation1
        self.aggregation2 = aggregation2
        self.operation = operation

    def calculate_value(self):
        if self.operation == "sum":
            self.value = self.aggregation1.get_value() + self.aggregation2.get_value()
        elif self.operation == "subtraction":
            self.value = self.aggregation1.get_value() - self.aggregation2.get_value()
        elif self.operation == "division":
            self.value = self.aggregation1.get_value() / self.aggregation2.get_value()
        elif self.operation == "multiplication":
            self.value = self.aggregation1.get_value() * self.aggregation2.get_value()
        elif self.operation == "average":
            self.value = (self.aggregation1.get_value() + self.aggregation2.get_value()) / 2
        elif self.operation == "min":
            self.value = min(self.aggregation1.get_value(), self.aggregation2.get_value())
        elif self.operation == "max":
            self.value = max(self.aggregation1.get_value(), self.aggregation2.get_value())
