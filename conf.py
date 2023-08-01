from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Boolean, ForeignKey, and_, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
import os
from datetime import date, time, timedelta, datetime
import time as tm
from sys import platform
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
password = os.getenv('DB_PASSWORD')
uri = os.getenv('URI')
nc_user = os.getenv('NC_USER')
nc_pass = os.getenv('NC_PASS')
nc_link = os.getenv('NC_LINK')

engine = create_engine(f'mysql+pymysql://root:{password}@{uri}', pool_recycle=3600)

# engine = create_engine('sqlite:///database.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)


# Patient Class -----------------------------------------------------------------------------------------------------------
class PrescriptionFile(Base):
    __tablename__ = "prescription_file"
    id = Column(Integer(), primary_key=True, autoincrement=True)
    encounter_id = Column(Integer(), ForeignKey("encounter.encounter_id"))
    file_path = Column(String(255))
    prescription_type = Column(String(100))
    encounter = relationship("Encounter", back_populates="prescription_files")

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
    prescription_files = relationship("PrescriptionFile", order_by=PrescriptionFile.id, back_populates="encounter")
    synced_to_calendar = Column(Boolean, default=False)

    def unsync_to_calendar(self):
        self.synced_to_calendar = False

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

    def get_owed_money(self):
        with Session() as session:
            try:
                # Get the total treatment cost for the patient
                total_treatment_cost = session.query(func.sum(Encounter.treatment_cost)).filter(
                    Encounter.patient_id == self.patient_id
                ).scalar() or 0

                # Get the total payments made by the patient
                total_payments = session.query(func.sum(Encounter.payment)).filter(
                    Encounter.patient_id == self.patient_id
                ).scalar() or 0

                # Calculate the owed money (all fees - all payments)
                owed_money = total_treatment_cost - total_payments
                return owed_money
            except Exception as e:
                print(f"Error getting patient owed money: {e}")
                return None

    def __repr__(self):
        owed_money = self.get_owed_money()
        return f'{self.patient_id},{self.first_name},{self.last_name},{self.date_of_birth},{self.phone},{owed_money}'
        # return f'{self.patient_id},{self.first_name},{self.last_name},{self.date_of_birth},{self.phone}'
#---------------------------------------------------------------------------------------------------------------------------


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine

def get_last_patient_encounter(patient_id):
    with Session() as session:
        try:
            last_encounter = session.query(Encounter).filter(
                Encounter.patient_id == patient_id
            ).order_by(Encounter.rdv.desc()).first()
            return last_encounter
        except Exception as e:
            print(f"Error getting the last patient encounter: {e}")
            return None

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
            generated_id = record.patient_id
            return generated_id
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
            return [(str(r.patient_id), str(r.first_name), str(r.last_name), str(r.date_of_birth), str(r.phone), str(r.get_owed_money())) for r in session.query(Patient).filter(*filters)]
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
        
def select_all_patients():
    with Session() as session:
        try:
            patients = session.query(Patient).all()
            return patients
        except Exception as e:
            print(f"Error selecting patients: {e}")
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
            patient = session.query(Patient).filter(Patient.first_name == first_name,
                                                    Patient.last_name == last_name,
                                                    Patient.phone == phone,
                                                    Patient.date_of_birth == date_of_birth).first()
            return patient
        except Exception as e:
            print(f"Error selecting patient by details: {e}")
            return None

def select_patient_by_id(patient_id):
    with Session() as session:
        try:
            patient = session.query(Patient).filter(Patient.patient_id == patient_id).first()
            return patient
        except Exception as e:
            print(f"Error selecting patient by details: {e}")
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
    days_to_saturday = (today.weekday()-5) % 7
    start_date = today - timedelta(days=days_to_saturday) + timedelta(weeks=week_index)
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

        if today == encounter.rdv.date():
            encounter_map[(time_slot_index, day_index)] = f"[bold yellow]{pat.first_name} {pat.last_name}"
            if '%' in encounter.note:
                encounter_map[(time_slot_index, day_index)] = f"[bold yellow underline]{pat.first_name} {pat.last_name}"
                
        elif '%' in encounter.note:
            encounter_map[(time_slot_index, day_index)] = f"[bold underline]{pat.first_name} {pat.last_name}"
        else:
            encounter_map[(time_slot_index, day_index)] = f"{pat.first_name} {pat.last_name}"

    
    for i, time_slot in enumerate(time_slots):
        slot_start, slot_end = time_slot
        encounters_in_slot = [encounter_map.get((i, j), "_") for j in range(7)]

        schedule.append((slot_start.strftime('%H:%M'), *encounters_in_slot))
    
    return schedule


def calculate_age(dob):
    today = date.today()
    years = today.year - dob.year
    months = today.month - dob.month

    # Adjust for cases where the birthday hasn't occurred yet in the current month
    if today.day < dob.day:
        months -= 1

    # Adjust for cases where the current month is earlier than the birth month
    if today.month < dob.month:
        years -= 1
        months += 12

    return f"{years} ans {months} mois"


def generate_prescription_png(patient, selection):
    try:
        if platform == 'darwin':
            pt_dir = f'/Volumes/mediaserver/patients/{patient[0]} {patient[1]} {patient[2]}'
        else:
            pt_dir = f'Z:\\patients\\{patient[0]} {patient[1]} {patient[2]}'

        output_filename = os.path.join(pt_dir, f"{selection}.png")

        # Load the PNG template (replace 'prescription_template.png' with your actual template path)

        template_path = f"templates/{selection}.png"
        dob = datetime.strptime(patient[3], "%Y-%m-%d").date()
        age = calculate_age(dob)
        today = date.today()
        formatted_date = today.strftime("%d-%m-%Y")

        template_image = Image.open(template_path)

        # Create a new transparent image with the same size as the template
        output_image = Image.new("RGBA", template_image.size, (0, 0, 0, 0))

        # Paste the template on the new transparent image
        output_image.paste(template_image, (0, 0))

        # Set font and size for patient name and age
        font = ImageFont.truetype("arial.ttf", 40)
        draw = ImageDraw.Draw(output_image)

        # Add patient name and age to the image
        draw.text((394, 480), f"{patient[1]} {patient[2]}", font=font, fill=(0, 0, 0, 255))
        draw.text((1180, 480), f"{age}", font=font, fill=(0, 0, 0, 255))
        draw.text((1180, 540), f"{formatted_date}", font=font, fill=(0, 0, 0, 255))

        # Save the output image as PNG
        output_image.save(output_filename)
    except Exception as e:
        print(e)
        return e


init_db()

# generate_prescription_png(5, 'pano')