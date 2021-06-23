import indigo

from objects import Inverter, InverterBundle, HomeManager
import traceback

DISPLAY_NAME = 'Energy Meter'


class Plugin(indigo.PluginBase):
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
            home_manager = HomeManager(dev)
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
        """
        Updates the states of all Inverters.
        If, for some reason, a ConnectionError is found, it attempts to reconnect the inverter
        """
        for inv in self.inverters.values():
            try:
                inv.update_states()

            except ConnectionError:
                indigo.server.log('Lost connection to inverter: {}. Reconnecting...'.format(inv.device.name),
                                  type=DISPLAY_NAME)
                inv.disconnect()
                inv.connect()  # Reconnect inverter

    def update_inverter_bundles(self):
        """
        Updates the states of all Inverter Bundles
        """
        for bundle in self.bundles.values():
            bundle.update_all_states()

    def update_home_managers(self):
        """
        Updates all Home Managers.
        Home Manager support is being discontinued by this plugin. The values that are output are not correct and should
        not be used.
        """
        for hm in self.homeManagers.values():
            try:
                states = hm.getReading()
                hm.device.updateStatesOnServer(states)
            except Exception as e:
                indigo.server.log(traceback.print_exc(), type=DISPLAY_NAME)

    def reconnect_all(self):
        """
        Reconnects all devices
        """
        indigo.server.log('Reconnecting all devices........%d devices' % len(self.devices))
        for inv in self.inverters.values():
            if inv.reconnect():
                indigo.server.log('    - {} --- OK'.format(inv.device.name), type=DISPLAY_NAME)
            else:
                indigo.server.log('    - {} --- FAILED'.format(inv.device.name), type=DISPLAY_NAME)

    def reconnect_device(self, valuesDict, typeId):
        """
        Reconnects a specific device
        """
        indigo.server.log('Reconnect Device is not yet implemented', type=DISPLAY_NAME)

    def reconnect_bundle(self, valuesDict, typeId):
        """
        Reconnects all devices in a specific bundle
        """
        bundle = indigo.devices[valuesDict['targetBundle']]
        bundle.reconnectAll()
