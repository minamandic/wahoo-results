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

"""Monitor the startlist directory"""

import logging
from typing import Callable

import watchdog.events  # type: ignore

CallbackFn = Callable[[], None]
CreatedCallbackFn = Callable[[str], None]

logger = logging.getLogger(__name__)


class SCBWatcher(watchdog.events.PatternMatchingEventHandler):
    """Monitors a directory for changes to CTS Startlist files"""

    def __init__(self, callback: CallbackFn):
        super().__init__(patterns=["*.scb"], ignore_directories=True)
        self._callback = callback

    def on_any_event(self, event: watchdog.events.FileSystemEvent):
        # Limit triggering to only events that modify the contents to avoid
        # creating a loop
        if event.event_type in [
            watchdog.events.EVENT_TYPE_CREATED,
            watchdog.events.EVENT_TYPE_DELETED,
            watchdog.events.EVENT_TYPE_MODIFIED,
            watchdog.events.EVENT_TYPE_MOVED,
        ]:
            logger.debug(
                "SCBWatcher: operation=%s, path=%s", event.event_type, event.src_path
            )
            self._callback()


class DO4Watcher(watchdog.events.PatternMatchingEventHandler):
    """Monitors a directory for new .do4 race result files"""

    def __init__(self, callback: CreatedCallbackFn):
        super().__init__(patterns=["*.do4"], ignore_directories=True)
        self._callback = callback

    def on_created(self, event: watchdog.events.FileCreatedEvent):
        logger.debug(
            "DO4Watcher: operation=%s, path=%s", event.event_type, event.src_path
        )
        self._callback(event.src_path)
