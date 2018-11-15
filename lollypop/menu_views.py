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

from gi.repository import Gtk, Gio, GLib

from gettext import gettext as _
from hashlib import sha256

from lollypop.define import Type, App, SelectionListMask
from lollypop.shown import ShownLists, ShownPlaylists


class ViewsMenu(Gio.Menu):
    """
        Configure defaults items
    """

    def __init__(self, rowid, mask):
        """
            Init menu
            @param rowid as int
            @param lists as [int]
            @param mask as SelectionListMask
        """
        Gtk.Popover.__init__(self)
        self.__rowid = rowid
        self.__mask = mask
        # Startup menu
        if rowid in [Type.POPULARS, Type.RADIOS, Type.LOVED,
                     Type.ALL, Type.RECENTS, Type.YEARS,
                     Type.RANDOMS, Type.NEVER,
                     Type.PLAYLISTS, Type.ARTISTS]:
            startup_menu = Gio.Menu()
            action = Gio.SimpleAction(name="default_selection_id")
            App().add_action(action)
            action.connect('activate',
                           self.__on_action_clicked,
                           rowid)
            item = Gio.MenuItem.new(_("Default on startup"),
                                    "app.default_selection_id")
            startup_menu.append_item(item)
            self.insert_section(0, _("Startup"), startup_menu)
        # Shown menu
        shown_menu = Gio.Menu()
        if mask & SelectionListMask.PLAYLISTS:
            lists = ShownPlaylists.get(True)
            wanted = App().settings.get_value("shown-playlists")
        else:
            lists = ShownLists.get(mask, True)
            wanted = App().settings.get_value("shown-album-lists")
        for item in lists:
            exists = item[0] in wanted
            encoded = sha256(item[1].encode("utf-8")).hexdigest()
            action = Gio.SimpleAction.new_stateful(
                encoded,
                None,
                GLib.Variant.new_boolean(exists))
            action.connect("change-state",
                           self.__on_action_change_state,
                           item[0])
            App().add_action(action)
            shown_menu.append(item[1], "app.%s" % encoded)
        # Translators: shown => items
        self.insert_section(1, _("Shown"), shown_menu)

#######################
# PRIVATE             #
#######################
    def __on_action_change_state(self, action, param, rowid):
        """
            Set action value
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
            @param rowid as int
        """
        action.set_state(param)
        if self.__mask & SelectionListMask.PLAYLISTS:
            option = "shown-playlists"
        else:
            option = "shown-album-lists"
        wanted = list(App().settings.get_value(option))
        if param:
            wanted.append(rowid)
        else:
            wanted.remove(rowid)
        App().settings.set_value(option, GLib.Variant("ai", wanted))
        if self.__mask & SelectionListMask.LIST_ONE:
            App().window.container.update_list_one(True)
        elif self.__mask & SelectionListMask.LIST_TWO:
            App().window.container.update_list_two(True)

    def __on_action_clicked(self, action, variant, rowid):
        """
            Add to playlists
            @param Gio.SimpleAction
            @param GVariant
            @param rowid as int
        """
        if self.__mask & SelectionListMask.LIST_ONE:
            App().settings.set_value(
                "list-one-ids",
                GLib.Variant("ai", [rowid]))
            App().settings.set_value(
                "list-two-ids",
                GLib.Variant("ai", []))
        elif self.__mask & SelectionListMask.LIST_TWO:
            App().settings.set_value(
                "list-two-ids",
                GLib.Variant("ai", [rowid]))
