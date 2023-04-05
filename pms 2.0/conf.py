import sqlalchemy as db
from sqlalchemy.orm import relationship, declarative_base
import datetime as dt
from datetime import timedelta
import numpy as np
from dotenv import load_dotenv
import os


from sqlalchemy import and_, func
from datetime import date, time, timedelta


load_dotenv()
password = os.getenv('DB_PASSWORD')
uri = os.getenv('URI')

engine = db.create_engine(f'mysql+pymysql://root:{password}@{uri}')
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

def select_one_first_name(first_name):
    try:
        return session.query(patient).filter_by(patient.first_name == first_name).one()
    except Exception as e:
        print(e)

def select_one_id(id):
    try:
        return session.query(patient).filter(patient.patient_id == id).one()
    except Exception as e:
        print(e)

def select_all(first_name):
    try:
        return session.query(patient).filter_by(patient.first_name == first_name).all()
    except Exception as e:
        print(e)

def select_all_contains(first_name):
    try:
        return session.query(patient).filter(patient.first_name.contains(first_name))
    except Exception as e:
        print(e)

def select_all_starts_with(**kwargs):
    try:
        filters = [getattr(patient, key).startswith(value) for key, value in kwargs.items()]
        return [(str(r.patient_id), str(r.first_name), str(r.last_name), str(r.date_of_birth), str(r.phone)) for r in session.query(patient).filter(*filters)]
    except Exception as e:
        print(e)

def select_all_encounters():
    try:
        return session.query(Encounter).all()
    except Exception as e:
        print(e)

def select_encounter(q):
    try:
        return session.query(Encounter).filter(Encounter.rdv == q.rdv).one()
    except Exception as e:
        print(e)

def select_all_pt_encounters(id):
    try:
        return [(str(r.encounter_id), str(r.rdv), str(r.note), str(r.payment), str(r.treatment_cost)) for r in session.query(Encounter).filter(Encounter.patient_id == id).all()]
    except Exception as e:
        print(e)

def select_week_encounters(start, end):
    try:
        return session.query(Encounter).filter(Encounter.rdv.between(start, end)).all()
    except Exception as e:
        print(e)

def select_patient_encounters(id):
    try:
        return session.query(Encounter).filter(Encounter.patient_id == id).all()
    except Exception as e:
        print(e)

def get_weekly_start_end(ind):
    # print(ind)
    if ind < 0:
        today_date = dt.datetime.today() - timedelta(days=ind*-6)
    else:
        today_date = dt.datetime.today() + timedelta(days=ind*6)

    SHIFTED_INDEX = {0:2, 1:3, 2:4, 3:5, 4:6, 5:0, 6:1}

    today_index = today_date.weekday()
    shifted_index = SHIFTED_INDEX[today_index]
    current_week = today_date - timedelta(days=shifted_index)

    hour_start = 0
    minute_start = 0
    day_start = current_week.day
    year_start = current_week.year
    month_start = current_week.month

    current_week_start = dt.datetime(year_start, month_start, day_start, hour_start, minute_start)
    current_week_end = current_week_start + timedelta(days=6)

    day_end = current_week_end.day
    year_end = current_week_end.year
    month_end = current_week_end.month
    hour_end = 23
    minute_end = 59
    current_week_end_final = dt.datetime(year_end, month_end, day_end, hour_end, minute_end)
    
    return (current_week_start, current_week_end_final)


import numpy as np

