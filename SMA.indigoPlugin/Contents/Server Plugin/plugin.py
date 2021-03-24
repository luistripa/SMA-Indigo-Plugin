import indigo
import socket
from struct import pack
from binascii import b2a_hex

from objects import Inverter, InverterBundle
import traceback

DISPLAY_NAME = 'Energy Meter'


class Plugin(indigo.PluginBase):
    class HomeManager:
        """
        Output values are not correct
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

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        """
        Stores all bundles. A bundle is a group of devices. Each bundle is a specific device that stores the average
        and total values of all inverters in the bundle.
        """
        self.bundles = dict()

        """
        Stores all Inverter objects in the system.
        """
        self.inverters = dict()

        """
        Stores all HomeManager objects in the system
        """
        self.homeManagers = dict()

    def startup(self):
        pass

    def shutdown(self):
        # Close connection to all inverters
        for inv in self.inverters.values():
            inv.client.close()
        for hm in self.homeManagers.values():
            hm.close()

    def runConcurrentThread(self):
        try:
            while True:
                self.update_inverters()
                self.update_inverter_bundles()
                self.update_home_managers()
                self.sleep(10)

        except self.StopThread:
            self.shutdown()

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            pass

    def deviceStartComm(self, dev):
        props = dev.pluginProps

        if dev.deviceTypeId == 'solarInverter':
            inverter = Inverter(dev, props['inverterAddress'], int(props['inverterPort']))

            if inverter.connect():
                self.inverters[dev.name] = inverter
                indigo.server.log('Started communication with inverter device: {}'.format(inverter.device.name),
                                  type=DISPLAY_NAME)
            else:
                indigo.server.log('Failed to establish connection to inverter: {}'.format(inverter.device.name),
                                  type=DISPLAY_NAME)

        elif dev.deviceTypeId == 'inverterBundle':
            bundle = InverterBundle(dev)
            for inverterId in props['inverterList']:
                inverter = indigo.devices[inverterId]
                bundle.add_inverter(inverter)
            self.bundles[dev.name] = bundle

        elif dev.deviceTypeId == 'homeManager':
            home_manager = self.HomeManager(dev)
            self.homeManagers[dev.name] = home_manager

        else:
            indigo.server.log('Unknown device type id.', type=DISPLAY_NAME)

    def deviceStopComm(self, dev):
        if dev.deviceTypeId == 'solarInverter' and dev.name in self.inverters.keys():
            self.inverters[dev.name].disconnect()
            del self.inverters[dev.name]

        elif dev.deviceTypeId == 'homeManager' and dev in self.homeManagers.keys():
            self.homeManagers[dev.name].close()
            del self.homeManagers[dev.name]

    ###########################

    def update_inverters(self):
        for inv in self.inverters.values():
            try:
                inv.update_states()

            except ConnectionError:
                indigo.server.log('Lost connection to inverter: {}. Reconnecting...'.format(inv.device.name),
                                  type=DISPLAY_NAME)
                inv.disconnect()
                inv.connect()  # Reconnect inverter

    def update_inverter_bundles(self):
        for bundle in self.bundles.values():
            bundle.update_all_states()

    def update_home_managers(self):
        for hm in self.homeManagers.values():
            try:
                states = hm.getReading()
                hm.device.updateStatesOnServer(states)
            except Exception as e:
                indigo.server.log(traceback.print_exc(), type=DISPLAY_NAME)

    def reconnect_all(self):
        indigo.server.log('Reconnecting all devices........%d devices' % len(self.devices))
        for inv in self.inverters.values():
            if inv.connect():
                indigo.server.log('    - {} --- OK'.format(inv.device.name), type=DISPLAY_NAME)
            else:
                indigo.server.log('    - {} --- FAILED'.format(inv.device.name), type=DISPLAY_NAME)

    def reconnect_device(self, valuesDict, typeId):
        indigo.server.log('Not yet implemented', type=DISPLAY_NAME)

    def reconnect_bundle(self, valuesDict, typeId):
        bundle = indigo.devices[valuesDict['targetBundle']]
        bundle.reconnectAll()
