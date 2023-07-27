# sync_db_to_calendar.py

# Import required libraries
import caldav
from caldav.elements import dav
from datetime import timedelta, datetime
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from conf import Encounter

# Load environment variables and setup database connection
load_dotenv()
password = os.getenv('DB_PASSWORD')
uri = os.getenv('URI')
nc_user = os.getenv('NC_USER')
nc_pass = os.getenv('NC_PASS')
nc_link = os.getenv('NC_LINK')

engine = create_engine(f'mysql+pymysql://root:{password}@{uri}', pool_recycle=3600)
Session = sessionmaker(bind=engine)


def synchronize_db_to_calendar():
    # Connect to the Nextcloud CalDAV server
    client = caldav.DAVClient(f"https://{nc_link}/remote.php/dav/calendars/{nc_user}/", username=nc_user, password=nc_pass)

    # Get the calendar
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise ValueError("No calendars found on the server.")
    calendar = calendars[0]  # Assuming we're working with the first calendar found

    with Session() as session:
        try:
            # Fetch new encounters from the database that are not synced to the calendar
            new_encounters = session.query(Encounter).filter(
                and_(
                    Encounter.rdv >= datetime.now(),
                    Encounter.synced_to_calendar == False  # Only fetch encounters not synced to the calendar
                )
            ).all()

            # Add new encounters to the calendar
            for encounter in new_encounters:
                event_summary = f"Encounter With {encounter.patient.first_name} {encounter.patient.last_name}"
                event_description = f"Note: {encounter.note}"


 
                event_data = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp.//CalDAV Client//EN
BEGIN:VEVENT
SUMMARY:{event_summary}
DESCRIPTION:{event_description}
DTSTART:{encounter.rdv.strftime('%Y%m%dT%H%M%S')}
DTEND:{(encounter.rdv + timedelta(minutes=20)).strftime('%Y%m%dT%H%M%S')}
END:VEVENT
END:VCALENDAR
"""
                try:
                    calendar.add_event(event_data)
                    # Mark the encounter as synced in the database
                    encounter.synced_to_calendar = True
                    session.commit()
                    print(f"Encounter {encounter.encounter_id} successfully saved to the calendar.")
                except Exception as e:
                    print(f"Error saving the encounter to the calendar: {e}")

        except Exception as e:
            print(f"Error synchronizing encounters from the database to the calendar: {e}")



if __name__ == "__main__":
    synchronize_db_to_calendar()