def get_weekly_encounters_formatted(result):
    formatted_data = [("time", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")]
    
    rows = ['9:00', '9:20', '9:40', '10:00', '10:20', '10:40',
            '11:00', '11:20', '11:40', '12:00', '12:20', '12:40',
            '13:00', '13:20', '13:40', '14:00', '14:20', '14:40',
            '15:00', '15:20', '15:40']

    dict_row = {'9:0': 0, '9:20': 1, '9:40': 2, '10:0': 3, '10:20': 4, '10:40': 5,
                '11:0': 6, '11:20': 7, '11:40': 8, '12:0': 9, '12:20': 10, '12:40': 11,
                '13:0': 12, '13:20': 13, '13:40': 14, '14:0': 15, '14:20': 16, '14:40': 17,
                '15:0': 18, '15:20': 19, '15:40': 20}

    dict_column = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 0, 6: 1}

    weekly_matrix = np.full((21, 7), dtype=object, fill_value='_')

    if result is not None:
        for r in result:
            rdv_time = f'{r.rdv.hour}:{r.rdv.minute}'
            row = dict_row[rdv_time]
            clm = dict_column[r.rdv.weekday()]
            patient = select_one_id(r.patient_id)
            encounter_info = (patient.first_name, patient.last_name, patient.patient_id, r.encounter_id)
            weekly_matrix[row, clm] = encounter_info

    for i, row in enumerate(rows):
        formatted_row = [row] + list(weekly_matrix[i])
        formatted_data.append(tuple(formatted_row))

    return formatted_data


def get_weekly_encounters_csv(result):
    rows = ['9:00', '9:20', '9:40', '10:00', '10:20', '10:40',
            '11:00', '11:20', '11:40', '12:00', '12:20', '12:40',
            '13:00', '13:20', '13:40', '14:00', '14:20', '14:40',
            '15:00', '15:20', '15:40']

    dict_row = {'9:0': 0, '9:20': 1, '9:40': 2, '10:0': 3, '10:20': 4, '10:40': 5,
                '11:0': 6, '11:20': 7, '11:40': 8, '12:0': 9, '12:20': 10, '12:40': 11,
                '13:0': 12, '13:20': 13, '13:40': 14, '14:0': 15, '14:20': 16, '14:40': 17,
                '15:0': 18, '15:20': 19, '15:40': 20}

    dict_column = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 0, 6: 1}

    coor_array = []
    patients = []

    weekly_matrix = np.full((21, 7), dtype=object, fill_value='_')

    if result is not None:
        for r in result:
            rdv_time = f'{r.rdv.hour}:{r.rdv.minute}'
            row = dict_row[rdv_time]
            clm = dict_column[r.rdv.weekday()]
            coor_array.append([row, clm])
            patient = select_one_id(r.patient_id)
            patients.append(f'{patient.first_name} {patient.last_name} {patient.patient_id} {r.encounter_id}')

        for i, (x, y) in enumerate(coor_array):
            weekly_matrix[x, y] = patients[i]
        arr2 = weekly_matrix.flatten()

        for i, v in enumerate(arr2):
            index = int(i / 7)
            rows[index] = rows[index] + ',' + str(v)

        print(len(rows[0]))
        pretty = '\n'.join(rows)
        return pretty


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
    
    # Generate time slots
    time_slots = generate_time_slot(9, 0, 20, 21)
    
    schedule = []
    
    for time_slot in time_slots:
        slot_start, slot_end = time_slot
        encounters_in_slot = ["_"] * 7  # Initialize empty encounters for the week

        for i in range(7):
            day_start = dt.datetime.combine(start_date + timedelta(days=i), slot_start)
            day_end = dt.datetime.combine(start_date + timedelta(days=i), slot_end)
            
            encounters = session.query(Encounter, patient).join(patient).filter(
                and_(
                    Encounter.rdv >= day_start,
                    Encounter.rdv < day_end
                )
            ).all()
            
            if encounters:
                encounter, pat = encounters[0]  # Assuming only one encounter per time slot
                encounters_in_slot[i] = f"{pat.first_name} {pat.last_name} {encounter.encounter_id} {pat.patient_id}"
        
        schedule.append((slot_start.strftime('%H:%M'), *encounters_in_slot))
    
    return schedule


init_db()


# patient_id = 1
# owed_amount = calculate_owed_amount(patient_id)
# print(f"The owed amount for patient {patient_id} is: {owed_amount}")





# start, end = get_weekly_start_end(0)
# enc = select_week_encounters(start, end)
# rows = get_weekly_encounters_csv(enc)
# print(rows)
results = generate_schedule(0)
print(results)
for r in results:
    print(r)

# patients = select_all_starts_with(first_name='abd')
# print(patients)
# for patient in patients:
#     print(patient)


