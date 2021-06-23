from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from comms import Client

from typing import List
import socket
from struct import pack
from binascii import b2a_hex


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


class HomeManager:
    """
    Home Manager support is being discontinued by this plugin. The values that are output are not correct and should
    not be used.
    """

    def __init__(self, device):
        self.device = device
        self.mcastGroup = device.pluginProps['multicastGroup']
        self.mcastPort = int(device.pluginProps['multicastPort'])
        self.setup()

    def hex2dec(self, s):
        return int(s, 16)

    def setup(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.mcastPort))
        mreq = pack("4sl", socket.inet_aton(self.mcastGroup), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def getReading(self):
        info = self.sock.recv(600)
        info_ascii = b2a_hex(info)
        powerFromGrid = self.hex2dec(info_ascii[64:72]) / 10
        totalPowerFromGrid = self.hex2dec(info_ascii[80:96]) / 3600000
        powerToGrid = self.hex2dec(info_ascii[104:112]) / 10
        totalPowerToGrid = self.hex2dec(info_ascii[120:136]) / 3600000
        return [{'key': 'powerFromGrid', 'value': powerFromGrid},
                {'key': 'totalPowerFromGrid', 'value': totalPowerFromGrid},
                {'key': 'powerToGrid', 'value': powerToGrid},
                {'key': 'totalPowerToGrid', 'value': totalPowerToGrid}]

    def close(self):
        self.sock.close()