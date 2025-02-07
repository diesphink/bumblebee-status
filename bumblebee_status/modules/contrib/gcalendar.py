"""Displays first upcoming event in google calendar.

Events that are set as 'all-day' will not be shown.

Requires credentials.json from a google api application where the google calendar api is installed.
On first time run the browser will open and google will ask for permission for this app to access the google calendar and then save a .gcalendar_token.json file to the credentials_path directory which stores this permission.

A refresh is done every 15 minutes.

Parameters:
    * gcalendar.time_format: Format time output. Defaults to "%H:%M".
    * gcalendar.date_format: Format date output. Defaults to "%d.%m.%y".
    * gcalendar.credentials_path: Path to credentials.json. Defaults to "~/".
    * gcalendar.locale: locale to use rather than the system default.
    * gcalendar.calendars: Comma separated list of calendar names that will be shown. Defaults to show all.

Requires these pip packages:
   * google-api-python-client >= 1.8.0
   * google-auth-httplib2 
   * google-auth-oauthlib
"""

# This import belongs to the google code
from __future__ import print_function

from dateutil.parser import parse as dtparse

import core.module
import core.widget
import core.decorators

import datetime
import os.path
import locale

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class Module(core.module.Module):
    @core.decorators.every(minutes=15)
    def __init__(self, config, theme):
        super().__init__(config, theme, core.widget.Widget(self.status))
        self.__time_format = self.parameter("time_format", "%H:%M")
        self.__date_format = self.parameter("date_format", "%d.%m.%y")
        self.__credentials_path = os.path.expanduser(
            self.parameter("credentials_path", "~/")
        )
        self.__credentials = os.path.join(self.__credentials_path, "credentials.json")
        self.__token = os.path.join(self.__credentials_path, ".gcalendar_token.json")

        l = locale.getdefaultlocale()
        if not l or l == (None, None):
            l = ("en_US", "UTF-8")
        lcl = self.parameter("locale", ".".join(l))
        try:
            locale.setlocale(locale.LC_TIME, lcl.split("."))
        except Exception:
            locale.setlocale(locale.LC_TIME, ("en_US", "UTF-8"))

        self.__calendars = self.parameter("calendars", None)
        if self.__calendars:
            self.__calendars = [x.strip() for x in self.__calendars.split(',')]
        self._events = []
        self._expanded = False

        core.input.register(self, button=core.input.LEFT_MOUSE, cmd=self.toggle, wait=True)


    def toggle(self, _):
        self._expanded = not self._expanded
        self.update()

    def status(self, widget):
        """Get status."""
        if self._expanded:
            return "  ".join(self._events)
        elif len(self._events) > 1:
            return f"{self._events[0]} (+{len(self._events) - 1})"
        elif len(self._events) == 1:
            return self._events[0]
        else:
            return ""
        return f'{self._status} ({self._expanded})'

    def update(self):
        """Update current state."""
        self._events = self.get_events()

    def hidden(self):
        return self._events == []

    def get_events(self):
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

        """Shows basic usage of the Google Calendar API.
        Prints the start and name of the next 10 events on the user's calendar.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.__token):
            creds = Credentials.from_authorized_user_file(self.__token, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.__credentials, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.__token, "w") as token:
                token.write(creds.to_json())

        # try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        end = (
            datetime.datetime.utcnow() + datetime.timedelta(days=7)
        ).isoformat() + "Z"  # 'Z' indicates UTC time
        # Get all calendars
        calendar_list = service.calendarList().list().execute()
        event_list = []
        for calendar_list_entry in calendar_list["items"]:
            if self.__calendars:
                if calendar_list_entry['summary'] not in self.__calendars:
                    continue

            calendar_id = calendar_list_entry["id"]
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    timeMax=end,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            for event in events:
                start = dtparse(
                    event["start"].get("dateTime", event["start"].get("date"))
                )
                # Only add to list if not an whole day event
                if start.tzinfo:
                    event_list.append(
                        {
                            "date": start,
                            "summary": event["summary"],
                            "type": event["eventType"],
                        }
                    )
        sorted_list = sorted(event_list, key=lambda t: t["date"])

        smaller_date = None
        events = []
        for gevent in sorted_list:
            if (gevent["date"] >= datetime.datetime.now(datetime.timezone.utc) 
                and (smaller_date is None  or smaller_date == gevent['date'].date())):
                if gevent["date"].date() == datetime.datetime.utcnow().date() or smaller_date is not None:
                    events.append(str(
                        "%s %s"
                        % (
                            gevent["date"]
                            .astimezone()
                            .strftime(f"{self.__time_format}"),
                            gevent["summary"],
                        )
                    ))
                else:
                    events.append(str(
                        "%s %s"
                        % (
                            gevent["date"]
                            .astimezone()
                            .strftime(f"{self.__date_format} {self.__time_format}"),
                            gevent["summary"],
                        )
                    ))
                smaller_date = gevent['date'].date()

        return events

        # except:
        #     return None


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
