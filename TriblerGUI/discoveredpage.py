from PyQt5.QtWidgets import QWidget

from TriblerGUI.channel_list_item import ChannelListItem
from TriblerGUI.tribler_request_manager import TriblerRequestManager


class DiscoveredPage(QWidget):

    def initialize_discovered_page(self):
        self.discovered_channels = []
        self.window().core_manager.events_manager.discovered_channel.connect(self.on_discovered_channel)

    def load_discovered_channels(self):
        self.request_mgr = TriblerRequestManager()
        self.request_mgr.perform_request("channels/discovered", self.received_discovered_channels)

    def received_discovered_channels(self, results):
        self.discovered_channels = []
        self.window().discovered_channels_list.set_data_items([])
        items = []

        for result in results['channels']:
            items.append((ChannelListItem, result))
            self.discovered_channels.append(result)
            self.update_num_label()
        self.window().discovered_channels_list.set_data_items(items)

    def on_discovered_channel(self, channel_info):
        channel_info['torrents'] = 0
        channel_info['subscribed'] = False
        channel_info['votes'] = 0
        self.window().discovered_channels_list.insert_item(0, (ChannelListItem, channel_info))
        self.discovered_channels.append(channel_info)
        self.update_num_label()

    def update_num_label(self):
        self.window().num_discovered_channels_label.setText("%d items" % len(self.discovered_channels))