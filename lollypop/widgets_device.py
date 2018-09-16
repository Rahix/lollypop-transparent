# Copyright (c) 2014-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib, Gio, GObject, Pango

from gettext import gettext as _

from lollypop.sync_mtp import MtpSync
from lollypop.cellrenderer import CellRendererAlbum
from lollypop.define import App, Type
from lollypop.objects import Album
from lollypop.logger import Logger
from lollypop.helper_task import TaskHelper


# FIXME This class should not inherit MtpSync
# TODO Rework MtpSync code
class DeviceManagerWidget(Gtk.Bin, MtpSync):
    """
        Widget for synchronize mtp devices
    """
    __gsignals__ = {
        "sync-finished": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, parent):
        """
            Init widget
            @param device as Device
            @param parent as Gtk.Widget
        """
        Gtk.Bin.__init__(self)
        MtpSync.__init__(self)
        self.__parent = parent
        self.__stop = False
        self._uri = None

        self.__builder = Gtk.Builder()
        self.__builder.add_from_resource(
            "/org/gnome/Lollypop/DeviceManagerWidget.ui")
        widget = self.__builder.get_object("widget")
        self.connect("size-allocate", self.__on_size_allocate, widget)

        self.__error_label = self.__builder.get_object("error-label")
        self.__switch_albums = self.__builder.get_object("switch_albums")

        self.__menu_items = self.__builder.get_object("menu-items")
        self.__menu = self.__builder.get_object("menu")

        self.__model = Gtk.ListStore(bool, str, int)

        self.__view = self.__builder.get_object("view")
        self.__view.set_model(self.__model)

        self.__builder.connect_signals(self)

        self.add(widget)

        self.__infobar = self.__builder.get_object("infobar")
        self.__infobar_label = self.__builder.get_object("infobarlabel")

        renderer0 = Gtk.CellRendererToggle()
        renderer0.set_property("activatable", True)
        renderer0.connect("toggled", self.__on_item_toggled)
        column0 = Gtk.TreeViewColumn(" ✓", renderer0, active=0)
        column0.set_clickable(True)
        column0.connect("clicked", self.__on_column0_clicked)

        renderer1 = CellRendererAlbum()
        self.__column1 = Gtk.TreeViewColumn("", renderer1, album=2)

        renderer2 = Gtk.CellRendererText()
        renderer2.set_property("ellipsize-set", True)
        renderer2.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.__column2 = Gtk.TreeViewColumn("", renderer2, markup=1)
        self.__column2.set_expand(True)

        self.__view.append_column(column0)
        self.__view.append_column(self.__column1)
        self.__view.append_column(self.__column2)

    def populate(self, selected_ids=[]):
        """
            Populate playlists or albums for selected_ids
            @param selected_ids as [int]
            @thread safe
        """
        self.__model.clear()
        self.__stop = False
        if selected_ids[0] == Type.PLAYLISTS:
            playlists = [(Type.LOVED, App().playlists.LOVED)]
            playlists += App().playlists.get()
            synced_ids = App().playlists.get_synced_ids()
            self.__append_playlists(playlists, synced_ids)
            self.__column1.set_visible(False)
            self.__column2.set_title(_("Playlists"))
        else:
            if selected_ids[0] == Type.COMPILATIONS:
                albums = App().albums.get_compilation_ids()
            elif selected_ids[0] == Type.ALL:
                albums = App().albums.get_synced_ids()
            else:
                albums = App().albums.get_ids(selected_ids)
            self.__model.clear()
            self.__append_albums(albums)
            self.__column1.set_visible(True)
            self.__column2.set_title(_("Albums"))

    def set_uri(self, uri):
        """
            Set uri
            @param uri as str
        """
        try:
            self.__switch_albums.disconnect_by_func(self.__on_albums_state_set)
        except:
            pass
        self._load_db_uri(uri)
        encoder = self.mtp_syncdb.encoder
        normalize = self.mtp_syncdb.normalize
        self.__switch_normalize = self.__builder.get_object("switch_normalize")
        self.__switch_normalize.set_sensitive(False)
        self.__switch_normalize.set_active(normalize)
        self.__builder.get_object(encoder).set_active(True)
        for encoder in self._GST_ENCODER.keys():
            if not self._check_encoder_status(encoder):
                self.__builder.get_object(encoder).set_sensitive(False)
        self._uri = uri
        d = Gio.File.new_for_uri(uri)
        try:
            if not d.query_exists():
                d.make_directory_with_parents()
        except:
            pass

    def is_syncing(self):
        """
            @return True if syncing
        """
        return self._syncing

    def sync(self):
        """
            Start synchronisation
        """
        self._syncing = True
        App().window.container.progress.add(self)
        self.__menu.set_sensitive(False)
        self.__view.set_sensitive(False)
        helper = TaskHelper()
        helper.run(self._sync)

    def cancel_sync(self):
        """
            Cancel synchronisation
        """
        self._syncing = False

