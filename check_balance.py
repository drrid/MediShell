import re
import time
import serial

def send_sms(phone_number, message):
    # Convert phone number and message to UCS2 hex format
    ucs2_phone_number = phone_number.encode("utf-16be").hex()
    ucs2_message = message.encode("utf-16be").hex()

    # Set up the serial connection
    ser = serial.Serial('/dev/serial0', 9600, timeout=1)
    ser.flushInput()
    ser.flushOutput()

    # Set character set to UCS2 encoding
    ser.write(b'AT+CSCS="UCS2"\r')
    time.sleep(0.5)

    # Set modem to text mode
    ser.write(b'AT+CMGF=1\r')
    time.sleep(0.5)

    # Send SMS
    send_cmd = f'AT+CMGS="{ucs2_phone_number}"\r'
    ser.write(send_cmd.encode())
    time.sleep(0.5)

    ser.write(ucs2_message.encode() + b'\x1A')  # Add the <CTRL-Z> character (ASCII 26)
    time.sleep(7)

    response = ser.read(ser.in_waiting)
    ser.close()

    if b"+CMGS" in response:
        print("Message sent successfully!")
    else:
        print("Failed to send the message.")




def get_balance():
    ser = serial.Serial('/dev/serial0', 9600, timeout=1)
    ser.flushInput()
    ser.flushOutput()

    # Set character set to GSM encoding
    ser.write(b'AT+CSCS="GSM"\r')
    time.sleep(0.5)

    # Set modem to text mode
    ser.write(b'AT+CMGF=1\r')
    time.sleep(0.5)

    # Send USSD code
    ussd_code = "*200#"
    ussd_cmd = f'AT+CUSD=1,"{ussd_code}",15\r'
    ser.write(ussd_cmd.encode())
    time.sleep(7)

    response = ser.read(ser.in_waiting)
    ser.close()

    if b"+CUSD" in response:
        print("USSD request sent successfully!")
    else:
        print("Failed to send the USSD request.")
        return "Error: USSD request failed."

    balance_regex = re.compile(r"Crdit\s*:\s*([\d.]+DA)")
    balance = balance_regex.search(response.decode())

    if balance:
        return balance.group(1)
    else:
        return "Error: Balance not found."
    


balance = get_balance()
print(f"Your balance is: {balance}")
send_sms("+213671510693", f"Your balance is: {balance}")
