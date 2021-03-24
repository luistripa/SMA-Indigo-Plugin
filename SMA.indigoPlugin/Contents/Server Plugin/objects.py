from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from comms import Client


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

    def update_states(self):
        indigo_states = []
        self.states = self.client.generate_states()
        for state, value in self.states:
            indigo_states.append({'key': state, 'value': value})
        self.device.updateStatesOnServer(indigo_states)


class InverterBundle:
    def __init__(self, device):
        self.device = device
        self.inverters = list()

    def add_inverter(self, inverter: Inverter):
        self.inverters.append(inverter)

    def remove_inverter(self, inverter: Inverter):
        if self.inverters.__contains__(inverter):
            self.inverters.remove(inverter)

    def update_all_states(self):
        """
        Updates all bundle states.
        """
        pass

    def get_count(self) -> int:
        return len(self.inverters)

    def reconnect(self):
        for inverter in self.inverters:
            inverter.disconnect()
            inverter.connect()
