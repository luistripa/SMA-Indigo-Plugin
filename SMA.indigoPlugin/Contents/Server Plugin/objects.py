from comms import Client

from typing import List


class Inverter:
    def __init__(self, device, host, port):
        self.device = device
        self.host = host
        self.port = port
        self.client = Client(host, port)
        self.states = dict()

    def connect(self) -> bool:
        return self.client.connect()

    def disconnect(self):
        self.client.close()

    def reconnect(self):
        self.disconnect()
        return self.connect()

    def update_states(self):
        indigo_states = []
        self.states = self.client.generate_states()
        for state, value in self.states:
            indigo_states.append({'key': state, 'value': value})
        self.device.updateStatesOnServer(indigo_states)


class InverterBundle:
    """
    This object is not operational yet
    """
    def __init__(self, device):
        self.device = device
        self.inverters: List[Inverter] = list()

    def add_inverter(self, inverter: Inverter):
        self.inverters.append(inverter)

    def remove_inverter(self, inverter: Inverter):
        if self.inverters.__contains__(inverter):
            self.inverters.remove(inverter)

    def update_all_states(self):
        """
        Updates all bundle states.
        """
        raise NotImplementedError("Function update_all_states is not yet implemented")

    def get_count(self) -> int:
        return len(self.inverters)

    def reconnect(self):
        for inverter in self.inverters:
            inverter.disconnect()
            inverter.connect()
