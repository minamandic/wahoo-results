# Wahoo! Results - https://github.com/JohnStrunk/wahoo-results
# Copyright (C) 2022 - John D. Strunk
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

'''Wahoo Results!'''

import copy
import datetime
import os
import re
from time import sleep
from tkinter import Tk, messagebox
from typing import List, Optional
from watchdog.observers import Observer #type: ignore

import main_window
import imagecast
from model import Model
from racetimes import RaceTimes, RawTime, from_do4
from scoreboard import ScoreboardImage, waiting_screen
from startlist import StartList, from_scb
from template import get_template
import widgets
from watcher import DO4Watcher, SCBWatcher

CONFIG_FILE = "wahoo-results.ini"

def main():
    '''Main program'''
    root = Tk()

    model = Model()
    model.load(CONFIG_FILE)
    main_window.View(root, model)

    # Exit menu exits app
    def exit_fn():
        try:
            model.save(CONFIG_FILE)
        except PermissionError as err:
            messagebox.showerror(title="Error saving configuration",
                message=f'Unable to write configuration file "{err.filename}". {err.strerror}',
                detail="Please ensure the working directory is writable.")
        root.destroy()

    model.menu_exit.add(exit_fn)

    # Connections for the appearance tab
    setup_appearance(model)

    # Connections for the directories tab
    scb_observer = Observer()
    scb_observer.start()
    setup_scb_watcher(model, scb_observer)

    do4_observer = Observer()
    do4_observer.start()
    setup_do4_watcher(model, do4_observer)

    # Connections for the run tab
    icast = imagecast.ImageCast(9998)
    setup_run(model, icast)
    icast.start()

    # Set initial scoreboard image
    model.scoreboard.set(waiting_screen(imagecast.IMAGE_SIZE, model))

    root.mainloop()

    scb_observer.stop()
    scb_observer.join()
    do4_observer.stop()
    do4_observer.join()
    icast.stop()

def setup_appearance(model: Model) -> None:
    '''Link model changes to the scoreboard preview'''
    def update_preview() -> None:
        preview = ScoreboardImage(imagecast.IMAGE_SIZE, get_template(), model)
        model.appearance_preview.set(preview.image)
    for element in [
        model.font_normal,
        model.font_time,
        model.text_spacing,
        model.title,
        model.image_bg,
        model.color_title,
        model.color_event,
        model.color_even,
        model.color_odd,
        model.color_first,
        model.color_second,
        model.color_third,
        model.color_bg,
        model.num_lanes,
    ]: element.trace_add("write", lambda *_: update_preview())
    update_preview()

def setup_scb_watcher(model: Model, observer: Observer) -> None:
    '''Set up file system watcher for startlists'''
    def process_startlists() -> None:
        '''
        Load all the startlists from the current directory and update the UI
        with their information.
        '''
        directory = model.dir_startlist.get()
        files = os.scandir(directory)
        startlists: List[StartList] = []
        for file in files:
            if file.name.endswith(".scb"):
                try:
                    startlist = from_scb(file.path)
                    startlists.append(startlist)
                except ValueError:
                    pass
        startlists.sort(key=lambda l: l.event_num)
        contents: widgets.StartListType = []
        for startlist in startlists:
            contents.append({
                'event': str(startlist.event_num),
                'desc': startlist.event_name,
                'heats': str(startlist.heats),
            })
        model.startlist_contents.set(contents)

    def scb_dir_updated() -> None:
        '''
        When the startlist directory is changed, update the watched to look at
        the new directory and trigger processing of the startlists.
        '''
        path = model.dir_startlist.get()
        if not os.path.exists(path):
            return
        observer.unschedule_all()
        observer.schedule(SCBWatcher(process_startlists), path)
        process_startlists()

    model.dir_startlist.trace_add("write", lambda *_: scb_dir_updated())
    scb_dir_updated()

def setup_do4_watcher(model: Model, observer: Observer) -> None:
    '''Set up watches for files/directories and connect to model'''
    def process_racedir() -> None:
        '''
        Load all the race results and update the UI
        '''
        directory = model.dir_results.get()
        files = os.scandir(directory)
        contents: widgets.RaceResultType = []
        for file in files:
            if file.name.endswith(".do4"):
                match = re.match(r'^(\d+)-', file.name)
                if match is None:
                    continue
                try:
                    racetime = from_do4(file.path, 2, RawTime("0.30"))
                    contents.append({
                        'meet': match.group(1),
                        'event': str(racetime.event),
                        'heat': str(racetime.heat),
                        'time': str(datetime.datetime.fromtimestamp(file.stat().st_mtime))
                    })
                except ValueError:
                    pass
                except OSError:
                    pass
        model.results_contents.set(contents)

    def process_new_result(file: str) -> None:
        '''Process a new race result that has been detected'''
        racetime: Optional[RaceTimes] = None
        # Retry mechanism since we get errors if we try to read while it's
        # still being written.
        for tries in range(1, 6):
            try:
                racetime = from_do4(file, 2, RawTime("0.30"))
            except ValueError:
                sleep(0.05 * tries)
            except OSError:
                sleep(0.05 * tries)
        if racetime is None:
            return
        efilename = f"E{racetime.event:0>3}.scb"
        try:
            startlist = from_scb(os.path.join(model.dir_startlist.get(), efilename))
            racetime.set_names(startlist)
        except OSError:
            pass
        except ValueError:
            pass
        scoreboard = ScoreboardImage(imagecast.IMAGE_SIZE, racetime, model)
        model.scoreboard.set(scoreboard.image)
        process_racedir()  # update the UI

    def do4_dir_updated() -> None:
        '''
        When the raceresult directory is changed, update the watch to look at
        the new directory and trigger processing of the results.
        '''
        path = model.dir_results.get()
        if not os.path.exists(path):
            return
        observer.unschedule_all()
        observer.schedule(DO4Watcher(process_new_result), path)
        process_racedir()

    model.dir_results.trace_add("write", lambda *_: do4_dir_updated())
    do4_dir_updated()

def setup_run(model: Model, icast: imagecast.ImageCast) -> None:
    '''Link Chromecast discovery/management to the UI'''
    def cast_discovery() -> None:
        dev_list = copy.deepcopy(icast.get_devices())
        model.cc_status.set(dev_list)
    def update_cc_list() -> None:
        dev_list = model.cc_status.get()
        for dev in dev_list:
            icast.enable(dev['uuid'], dev['enabled'])
    model.cc_status.trace_add("write", lambda *_: update_cc_list())
    icast.set_discovery_callback(cast_discovery)

    # Link Chromecast contents to the UI preview
    model.scoreboard.trace_add("write", lambda *_: icast.publish(model.scoreboard.get()))

if __name__ == "__main__":
    main()
