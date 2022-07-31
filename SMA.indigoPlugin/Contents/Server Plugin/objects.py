import indigo


class Dependency(object):
    def __init__(self):
        self._dependencies = list()
        self._dependants = list()

    def add_dependency(self, dependency):
        self._dependencies.append(dependency)

    def add_dependant(self, dependant):
        self._dependants.append(dependant)

    def get_dependencies(self):
        return self._dependencies

    def get_dependants(self):
        return self._dependants


class Inverter(Dependency):
    def __init__(self, device):
        super(Inverter, self).__init__()
        self.device = device
        self.states = dict()

    def update_states(self, states):
        self.states = states

    def get_value_for_state(self, state_name):
        return self.states.get(state_name, None)


class Aggregation(Dependency):
    def __init__(self, device):
        super(Aggregation, self).__init__()
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
        for inverter_id in self.inverter_list:
            inverter = indigo.devices[int(inverter_id)]
            value += inverter.states[self.state]

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
        for aggregation_id in self.aggregation_list:
            value += indigo.devices[int(aggregation_id)].states['value']

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
            self.value = indigo.devices[self.inverter1].states[self.inverter1_state] + \
                         indigo.devices[self.inverter2].states[self.inverter2_state]
        elif self.operation == "subtraction":
            self.value = indigo.devices[self.inverter1].states[self.inverter1_state] - \
                         indigo.devices[self.inverter2].states[self.inverter2_state]
        elif self.operation == "division":
            try:
                self.value = indigo.devices[self.inverter1].states[self.inverter1_state] / \
                             indigo.devices[self.inverter2].states[self.inverter2_state]
            except ZeroDivisionError:
                self.value = 0
        elif self.operation == "multiplication":
            self.value = indigo.devices[self.inverter1].states[self.inverter1_state] * \
                         indigo.devices[self.inverter2].states[self.inverter2_state]
        elif self.operation == "average":
            self.value = (indigo.devices[self.inverter1].states[self.inverter1_state] +
                          indigo.devices[self.inverter2].states[self.inverter2_state]) / 2
        elif self.operation == "min":
            self.value = min(indigo.devices[self.inverter1].states[self.inverter1_state],
                             indigo.devices[self.inverter2].states[self.inverter2_state])
        elif self.operation == "max":
            self.value = max(indigo.devices[self.inverter1].states[self.inverter1_state],
                             indigo.devices[self.inverter2].states[self.inverter2_state])


class AggregationToAggregationAggregation(Aggregation):
    def __init__(self, device, aggregation1, aggregation2, operation):
        super(AggregationToAggregationAggregation, self).__init__(device)
        self.aggregation1 = aggregation1
        self.aggregation2 = aggregation2
        self.operation = operation

    def calculate_value(self):
        if self.operation == "sum":
            self.value = indigo.devices[self.aggregation1].states['value'] + \
                         indigo.devices[self.aggregation2].states['value']
        elif self.operation == "subtraction":
            self.value = indigo.devices[self.aggregation1].states['value'] - \
                         indigo.devices[self.aggregation2].states['value']
        elif self.operation == "division":
            try:
                self.value = indigo.devices[self.aggregation1].states['value'] / \
                             indigo.devices[self.aggregation2].states['value']
            except ZeroDivisionError:
                self.value = 0
        elif self.operation == "multiplication":
            self.value = indigo.devices[self.aggregation1].states['value'] * \
                         indigo.devices[self.aggregation2].states['value']
        elif self.operation == "average":
            self.value = (indigo.devices[self.aggregation1].states['value'] +
                          indigo.devices[self.aggregation2].states['value']) / 2
        elif self.operation == "min":
            self.value = min(indigo.devices[self.aggregation1].states['value'],
                             indigo.devices[self.aggregation2].states['value'])
        elif self.operation == "max":
            self.value = max(indigo.devices[self.aggregation1].states['value'],
                             indigo.devices[self.aggregation2].states['value'])


class AggregationToInverterAggregation(Aggregation):
    def __init__(self, device, aggregation, inverter, inverter_state, operation):
        super(AggregationToInverterAggregation, self).__init__(device)
        self.aggregation = aggregation
        self.inverter = inverter
        self.inverter_state = inverter_state
        self.operation = operation

    def calculate_value(self):
        if self.operation == "sum":
            self.value = indigo.devices[self.aggregation].states['value'] + \
                         indigo.devices[self.inverter].states[self.inverter_state]
        elif self.operation == "subtraction":
            self.value = indigo.devices[self.aggregation].states['value'] - \
                         indigo.devices[self.inverter].states[self.inverter_state]
        elif self.operation == "division":
            try:
                self.value = indigo.devices[self.aggregation].states['value'] / \
                             indigo.devices[self.inverter].states[self.inverter_state]
            except ZeroDivisionError:
                self.value = 0
        elif self.operation == "multiplication":
            self.value = indigo.devices[self.aggregation].states['value'] * \
                         indigo.devices[self.inverter].states[self.inverter_state]
        elif self.operation == "average":
            self.value = (indigo.devices[self.aggregation].states['value'] +
                          indigo.devices[self.inverter].states[self.inverter_state]) / 2
        elif self.operation == "min":
            self.value = min(indigo.devices[self.aggregation].states['value'],
                             indigo.devices[self.inverter].states[self.inverter_state])
        elif self.operation == "max":
            self.value = max(indigo.devices[self.aggregation].states['value'],
                             indigo.devices[self.inverter].states[self.inverter_state])


class InverterToAggregationAggregation(Aggregation):
    def __init__(self, device, inverter, inverter_state, aggregation, operation):
        super(InverterToAggregationAggregation, self).__init__(device)
        self.inverter = inverter
        self.inverter_state = inverter_state
        self.aggregation = aggregation
        self.operation = operation

    def calculate_value(self):
        if self.operation == "sum":
            self.value = indigo.devices[self.inverter].states[self.inverter_state] + \
                         indigo.devices[self.aggregation].states['value']
        elif self.operation == "subtraction":
            self.value = indigo.devices[self.inverter].states[self.inverter_state] - \
                         indigo.devices[self.aggregation].states['value']
        elif self.operation == "division":
            try:
                self.value = indigo.devices[self.inverter].states[self.inverter_state] / \
                             indigo.devices[self.aggregation].states['value']
            except ZeroDivisionError:
                self.value = 0
        elif self.operation == "multiplication":
            self.value = indigo.devices[self.inverter].states[self.inverter_state] * \
                         indigo.devices[self.aggregation].states['value']
        elif self.operation == "average":
            self.value = (indigo.devices[self.inverter].states[self.inverter_state] +
                          indigo.devices[self.aggregation].states['value']) / 2
        elif self.operation == "min":
            self.value = min(indigo.devices[self.inverter].states[self.inverter_state],
                             indigo.devices[self.aggregation].states['value'])
        elif self.operation == "max":
            self.value = max(indigo.devices[self.inverter].states[self.inverter_state],
                             indigo.devices[self.aggregation].states['value'])
