'''
TKinter code to display the scoreboard

This file can be directly executed to display a mockup of the scoreboard.
'''
# Wahoo! Results - https://github.com/JohnStrunk/wahoo-results
# Copyright (C) 2020 - John D. Strunk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Dict, Union
from PIL import Image, ImageTk  #type: ignore
from PIL.ImageEnhance import Brightness  #type: ignore

from bounded_text import BoundedText

TkContainer = Any

#pylint: disable=too-many-ancestors,too-many-instance-attributes
class Scoreboard(tk.Canvas):
    '''
    Tkinter object that displays the Wahoo Results scoreboard

    Parameters:
        container: The parent Tk object for this widget
        kwargs: Parameters to pass to the underlying canvas widget
    '''

    # Background for the scoreboard
    _bg_color = "black"
    _text_color = "white"
    _bg_image: Image = None
    _bg_image_fill: str
    _bg_image_pimage: ImageTk.PhotoImage
    # Maximum number of lanes supported
    _max_lanes = 10
    # Number of lanes that will be shown
    _num_lanes: int
    _event_num: Union[int, str] = ""
    _event_description: str = ""
    _heat_num: int = 0
    _text_items: Dict[str, BoundedText] = {}
    _border_pct = 0.05
    _header_gap_pct = 0.05
    _font: tkfont.Font
    _line_height: int

    def __init__(self, container: TkContainer, **kwargs):
        super().__init__(container, kwargs)
        self.create_image(0, 0, image=None, tag="bg_image")
        self._font = tkfont.Font()
        for i in ["event_heat", "event_desc", "hdr_lane", "hdr_name", "hdr_time"]:
            self._text_items[i] = BoundedText(self, 0, 0, fill=self._text_color, width=1)
        self.bind("<Configure>", self._reconfigure)
        self.set_lanes(9999)
        self._reconfigure(None)
        self.clear()

    @classmethod
    def format_place(cls, place: int) -> str:
        """
        >>> Scoreboard.format_place(1)
        '1st'
        >>> Scoreboard.format_place(6)
        '6th'
        """
        if place == 0:
            return ""
        if place == 1:
            return "1st"
        if place == 2:
            return "2nd"
        if place == 3:
            return "3rd"
        return f"{place}th"

    @classmethod
    def format_time(cls, time_seconds: float) -> str:
        """
        >>> Scoreboard.format_time(1.2)
        '01.20'
        >>> Scoreboard.format_time(9.87)
        '09.87'
        >>> Scoreboard.format_time(50)
        '50.00'
        >>> Scoreboard.format_time(120.0)
        '2:00.00'
        """
        minutes = int(time_seconds//60)
        seconds = time_seconds - minutes*60.0
        if minutes == 0:
            return f"{seconds:05.2f}"
        return f"{minutes}:{seconds:05.2f}"

    def clear(self):
        '''Clear the scoreboard'''
        for i in range(self._max_lanes):
            self._text_items[f"lane_{i}_name"].text = ""
            self._text_items[f"lane_{i}_pl"].text = ""
            self._text_items[f"lane_{i}_time"].text = ""
        self.event("1", "")
        self.heat(1)

    def event(self, event_num: Union[int, str], event_description: str):
        '''
        Set the event number and description

        Parameters:
            event_num: The event number
            event_description: The text description of the event
        '''
        self._event_num = event_num
        self._event_description = event_description
        self._text_items["event_heat"].text = f"E: {self._event_num} / H: {self._heat_num}"
        self._text_items["event_desc"].text = self._event_description

    def heat(self, heat_num: int):
        '''
        Set the heat number

        Parameters:
            heat_num: The number of the current heat
        '''
        self._heat_num = heat_num
        self._text_items["event_heat"].text = f"E: {self._event_num} / H: {self._heat_num}"

    #pylint: disable=unused-argument,too-many-arguments
    def lane(self, lane_num: int, name: str = "", team: str = "",
             time: float = 0.0, place: int = 0):
        '''
        Update the data for a lane

        Parameters:
            lane_num: The lane to update
            name: The name of the swimmer
            team: The swimmer's team
            time: The result time from the race,
                  Zero if the lane was empty,
                  Negative if the time was inconsistent.
        '''
        self._text_items[f"lane_{lane_num-1}_name"].text = name
        pl_txt = self._text_items[f"lane_{lane_num-1}_pl"]
        pl_txt.text = self.format_place(place)
        if place == 1:
            pl_txt.configure(fill="#00FFFF")
        elif place == 2:
            pl_txt.configure(fill="#FF0000")
        elif place == 3:
            pl_txt.configure(fill="#FFFF00")
        else:
            pl_txt.configure(fill=self._text_color)
        if time == 0.0:
            self._text_items[f"lane_{lane_num-1}_time"].text = ""
        elif time < 0.0:
            self._text_items[f"lane_{lane_num-1}_time"].text = "--:--.--"
        else:
            self._text_items[f"lane_{lane_num-1}_time"].text = self.format_time(time)

    def set_lanes(self, lanes: int):
        '''
        Configure the number of lanes displayed on the scoreboard

        Parameters:
            lanes: The number of lanes to display
        '''
        self._num_lanes = min(lanes, self._max_lanes)

    def bg_image(self, image: Image, fill: str = "fit"):
        '''
        Set a background image for the scoreboard

        Parameters:
            image: The image to display
            fill: A string indicating how to format the image
                "none": Use the image as-is
                "stretch": Stretch the image to fill the entire scoreboard
                "fit": Uniformly scale to fit it on the scoreboard
                "cover": Uniformly scale to fully cover the scoreboard
        '''
        self._bg_image = image
        self._bg_image_fill = fill

    def _reconfigure(self, event):
        self.update()
        self._draw_bg(event)
        self._update_font()
        self._draw_header()
        self._draw_lanes()
        self._update_font()

    def _update_font(self):
        line_height = int(self.winfo_height() *
                          (1 - 2*self._border_pct - self._header_gap_pct) /
                          (self._num_lanes + 2))
        self._font = tkfont.Font(family="Overpass", weight="bold", size=int(-0.75 * line_height))
        self._line_height = line_height
        for i in self._text_items.values():
            i.font = self._font

    def _draw_header(self):
        eh_pct = 0.33  # fraction of width for event/heat number
        desc_pct = 0.66  # fraction of width for event description
        lpos = int(self.winfo_width() * self._border_pct)
        rpos = int(self.winfo_width() * (1-self._border_pct))
        vpos = int(self.winfo_height() * self._border_pct + self._line_height)
        self._text_items["event_heat"].configure(anchor="sw")
        self._text_items["event_heat"].move_to(lpos, vpos)
        self._text_items["event_heat"].width = (rpos-lpos)*eh_pct
        self._text_items["event_desc"].configure(anchor="se")
        self._text_items["event_desc"].move_to(rpos, vpos)
        self._text_items["event_desc"].width = (rpos-lpos)*desc_pct

    def _draw_lanes(self):
        idx_pct = 0.12  # fraction of width for lane number
        pl_pct = 0.10  # fraction of width for heat place
        name_pct = 0.55  # fraction of width for name
        time_pct = 0.20  # fraction of width for finish time
        lpos = int(self.winfo_width() * self._border_pct)
        rpos = int(self.winfo_width() * (1-self._border_pct))
        width = rpos - lpos
        lane_top = int(self.winfo_height() * (self._border_pct + self._header_gap_pct) +
                       2 * self._line_height)
        self._text_items["hdr_lane"].configure(anchor="s")
        self._text_items["hdr_lane"].move_to(lpos + idx_pct/3 * width, lane_top)
        self._text_items["hdr_lane"].width = idx_pct * width
        self._text_items["hdr_lane"].text = "Lane"
        self._text_items["hdr_name"].configure(anchor="sw")
        self._text_items["hdr_name"].move_to(lpos + (idx_pct + pl_pct) * width, lane_top)
        self._text_items["hdr_name"].width = name_pct * width
        self._text_items["hdr_name"].text = "Name"
        self._text_items["hdr_time"].configure(anchor="se")
        self._text_items["hdr_time"].move_to(rpos, lane_top)
        self._text_items["hdr_time"].width = time_pct * width
        self._text_items["hdr_time"].text = "Time"
        for i in range(self._max_lanes):
            # Lane number
            txt = self._text_items.setdefault(f"lane_{i}_idx",
                BoundedText(self, 0, 0, fill=self._text_color, width=1))
            txt.configure(anchor="s")
            txt.move_to(lpos + idx_pct/3 * width, lane_top + (i+1) * self._line_height)
            txt.width = idx_pct * width
            if i < self._num_lanes:
                txt.text = f"{i+1}"
            else:
                txt.text = ""
            # Place
            txt = self._text_items.setdefault(f"lane_{i}_pl",
                BoundedText(self, 0, 0, fill=self._text_color, width=1))
            txt.configure(anchor="sw")
            txt.move_to(lpos + idx_pct * width, lane_top + (i+1) * self._line_height)
            txt.width = pl_pct * width
            if i >= self._num_lanes:
                txt.text = ""
            # Name
            txt = self._text_items.setdefault(f"lane_{i}_name",
                BoundedText(self, 0, 0, fill=self._text_color, width=1))
            txt.configure(anchor="sw")
            txt.move_to(lpos + (idx_pct + pl_pct) * width, lane_top + (i+1) * self._line_height)
            txt.width = name_pct * width
            if i >= self._num_lanes:
                txt.text = ""
            # Time
            txt = self._text_items.setdefault(f"lane_{i}_time",
                BoundedText(self, 0, 0, fill=self._text_color, width=1))
            txt.configure(anchor="se")
            txt.move_to(rpos, lane_top + (i+1) * self._line_height)
            txt.width = time_pct * width
            if i >= self._num_lanes:
                txt.text = ""

    def _draw_bg(self, _):
        self.configure(bg=self._bg_color)
        if self._bg_image is not None:
            i_size = self._bg_image.size
            c_size = (self.winfo_width(), self.winfo_height())
            if self._bg_image_fill == "stretch":
                scaled = self._bg_image.resize(c_size)
            elif self._bg_image_fill == "fit":
                factor = min(c_size[0]/i_size[0], c_size[1]/i_size[1])
                scaled = self._bg_image.resize((int(i_size[0]*factor), int(i_size[1]*factor)))
            elif self._bg_image_fill == "cover":
                factor = max(c_size[0]/i_size[0], c_size[1]/i_size[1])
                scaled = self._bg_image.resize((int(i_size[0]*factor), int(i_size[1]*factor)))
            else:
                scaled = self._bg_image
            self._bg_image_pimage = ImageTk.PhotoImage(scaled)
            self.coords("bg_image", c_size[0]//2, c_size[1]//2)
            self.itemconfigure("bg_image", image=self._bg_image_pimage)

def show_mockup(board: Scoreboard):
    '''
    Displays fake data on the scoreboard for testing and demonstration
    purposes
    '''
    image = Image.open('rsa2.png')
    board.bg_image(Brightness(image).enhance(0.2), "fit")
    board.set_lanes(6)
    board.event(725, "GIRLS 12 & UNDER 100 BACK")
    board.heat(42)
    board.lane(1, "SWIMMER, FIRST", "TEAM1", 30.02, 1)
    board.lane(2, "SWIMMER, ANOTHER", "TEAM2", 900.47, 3)
    board.lane(3, "REALLYREALLYLONGNAME, IMA", "TEAM2", 1000.00, 4)
    board.lane(4, "SWIMMER, ANOTHER", "TEAM2", -900.47)
    board.lane(5, "VACANT", "NOTEAM", 0)
    board.lane(6, "SWIMMER, THELAST", "TEAM1", 90.30, 2)

def main():
    '''Display a scoreboard mockup'''
    root = tk.Tk()
    root.geometry("1366x768")
    board = Scoreboard(root)
    board.pack(fill='both', expand='yes')
    show_mockup(board)
    root.mainloop()

if __name__ == '__main__':
    main()
