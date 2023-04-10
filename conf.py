from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Boolean, ForeignKey, and_
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
import os
from datetime import date, time, timedelta, datetime


load_dotenv()
password = os.getenv('DB_PASSWORD')
uri = os.getenv('URI')

engine = create_engine(f'mysql+pymysql://root:{password}@{uri}', pool_recycle=3600)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Encounter Class -----------------------------------------------------------------------------------------------------------
class Encounter(Base):

    __tablename__ = "encounter"
    encounter_id = Column(Integer(), primary_key=True, autoincrement=True)
    patient_id = Column(Integer(), ForeignKey("patient.patient_id"))
    rdv = Column(DateTime())
    notified = Column(Boolean, default=False)
    note = Column(String(100), default='')
    payment = Column(Integer(), default=0)
    treatment_cost = Column(Integer(), default=0)
    patient = relationship("Patient", back_populates="encounters")

    def __repr__(self):
        return f'{self.encounter_id},{self.rdv},{self.note},{self.payment},{self.treatment_cost}'

# Patient Class -----------------------------------------------------------------------------------------------------------
class Patient(Base):

    __tablename__ = 'patient'
    patient_id = Column(Integer(), primary_key=True, autoincrement=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    phone = Column(Integer())
    date_of_birth = Column(Date())
    encounters = relationship("Encounter")

    def __repr__(self):
        return f'{self.patient_id},{self.first_name},{self.last_name},{self.date_of_birth},{self.phone}'

#---------------------------------------------------------------------------------------------------------------------------


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine


def update_patient(patient_id, **kwargs):
    """Update the patient with the given ID using the provided keyword arguments."""
    with Session() as session:
        try:
            patient_to_update = session.query(Patient).filter(Patient.patient_id == patient_id).one()

            for key, value in kwargs.items():
                setattr(patient_to_update, key, value)

            session.commit()
        except Exception as e:
            print(e)
            session.rollback()

def save_to_db(record):
    """Save the given record to the database."""
    with Session() as session:
        try:
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            print(e)

def update_encounter(encounter_id, **kwargs):
    """Update the encounter with the given ID using the provided keyword arguments."""
    with Session() as session:
        try:
            session.query(Encounter).filter(Encounter.encounter_id == encounter_id).update(kwargs)
            session.commit()
        except Exception as e:
            session.rollback()
            print(e)


def delete_encounter(encounter_id):
    with Session() as session:
        try:
            encounter_to_delete = session.query(Encounter).filter(Encounter.encounter_id == encounter_id).one()
            session.delete(encounter_to_delete)
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()

def select_all_starts_with(**kwargs):
    with Session() as session:
        try:
            filters = [getattr(Patient, key).startswith(value) for key, value in kwargs.items()]
            return [(str(r.patient_id), str(r.first_name), str(r.last_name), str(r.date_of_birth), str(r.phone)) for r in session.query(Patient).filter(*filters)]
        except Exception as e:
            print(e)


def select_encounter_by_rdv(rdv):
    with Session() as session:
        try:
            encounter = session.query(Encounter).filter(Encounter.rdv == rdv).one()
            return encounter
        except Exception as e:
            print(f"Error selecting encounter by rdv: {e}")
            return None
    
def select_all_pt_encounters(patient_id):
    with Session() as session:
        try:
            return [(str(r.encounter_id), str(format_timestamp(r.rdv)), str(r.note), str(r.payment), str(r.treatment_cost)) for r in session.query(Encounter).filter(Encounter.patient_id == patient_id).order_by(Encounter.rdv).all()]
        except Exception as e:
            print(e)

def format_timestamp(timestamp):
    # dt_object = dt.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    formatted_timestamp = timestamp.strftime('%d %b %H:%M')
    return formatted_timestamp

def select_pt_encounter(encounter_id):
    with Session() as session:
        try:
            return [(str(r.encounter_id), str(format_timestamp(r.rdv)), str(r.note), str(r.payment), str(r.treatment_cost)) for r in session.query(Encounter).filter(Encounter.encounter_id == encounter_id).order_by(Encounter.rdv).all()]
        except Exception as e:
            print(e)

def select_patient_by_details(first_name, last_name, phone, date_of_birth):
    with Session() as session:
        try:
            patient2 = session.query(Patient).filter(Patient.first_name == first_name,
                                                    Patient.last_name == last_name,
                                                    Patient.phone == phone,
                                                    Patient.date_of_birth == date_of_birth).first()
            return patient2
        except Exception as e:
            print(f"Error selecting patient by details: {e}")
            return None


def calculate_owed_amount(patient_id):
    try:
        patient_encounters = select_all_pt_encounters(patient_id)
        total_treatment_cost = sum(encounter.treatment_cost for encounter in patient_encounters)
        total_payments = sum(encounter.payment for encounter in patient_encounters)

        owed_amount = total_treatment_cost - total_payments

        return owed_amount
    except Exception as e:
        print(e)
        return None


def generate_time_slot(start_hour, start_minute, duration, count):
    time_slots = []
    current_time = time(hour=start_hour, minute=start_minute)

    for _ in range(count):
        next_time_minute = current_time.minute + duration
        next_time_hour = current_time.hour + next_time_minute // 60
        next_time = time(hour=next_time_hour % 24, minute=next_time_minute % 60)
        time_slots.append((current_time, next_time))
        current_time = next_time

    return time_slots


def generate_schedule(week_index):
    today = date.today()
    # Find the nearest Saturday (0 = Saturday, 1 = Sunday, etc.)
    days_to_saturday = (5 - today.weekday()) % 7
    start_date = today + timedelta(days=days_to_saturday) + timedelta(weeks=week_index - 1)
    end_date = start_date + timedelta(days=7)
    
    # Generate time slots
    time_slots = generate_time_slot(9, 0, 20, 21)
    
    schedule = []
    
    # Add days of the week with their respective dates
    days_of_week = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    schedule.append((" ", *tuple(f"{days_of_week[i]} {(start_date + timedelta(days=i)).strftime('%d %b %y').lstrip('0')}" for i in range(7))))
    
    # Fetch all encounters for the whole week
    with Session() as session:
        encounters = session.query(Encounter, Patient).join(Patient).filter(
            and_(
                Encounter.rdv >= datetime.combine(start_date, time_slots[0][0]),
                Encounter.rdv < datetime.combine(end_date, time_slots[-1][1]),
            )
        ).all()

    # Group encounters by time slot
    encounter_map = {}
    for encounter, pat in encounters:
        time_slot_index = (encounter.rdv.hour - 9) * 3 + encounter.rdv.minute // 20
        day_index = (encounter.rdv.date() - start_date).days
        encounter_map[(time_slot_index, day_index)] = f"{pat.first_name} {pat.last_name}"
    
    for i, time_slot in enumerate(time_slots):
        slot_start, slot_end = time_slot
        encounters_in_slot = [encounter_map.get((i, j), "_") for j in range(7)]

        schedule.append((slot_start.strftime('%H:%M'), *encounters_in_slot))
    
    return schedule


init_db()






