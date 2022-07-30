
from comms import Client


class ModBusService:
    def __init__(self):
        """
        Key is device id
        Value is Inverter object
        """
        self.clients = dict()

    def register_inverter(self, host, port, inverter):
        """
        Registers a new inverter into the ModBus Service.
        This function also establishes a connection to the inverter.
        @returns True if connection succeeds, False otherwise
        """
        client = Client(host, port)
        self.clients[inverter.device.id] = client
        return client.connect()

    def get_inverter_states(self, inverter):
        """
        Gets the inverter states using the modbus connection.
        @returns dict object with all the states and respective values
        """
        client = self.clients[inverter.device.id]
        states = client.generate_states()
        inverter.update_states(states)

    def reconnect_inverter(self, inverter):
        client = self.clients[inverter.device.id]
        client.close()
        return client.connect()

    def disconnect_inverter(self, inverter):
        client = self.clients[inverter.device.id]
        client.close()


class IndigoService:
    @staticmethod
    def update_inverter_states(inverter):
        """
        Updates inverter states on the indigo server
        """
        indigo_states = []
        for state_name, state_value in inverter.states:
            indigo_states.append({'key': state_name, 'value': state_value})
        inverter.device.updateStatesOnServer(indigo_states)

    @staticmethod
    def update_aggregation_states(aggregation):
        """
        Updates aggregation states on the indigo server
        """
        aggregation.device.updateStateOnServer(key='value', value=aggregation.value)