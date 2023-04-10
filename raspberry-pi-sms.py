import os
import time
import serial
import datetime
import schedule
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Date, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# 1. Install the required packages
# pip install sqlalchemy mysql-connector-python pyserial

# 2. Set up the MySQL connection and SQLAlchemy configuration
db_url = "mysql+pymysql://user:pass@192.168.5.225:3306/pms"
engine = create_engine(db_url)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# 2.  Define your classes
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

# 3. Create the SMS sending function using the modem and AT commands
def send_sms(phone_number, message):
    modem = serial.Serial('/dev/serial0', 9600, timeout=1)
    modem.write(b'AT+CMGF=1\r')  # Set modem to text mode
    time.sleep(1)
    modem.write(f'AT+CMGS="{phone_number}"\r'.encode())  # Set the recipient
    time.sleep(1)
    modem.write(message.encode() + b'\x1A')  # Send the message and the CTRL+Z character
    time.sleep(1)
    modem.close()

# 4. Create a function to query the database for new encounters
def send_sms_for_new_encounters():
    now = datetime.datetime.now()
    one_hour_later = now + datetime.timedelta(hours=1)
    new_encounters = session.query(Encounter).join(Patient).filter(Encounter.rdv.between(now, one_hour_later), Encounter.notified == False).all()

    for encounter in new_encounters:
        if not encounter.notified:  # Check the notified status before sending the message
            patient = encounter.patient
            message = f"Dear {patient.first_name} {patient.last_name}, you have an appointment today at {encounter.rdv.strftime('%H:%M')}. Please, don't be late."
            send_sms(patient.phone, message)
            encounter.notified = True
            session.commit()

# 5. Schedule the script to run periodically
if __name__ == "__main__":
    send_sms_for_new_encounters()

# 6. Set up the script to run automatically on Raspberry Pi startup
# Add the following line to the '/etc/rc.local' file, before 'exit 0':
# python3 /path/to/your/script.py &