from typing import List, Dict, Union
from pymodbus.client.sync import ModbusTcpClient as ModbusClient


class Inverter:
    def __init__(self, device, host, port):
        self.device = device
        self.host = host
        self.port = port
        self.client = ModbusClient(host=self.host, port=self.port)
        self.states: Dict[str, Union[str, int]] = dict()

    def connect(self) -> bool:
        return self.client.connect()

    def disconnect(self):
        self.client.close()

    def update_state(self, key, value):
        self.states[key] = value

    def update_states_on_server(self):
        states = []
        for key, value in self.states.keys(), self.states.values():
            states.append({'key': key, 'value': value})
        self.device.updateStatesOnServer()


class InverterBundle:
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
        pass

    def get_count(self) -> int:
        return len(self.inverters)

    def reconnect(self):
        for inverter in self.inverters:
            inverter.disconnect()
            inverter.connect()