#######################
# PROTECTED           #
#######################
    def _update_progress(self):
        """
            Update progress bar smoothly
        """
        current = App().window.container.progress.get_fraction()
        if self._syncing:
            progress = (self._fraction - current) / 10
        else:
            progress = 0.01
        if current < self._fraction:
            App().window.container.progress.set_fraction(current + progress,
                                                         self)
        if current < 1.0:
            if progress < 0.0002:
                GLib.timeout_add(500, self._update_progress)
            else:
                GLib.timeout_add(25, self._update_progress)
        else:
            GLib.timeout_add(1000, self._on_finished)

    def _pop_menu(self, button):
        """
            Popup menu for album
            @param button as Gtk.Button
            @param album id as int
        """
        parent = self.__menu_items.get_parent()
        if parent is not None:
            parent.remove(self.__menu_items)
        popover = Gtk.Popover.new(button)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.add(self.__menu_items)
        popover.popup()

    def _on_finished(self):
        """
            Emit finished signal
        """
        MtpSync._on_finished(self)
        App().window.container.progress.set_fraction(1.0, self)
        self.__view.set_sensitive(True)
        self.__menu.set_sensitive(True)
        self.emit("sync-finished")

    def _on_errors(self):
        """
            Show information bar with error message
        """
        MtpSync._on_errors(self)
        error_text = _("Unknown error while syncing,"
                       " try to reboot your device")
        try:
            d = Gio.File.new_for_uri(self._uri)
            info = d.query_filesystem_info("filesystem::free")
            free = info.get_attribute_as_string("filesystem::free")

            if free is None or int(free) < 1024:
                error_text = _("No free space available on device")
        except Exception as e:
            Logger.error("DeviceWidget::_on_errors(): %s" % e)
        self.__error_label.set_text(error_text)
        self.__infobar.show()

    def _on_convert_toggled(self, widget):
        """
            Save option
            @param widget as Gtk.RadioButton
        """
        if widget.get_active():
            encoder = widget.get_name()
            if encoder == "convert_none":
                self.__switch_normalize.set_sensitive(False)
                self.mtp_syncdb.set_normalize(False)
                self.mtp_syncdb.set_encoder("convert_none")
            else:
                self.__switch_normalize.set_sensitive(True)
                self.mtp_syncdb.set_encoder(encoder)

    def _on_normalize_state_set(self, widget, state):
        """
            Save option
            @param widget as Gtk.Switch
            @param state as bool
        """
        self.mtp_syncdb.set_normalize(state)

    def _on_response(self, infobar, response_id):
        """
            Hide infobar
            @param widget as Gtk.Infobar
            @param reponse id as int
        """
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

#######################
# PRIVATE             #
#######################
    def __append_playlists(self, playlists, synced_ids):
        """
            Append a playlist
            @param playlists as [(int, str)]
            @param synced_ids as [int]
        """
        if playlists and not self.__stop:
            playlist = playlists.pop(0)
            selected = playlist[0] in synced_ids
            self.__model.append([selected, playlist[1], playlist[0]])
            GLib.idle_add(self.__append_playlists, playlists, synced_ids)

    def __append_albums(self, albums):
        """
            Append albums
            @param albums as [int]
        """
        if albums and not self.__stop:
            album = Album(albums.pop(0))
            synced = App().albums.get_synced(album.id)
            # Do not sync youtube albums
            if synced != Type.NONE:
                if album.artist_ids[0] == Type.COMPILATIONS:
                    name = GLib.markup_escape_text(album.name)
                else:
                    artists = ", ".join(album.artists)
                    name = "<b>%s</b> - %s" % (
                        GLib.markup_escape_text(artists),
                        GLib.markup_escape_text(album.name))
                self.__model.append([synced, name, album.id])
            GLib.idle_add(self.__append_albums, albums)

    def __populate_albums_playlist(self, album_id, toggle):
        """
            Populate hidden albums playlist
            @param album_id as int
            @param toggle as bool
        """
        App().albums.set_synced(album_id, toggle)

    def __on_column0_clicked(self, column):
        """
            Select/Unselect all playlists
            @param column as Gtk.TreeViewColumn
        """
        selected = False
        for item in self.__model:
            if item[0]:
                selected = True
        for item in self.__model:
            item[0] = not selected
            if self.__column1.get_visible():
                self.__populate_albums_playlist(item[2], item[0])
            else:
                App().playlists.set_synced(item[2], item[0])

    def __on_item_toggled(self, view, path):
        """
            When item is toggled, set model
            @param widget as cell renderer
            @param path as str representation of Gtk.TreePath
        """
        iterator = self.__model.get_iter(path)
        toggle = not self.__model.get_value(iterator, 0)
        self.__model.set_value(iterator, 0, toggle)
        item_id = self.__model.get_value(iterator, 2)
        if self.__column1.get_visible():
            self.__populate_albums_playlist(item_id, toggle)
        else:
            App().playlists.set_synced(item_id, toggle)

    def __on_size_allocate(self, widget, allocation, child_widget):
        """
            Set child widget size
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
            @param child_widget as Gtk.Widget
        """
        width = max(400, allocation.width / 2)
        child_widget.set_size_request(width, -1)
