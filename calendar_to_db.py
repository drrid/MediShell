# sync_calendar_to_db.py

# Import required libraries
import caldav
from caldav.elements import dav
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from conf import Encounter, Patient

# Load environment variables and setup database connection
load_dotenv()
password = os.getenv('DB_PASSWORD')
uri = os.getenv('URI')
nc_user = os.getenv('NC_USER')
nc_pass = os.getenv('NC_PASS')
nc_link = os.getenv('NC_LINK')

engine = create_engine(f'mysql+pymysql://root:{password}@{uri}', pool_recycle=3600)
Session = sessionmaker(bind=engine)

def synchronize_calendar_to_db():
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
            # Fetch events from the calendar
            events = calendar.events()

            # Add new encounters to the database
            for event in events:
                event_data = event.data
                # Parse event_data and extract relevant information (e.g., encounter_id, rdv, patient_name, note)

                # Check if the encounter already exists in the database (based on encounter_id)
                existing_encounter = session.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()

                if not existing_encounter:
                    # If encounter does not exist, create a new encounter and add it to the database
                    # Make sure to create the Patient object if it does not exist in the database
                    pass

        except Exception as e:
            print(f"Error synchronizing encounters from the calendar to the database: {e}")

if __name__ == "__main__":
    synchronize_calendar_to_db()
