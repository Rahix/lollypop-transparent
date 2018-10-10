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

from gi.repository import Gtk, GLib, Gdk

from gettext import gettext as _

from lollypop.define import App
from lollypop.define import Shuffle
from lollypop.pop_artwork import CoversPopover


class AlbumBaseWidget:
    """
        Base album widget
    """

    def __init__(self):
        """
            Init widget
        """
        self._artwork = None
        self._widget = None
        self._play_all_button = None
        self._action2_button = None
        self._action1_button = None
        self._show_overlay = False
        self._lock_overlay = True
        self._timeout_id = None
        self.__parent_filter = False

    def set_filtered(self, b):
        """
            Set widget filtered
        """
        self.__parent_filter = b

    def lock_overlay(self, lock):
        """
            Lock overlay
            @param lock as bool
        """
        self._lock_overlay = lock

    def show_overlay(self, set):
        """
            Set overlay
            @param set as bool
        """
        # Remove enter notify timeout
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self._show_overlay_func(set)

    @property
    def is_populated(self):
        """
            True if album populated
        """
        return True

    @property
    def filter(self):
        return ""

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__parent_filter

    @property
    def is_overlay(self):
        """
            True if overlayed or going to be
        """
        return self._show_overlay or self._timeout_id is not None

#######################
# PROTECTED           #
#######################
    def _set_play_all_image(self):
        """
            Set play all image based on current shuffle status
        """
        if App().settings.get_enum("shuffle") == Shuffle.NONE:
            self._play_all_button.set_from_icon_name(
                "media-playlist-consecutive-symbolic",
                Gtk.IconSize.BUTTON)
        else:
            self._play_all_button.set_from_icon_name(
                "media-playlist-shuffle-symbolic",
                Gtk.IconSize.BUTTON)

    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set:
            return
        self._show_overlay = set
        self.emit("overlayed", set)
        if set:
            if App().player.is_locked:
                opacity = 0.2
            else:
                opacity = 1
            if self._play_button is not None:
                self._play_button.set_opacity(opacity)
                self._play_button.get_style_context().add_class(
                    "rounded-icon")
                self._play_button.show()
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(opacity)
                self._play_all_button.get_style_context().add_class(
                    "rounded-icon-small")
                self._set_play_all_image()
                self._play_all_button.show()
            if self._action2_button is not None:
                self._action2_button.set_opacity(1)
                self._action2_button.get_style_context().add_class(
                    "rounded-icon-small")
                self._action2_button.show()
            if self._action1_button is not None:
                self._show_append(self._album.id not in App().player.album_ids)
                self._action1_button.set_opacity(opacity)
                self._action1_button.get_style_context().add_class(
                    "rounded-icon-small")
                self._action1_button.show()
        else:
            if self._play_button is not None:
                self._play_button.set_opacity(0)
                self._play_button.hide()
                self._play_button.get_style_context().remove_class(
                    "rounded-icon")
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(0)
                self._play_all_button.hide()
                self._play_all_button.get_style_context().remove_class(
                    "rounded-icon-small")
            if self._action2_button is not None:
                self._action2_button.hide()
                self._action2_button.set_opacity(0)
                self._action2_button.get_style_context().remove_class(
                    "rounded-icon-small")
            if self._action1_button is not None:
                self._action1_button.hide()
                self._action1_button.set_opacity(0)
                self._action1_button.get_style_context().remove_class(
                    "rounded-icon-small")

    def _on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def _on_enter_notify(self, widget, event):
        """
            Show overlay buttons after a timeout
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        if self._artwork is not None:
            self._artwork.set_opacity(0.9)
        if self._timeout_id is None:
            self._timeout_id = GLib.timeout_add(250,
                                                self.__on_enter_notify_timeout)

    def _on_leave_notify(self, widget, event):
        """
            Hide overlay buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            if self._artwork is not None:
                self._artwork.set_opacity(1)
            # Remove enter notify timeout
            if self._timeout_id is not None:
                GLib.source_remove(self._timeout_id)
                self._timeout_id = None
            if self._show_overlay:
                self._show_overlay_func(False)

    def _on_play_press_event(self, widget, event):
        """
            Play album
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        if App().player.is_party:
            action = App().lookup_action("party")
            action.change_state(GLib.Variant("b", False))
        App().player.play_album(self._album)
        self._show_append(False)
        return True

    def _on_artwork_press_event(self, widget, event):
        """
            Popover with album art downloaded from the web (in fact google :-/)
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        popover = CoversPopover(self._album)
        popover.set_relative_to(widget)
        popover.connect("closed", self._on_popover_closed)
        self._lock_overlay = True
        popover.popup()
        return True

    def _on_action_press_event(self, widget, event):
        """
            Append album to current list if not present
            Remove it if present
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if App().player.is_locked:
            return True
        if self._album.id in App().player.album_ids:
            if App().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(App().player.albums) > 1:
                    App().player.skip_album()
                    App().player.remove_album_by_id(self._album.id)
                # remove it and stop playback by going to next track
                else:
                    App().player.remove_album_by_id(self._album.id)
                    App().player.stop()
            else:
                App().player.remove_album_by_id(self._album.id)
            self._show_append(True)
        else:
            if App().player.is_playing and not App().player.albums:
                App().player.play_album(self._album)
            else:
                App().player.add_album(self._album)
            self._show_append(False)
        return True

    def _on_popover_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self._lock_overlay = False
        GLib.idle_add(self.show_overlay, False)

    def _show_append(self, append):
        """
            Show append button if append, else remove button
        """
        if append:
            self._action1_button.set_from_icon_name("list-add-symbolic",
                                                    Gtk.IconSize.BUTTON)
            self._action1_event.set_tooltip_text(_("Add to current playlist"))
        else:
            self._action1_button.set_from_icon_name("list-remove-symbolic",
                                                    Gtk.IconSize.BUTTON)
            self._action1_event.set_tooltip_text(
                _("Remove from current playlist"))

#######################
# PRIVATE             #
#######################
    def __on_enter_notify_timeout(self):
        """
            Show overlay buttons
        """
        self._timeout_id = None
        if not self._show_overlay:
            self._show_overlay_func(True)


class AlbumWidget(AlbumBaseWidget):
    """
        Album widget
    """

    def __init__(self, album, genre_ids, artist_ids):
        """
            Init Album widget
        """
        AlbumBaseWidget.__init__(self)
        self._album = album
        self.connect("destroy", self.__on_destroy)
        self._scan_signal = App().scanner.connect("album-updated",
                                                  self._on_album_updated)

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self._artwork is None:
            return
        selected = self._album.id == App().player.current_track.album.id
        if selected:
            self._artwork.set_state(Gtk.StateType.SELECTED)
        else:
            self._artwork.set_state(Gtk.StateType.NORMAL)

    @property
    def album(self):
        """
            @return Album
        """
        return self._album

    @property
    def filter(self):
        """
            @return str
        """
        return " ".join([self._album.name] + self._album.artists)

#######################
# PROTECTED           #
#######################
    def _on_album_updated(self, scanner, album_id, destroy):
        pass

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self._scan_signal is not None:
            App().scanner.disconnect(self._scan_signal)
