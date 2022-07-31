import indigo


class IndigoService:
    @staticmethod
    def update_inverter_states(device_id, states):
        """
        Updates inverter states on the indigo server
        """
        indigo_states = []
        for state_name, state_value in states.items():
            indigo_states.append({'key': state_name, 'value': state_value})
        indigo.devices[device_id].updateStatesOnServer(indigo_states)

    @staticmethod
    def update_aggregation_states(aggregation):
        """
        Updates aggregation states on the indigo server
        """
        aggregation.device.updateStateOnServer(key='value', value=aggregation.value)