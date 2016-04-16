import json
import os
import sys
from PyQt5 import uic
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QMainWindow, QListView, QListWidget, QLineEdit, QListWidgetItem, QApplication, QToolButton, \
    QWidget, QLabel, QTreeWidget, QTreeWidgetItem, QProgressBar, QStackedWidget
from TriblerGUI.channel_activity_list_item import ChannelActivityListItem
from TriblerGUI.channel_comment_list_item import ChannelCommentListItem

from TriblerGUI.channel_list_item import ChannelListItem
from TriblerGUI.channel_torrent_list_item import ChannelTorrentListItem
from TriblerGUI.event_request_manager import EventRequestManager
from TriblerGUI.tribler_request_manager import TriblerRequestManager
from TriblerGUI.utilities import create_rounded_image

# TODO martijn: temporary solution to convince VLC to find the plugin path
os.environ['VLC_PLUGIN_PATH'] = '/Applications/VLC.app/Contents/MacOS/plugins'


# Define stacked widget page indices
PAGE_HOME = 0
PAGE_MY_CHANNEL = 1
PAGE_SEARCH_RESULTS = 2
PAGE_CHANNEL_DETAILS = 3
PAGE_SETTINGS = 4
PAGE_VIDEO_PLAYER = 5
PAGE_SUBSCRIBED_CHANNELS = 6
PAGE_DOWNLOADS = 7

PAGE_CHANNEL_CONTENT = 0
PAGE_CHANNEL_COMMENTS = 1
PAGE_CHANNEL_ACTIVITY = 2


LIST_BATCH_SIZE = 20


