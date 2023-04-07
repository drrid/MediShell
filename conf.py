import sqlalchemy as db
from sqlalchemy.orm import relationship, declarative_base
import datetime as dt
from dotenv import load_dotenv
import os
from sqlalchemy import and_, func
from datetime import date, time, timedelta
import time as tm


load_dotenv()
password = os.getenv('DB_PASSWORD')
uri = os.getenv('URI')

engine = db.create_engine(f'mysql+pymysql://root:{password}@{uri}', pool_recycle=3600)
Base = declarative_base()
db_session = db.orm.sessionmaker(bind=engine)
session = db_session()

# Encounter Class -----------------------------------------------------------------------------------------------------------
class Encounter(Base):

    __tablename__ = "encounter"
    encounter_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer(), db.ForeignKey("patient.patient_id"))
    rdv = db.Column(db.DateTime())
    note = db.Column(db.String(100), default='')
    payment = db.Column(db.Integer(), default=0)
    treatment_cost = db.Column(db.Integer(), default=0)

    def __repr__(self):
        return f'{self.encounter_id},{self.rdv},{self.note},{self.payment},{self.treatment_cost}'

# Patient Class -----------------------------------------------------------------------------------------------------------
class patient(Base):

    __tablename__ = 'patient'
    patient_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.Integer())
    date_of_birth = db.Column(db.Date())
    encounters = relationship("Encounter")

    def __repr__(self):
        return f'{self.patient_id},{self.first_name},{self.last_name},{self.date_of_birth},{self.phone}'

#---------------------------------------------------------------------------------------------------------------------------


def init_db():
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine


def update_patient(patient_id, **kwargs):
    try:
        patient_to_update = session.query(patient).filter(patient.patient_id == patient_id).one()

        for key, value in kwargs.items():
            setattr(patient_to_update, key, value)

        session.commit()
    except Exception as e:
        print(e)
        session.rollback()

def save_to_db(record):
    try:
        session.add(record)
        session.commit()
    except Exception as e:
        session.rollback()
        print(e) 

def update_encounter(id, **kwargs):
    try:
        session.query(Encounter).filter(Encounter.encounter_id == id).update(kwargs)
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)

def delete_encounter(encounter_id):
    try:
        encounter_to_delete = session.query(Encounter).filter(Encounter.encounter_id == encounter_id).one()
        session.delete(encounter_to_delete)
        session.commit()
    except Exception as e:
        print(e)
        session.rollback()

def select_all_starts_with(**kwargs):
    try:
        filters = [getattr(patient, key).startswith(value) for key, value in kwargs.items()]
        return [(str(r.patient_id), str(r.first_name), str(r.last_name), str(r.date_of_birth), str(r.phone)) for r in session.query(patient).filter(*filters)]
    except Exception as e:
        print(e)

def select_encounter_by_rdv(rdv):
    try:
        encounter = session.query(Encounter).filter(Encounter.rdv == rdv).one()
        return encounter
    except Exception as e:
        print(f"Error selecting encounter by rdv: {e}")
        return None
    
def select_all_pt_encounters(id):
    try:
        return [(str(r.encounter_id), str(r.rdv), str(r.note), str(r.payment), str(r.treatment_cost)) for r in session.query(Encounter).filter(Encounter.patient_id == id).order_by(Encounter.rdv).all()]
    except Exception as e:
        print(e)

def select_patient_encounters(id):
    try:
        return session.query(Encounter).filter(Encounter.patient_id == id).all()
    except Exception as e:
        print(e)


def calculate_owed_amount(patient_id):
    try:
        patient_encounters = select_patient_encounters(patient_id)
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
    encounters = session.query(Encounter, patient).join(patient).filter(
        and_(
            Encounter.rdv >= dt.datetime.combine(start_date, time_slots[0][0]),
            Encounter.rdv < dt.datetime.combine(end_date, time_slots[-1][1]),
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


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# def read_patients_from_file(file_path):
#     with open(file_path, 'r') as f:
#         lines = f.readlines()

#     patients = []

#     for line in lines:
#         data = line.strip().split(',')
#         first_name, last_name, phone, dob = data
#         date_of_birth = dt.datetime.strptime(dob, '%Y-%m-%d').date()
#         patient2 = patient(first_name=first_name, last_name=last_name, phone=phone, date_of_birth=date_of_birth)
#         patients.append(patient2)

#     return patients


# def read_encounters_from_file(file_path):
#     with open(file_path, 'r') as f:
#         lines = f.readlines()

#     encounters = []

#     for line in lines:
#         data = line.strip().split(',')
#         patient_id, rdv, note, payment, treatment_cost = data
#         rdv = dt.datetime.strptime(rdv, '%Y-%m-%d %H:%M:%S')
#         payment = int(payment)
#         treatment_cost = int(treatment_cost)
#         encounter = Encounter(patient_id=patient_id, rdv=rdv, note=note, payment=payment, treatment_cost=treatment_cost)
#         encounters.append(encounter)

#     return encounters


# patients = read_patients_from_file('patients.txt')
# encounters = read_encounters_from_file('encounters.txt')

# for patient in patients:
#     save_to_db(patient)

# for encounter in encounters:
#     save_to_db(encounter)

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------





