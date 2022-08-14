"""Displays bluetooth status with icons. Left mouse click launches manager app `blueman-manager`.
Needs python-dbus to detect device types and nerd fonts to display the icons

Parameters:
    * bluetooth.manager : application to launch on click (blueman-manager)

Adapted by `Diego <https://github.com/diesphink>`_ from bluetooth2 by `martindoublem <https://github.com/martindoublem>`_
"""


import re
import dbus
import dbus.mainloop.glib

import core.module
import core.widget
import core.input


class Module(core.module.Module):
    def __init__(self, config, theme):
        super().__init__(config, theme, core.widget.Widget(self.status))

        self.manager = self.parameter("manager", "blueman-manager")
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SystemBus()

        core.input.register(
            self, button=core.input.LEFT_MOUSE, cmd=self.manager)

        self._icons = {
            'audio-headset': '',
            'input-mouse': '',
            'keyboard': '',
            'input-keyboard': '',
            'unknown': ''
        }

    def status(self, widget):
        """Get status."""
        return self._status

    def update(self):
        """Update current state."""
        devices = self.get_connected_devices()
        if devices:
            self._status = " ".join([self._icons[dev['icon']]
                                    for dev in devices])
        else:
            self._status = None
        return

    def state(self, widget):
        """Get current state."""
        return ["ON"]

    def hidden(self):
        return self._status is None

    def get_connected_devices(self):
        devices = []

        objects = dbus.Interface(self._bus.get_object(
            "org.bluez", "/"), "org.freedesktop.DBus.ObjectManager").GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:

                props = dbus.Interface(self._bus.get_object(
                    "org.bluez", path), "org.freedesktop.DBus.Properties").GetAll("org.bluez.Device1")

                if props['Connected'] == 1:
                    device = {'Name': props['Name']}
                    if 'Icon' in props:
                        device['icon'] = props['Icon']
                    elif re.search('keyboard', props['Name'], flags=re.IGNORECASE):
                        device['icon'] = 'keyboard'
                    else:
                        device['icon'] = 'unknown'
                    devices.append(device)
        return devices

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4