class TriblerWindow(QMainWindow):

    resize_event = pyqtSignal()

    def __init__(self):
        super(TriblerWindow, self).__init__()

        self.settings = None
        self.navigation_stack = []

        uic.loadUi('qt_resources/mainwindow.ui', self)

        # Remove the focus rect on OS X
        [widget.setAttribute(Qt.WA_MacShowFocusRect, 0) for widget in self.findChildren(QLineEdit) +
         self.findChildren(QListView) + self.findChildren(QTreeWidget)]

        self.subscribed_channels_list = self.findChild(QListWidget, "subscribed_channels_list")
        self.channel_torrents_list = self.findChild(QListWidget, "channel_torrents_list")
        self.top_menu_button = self.findChild(QToolButton, "top_menu_button")
        self.top_search_bar = self.findChild(QLineEdit, "top_search_bar")
        self.top_search_button = self.findChild(QToolButton, "top_search_button")
        self.my_profile_button = self.findChild(QToolButton, "my_profile_button")
        self.video_player_page = self.findChild(QWidget, "video_player_page")
        self.search_results_page = self.findChild(QWidget, "search_results_page")
        self.downloads_page = self.findChild(QWidget, "downloads_page")
        self.settings_page = self.findChild(QWidget, "settings_page")
        self.my_channel_page = self.findChild(QWidget, "my_channel_page")
        self.left_menu = self.findChild(QWidget, "left_menu")

        self.top_search_bar.returnPressed.connect(self.on_top_search_button_click)
        self.top_search_button.clicked.connect(self.on_top_search_button_click)
        self.top_menu_button.clicked.connect(self.on_top_menu_button_click)
        self.search_results_list.itemClicked.connect(self.on_channel_item_click)
        self.subscribed_channels_list.itemClicked.connect(self.on_channel_item_click)

        self.left_menu_home_button = self.findChild(QWidget, "left_menu_home_button")
        self.left_menu_home_button.clicked_menu_button.connect(self.clicked_menu_button)
        self.left_menu_my_channel_button = self.findChild(QWidget, "left_menu_my_channel_button")
        self.left_menu_my_channel_button.clicked_menu_button.connect(self.clicked_menu_button)
        self.left_menu_subscribed_button = self.findChild(QWidget, "left_menu_subscribed_button")
        self.left_menu_subscribed_button.clicked_menu_button.connect(self.clicked_menu_button)
        self.left_menu_downloads_button = self.findChild(QWidget, "left_menu_downloads_button")
        self.left_menu_downloads_button.clicked_menu_button.connect(self.clicked_menu_button)
        self.left_menu_videoplayer_button = self.findChild(QWidget, "left_menu_videoplayer_button")
        self.left_menu_videoplayer_button.clicked_menu_button.connect(self.clicked_menu_button)
        self.left_menu_settings_button = self.findChild(QWidget, "left_menu_settings_button")
        self.left_menu_settings_button.clicked_menu_button.connect(self.clicked_menu_button)

        self.menu_buttons = [self.left_menu_home_button, self.left_menu_my_channel_button,
                             self.left_menu_subscribed_button, self.left_menu_videoplayer_button,
                             self.left_menu_settings_button, self.left_menu_downloads_button]

        channel_back_button = self.findChild(QToolButton, "channel_back_button")
        channel_back_button.clicked.connect(self.on_page_back_clicked)

        self.stackedWidget.setCurrentIndex(PAGE_HOME)

        self.channel_tab = self.findChild(QWidget, "channel_tab")
        self.channel_tab.initialize()
        self.channel_tab.clicked_tab_button.connect(self.on_channel_tab_button_clicked)
        self.channel_stacked_widget = self.findChild(QStackedWidget, "channel_stacked_widget")

        self.channel_comments_list = self.findChild(QTreeWidget, "channel_comments_list")
        self.channel_activities_list = self.findChild(QListWidget, "channel_activities_list")

        # TODO Martijn: for now, fill the comments and activity with some dummy data
        for i in range(0, 10):
            parent_item = QTreeWidgetItem(self.channel_comments_list)
            widget_item = ChannelCommentListItem(self.channel_comments_list, 0)
            self.channel_comments_list.setItemWidget(parent_item, 0, widget_item)

            child_item = QTreeWidgetItem(self.channel_comments_list)
            widget_item = ChannelCommentListItem(self.channel_comments_list, 1)
            self.channel_comments_list.setItemWidget(child_item, 0, widget_item)

        for i in range(0, 10):
            item = QListWidgetItem(self.channel_activities_list)
            widget_item = ChannelActivityListItem(self.channel_activities_list)
            item.setSizeHint(widget_item.sizeHint())
            self.channel_activities_list.setItemWidget(item, widget_item)

        # fetch the settings
        self.settings_request_mgr = TriblerRequestManager()
        self.settings_request_mgr.get_settings(self.received_settings)

        self.event_request_manager = EventRequestManager()
        self.event_request_manager.received_free_space.connect(self.received_free_space)

        # Set profile image
        placeholder_pix = QPixmap("images/profile_placeholder.jpg")
        placeholder_pix = placeholder_pix.scaledToHeight(self.my_profile_button.width(), Qt.SmoothTransformation)
        placeholder_pix = create_rounded_image(placeholder_pix)
        self.my_profile_button.setIcon(QIcon(placeholder_pix))
        self.my_profile_button.setIconSize(QSize(self.my_profile_button.width(), self.my_profile_button.height()))

        self.left_menu.hide()

        self.video_player_page.initialize_player()
        self.search_results_page.initialize_search_results_page()
        self.settings_page.initialize_settings_page()
        self.my_channel_page.initialize_my_channel_page()
        self.downloads_page.initialize_downloads_page()

        self.show()

    def received_free_space(self, free_space):
        self.statusBar.set_free_space(free_space)

    def channels_list_load_next_items(self, should_fade=False):
        if len(self.channels) == self.channels_list_items_loaded:
            return

        delay = 0
        for i in range(self.channels_list_items_loaded,
                       min(self.channels_list_items_loaded + LIST_BATCH_SIZE, len(self.channels) - 1)):
            channel_data = self.channels[i]
            item = QListWidgetItem(self.channels_list)
            item.setSizeHint(QSize(-1, 60))
            item.setData(Qt.UserRole, channel_data)
            widget_item = ChannelListItem(self.channels_list, delay, channel_data, should_fade)
            self.channels_list.addItem(item)
            self.channels_list.setItemWidget(item, widget_item)
            delay += 50

        self.channels_list_items_loaded += LIST_BATCH_SIZE

    def received_channels(self, json_results):
        self.channels_list.clear()
        self.channels = json.loads(json_results)['channels']
        self.channels_list_items_loaded = 0
        self.channels_list_load_next_items(should_fade=True)

    def received_subscribed_channels(self, json_results):
        self.subscribed_channels_list.clear()
        results = json.loads(json_results)

        delay = 0
        for result in results['subscribed']:
            item = QListWidgetItem(self.subscribed_channels_list)
            item.setSizeHint(QSize(-1, 60))
            item.setData(Qt.UserRole, result)
            widget_item = ChannelListItem(self.subscribed_channels_list, delay, result)
            self.subscribed_channels_list.addItem(item)
            self.subscribed_channels_list.setItemWidget(item, widget_item)
            delay += 50

    def received_torrents_in_channel(self, json_results):
        self.channel_torrents_list.clear()
        results = json.loads(json_results)

        for result in results['torrents']:
            item = QListWidgetItem(self.channel_torrents_list)
            item.setSizeHint(QSize(-1, 60))
            item.setData(Qt.UserRole, result)
            widget_item = ChannelTorrentListItem(self.channel_torrents_list, result)
            self.channel_torrents_list.addItem(item)
            self.channel_torrents_list.setItemWidget(item, widget_item)

    def received_settings(self, json_results):
        results = json.loads(json_results)
        self.video_player_page.video_player_port = results['video']['port']
        self.settings = json.loads(json_results)

    def on_top_search_button_click(self):
        self.stackedWidget.setCurrentIndex(PAGE_SEARCH_RESULTS)
        self.search_request_mgr = TriblerRequestManager()
        self.search_request_mgr.search_channels(self.top_search_bar.text(),
                                                self.search_results_page.received_search_results)

    def on_top_menu_button_click(self):
        if self.left_menu.isHidden():
            self.left_menu.show()
        else:
            self.left_menu.hide()

    def on_channel_tab_button_clicked(self, button_name):
        if button_name == "channel_content_button":
            self.channel_stacked_widget.setCurrentIndex(PAGE_CHANNEL_CONTENT)
        elif button_name == "channel_comments_button":
            self.channel_stacked_widget.setCurrentIndex(PAGE_CHANNEL_COMMENTS)
        elif button_name == "channel_activity_button":
            self.channel_stacked_widget.setCurrentIndex(PAGE_CHANNEL_ACTIVITY)

    def clicked_menu_button(self, menu_button_name):
        # Deselect menu buttons
        for button in self.menu_buttons:
            button.unselectMenuButton()

        if menu_button_name == "left_menu_home_button":
            self.left_menu_home_button.selectMenuButton()
            self.stackedWidget.setCurrentIndex(PAGE_HOME)
        elif menu_button_name == "left_menu_my_channel_button":
            self.left_menu_my_channel_button.selectMenuButton()
            self.stackedWidget.setCurrentIndex(PAGE_MY_CHANNEL)
        elif menu_button_name == "left_menu_videoplayer_button":
            self.left_menu_videoplayer_button.selectMenuButton()
            self.stackedWidget.setCurrentIndex(PAGE_VIDEO_PLAYER)
        elif menu_button_name == "left_menu_downloads_button":
            self.left_menu_downloads_button.selectMenuButton()
            self.stackedWidget.setCurrentIndex(PAGE_DOWNLOADS)
        elif menu_button_name == "left_menu_settings_button":
            self.left_menu_settings_button.selectMenuButton()
            self.stackedWidget.setCurrentIndex(PAGE_SETTINGS)
        elif menu_button_name == "left_menu_subscribed_button":
            self.left_menu_subscribed_button.selectMenuButton()
            self.subscribed_channels_request_manager = TriblerRequestManager()
            self.subscribed_channels_request_manager.get_subscribed_channels(self.received_subscribed_channels)
            self.stackedWidget.setCurrentIndex(PAGE_SUBSCRIBED_CHANNELS)
        self.navigation_stack = []

    def on_channel_item_click(self, channel_list_item):
        channel_info = channel_list_item.data(Qt.UserRole)
        self.get_torents_in_channel_manager = TriblerRequestManager()
        self.get_torents_in_channel_manager.get_torrents_in_channel(str(channel_info['id']), self.received_torrents_in_channel)
        self.navigation_stack.append(self.stackedWidget.currentIndex())
        self.stackedWidget.setCurrentIndex(PAGE_CHANNEL_DETAILS)

        # initialize the page about a channel
        channel_detail_pane = self.findChild(QWidget, "channel_details")
        channel_name_label = channel_detail_pane.findChild(QLabel, "channel_name_label")
        channel_num_subs_label = channel_detail_pane.findChild(QLabel, "channel_num_subs_label")

        channel_name_label.setText(channel_info['name'])
        channel_num_subs_label.setText(str(channel_info['votes']))

    def on_page_back_clicked(self):
        prev_page = self.navigation_stack.pop()
        self.stackedWidget.setCurrentIndex(prev_page)

    def resizeEvent(self, event):
        self.resize_event.emit()

app = QApplication(sys.argv)
window = TriblerWindow()
window.setWindowTitle("Tribler")
sys.exit(app.exec_())
