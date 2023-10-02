import configparser
import smtplib
import mysql.connector
import time

config = configparser.ConfigParser()
config.read("data/config.conf")

# Database configuration
database_host = config.get('database', 'server')
database_username = config.get('database', 'username')
database_password = config.get('database', 'password')
database_name = config.get('database', 'database')

# Email configuration
email_server = config.get('email', 'server')
email_server_port = config.get('email', 'server_port')
email_server_use_ssl = bool(config.get('email', 'use_ssl'))
email_sender = config.get('email', 'sender')
email_password = config.get('email', 'sender_password')
email_recipients = config.get('email', 'recipients')

db_connection = mysql.connector.connect(host=database_host, user=database_username, password=database_password, database=database_name)
cursor = db_connection.cursor(dictionary=True)

def poll_database():
    last_id = str(load_last_id())
    query = "SELECT * FROM hardware_change_events WHERE ID > " + last_id + " ORDER BY ID"
    cursor.execute(query)
    hardware_change_event_list = cursor.fetchall()
    event_list_dictionary = {event["ID"]: event for event in hardware_change_event_list}
    
    # Send email if there are new results
    if hardware_change_event_list:
        query = "SELECT * FROM hardware_change_events_data WHERE EVENT_ID >= "+ str(hardware_change_event_list[0]["ID"]) + " ORDER BY EVENT_ID"
        cursor.execute(query)
        hardware_change_event_data_list = cursor.fetchall()

        # Format message
        message = "Se han detectado cambios en el hardware de los siguientes equipos:\n"
        current_event_id = 0
        for section_data in hardware_change_event_data_list:
            if current_event_id != section_data["EVENT_ID"]:
                current_event_id = section_data["EVENT_ID"]
                event_data = event_list_dictionary[current_event_id]
                message += "Equipo: " + str(event_data["NAME"]) + ", IP: " + str(event_data["IP_ADDRESS"]) +", Usuario: " + str(event_data["USERNAME"]) + "\n"
            
            message += "Seccion: " + section_data["SECTION"] + "\n"
            message += "Campos: " + section_data["FIELDS"] + "\n"
            message += "Hardware anadido: " + section_data["HARDWARE_ADDED"] + "\n"
            message += "Hardware removido: " + section_data["HARDWARE_REMOVED"] + "\n\n"
        
        # Send email
        smtp_server = smtplib.SMTP_SSL(email_server, email_server_port) if email_server_use_ssl else smtplib.SMTP(email_server, email_server_port)
        smtp_server.ehlo()
        smtp_server.login(email_sender, email_password)

        for recipient in email_recipients.split(","):
           sendmail(smtp_server, email_sender, recipient, message) 
        smtp_server.close()

        last_id = hardware_change_event_list[-1]["ID"]
        save_last_id(last_id)
    
    return last_id

def sendmail(mail_server, sender, recipient, message):
    content='From:' + sender + '\n' + 'To:' + recipient + '\n' + 'Subject:Cambio de Hardware detectado\n' + message
    mail_server.sendmail(email_sender, recipient, content)

def close_db_connection():
    cursor.close()
    db_connection.close()


# Writing the last ID to a file
def save_last_id(last_id):
    with open('data/last_id.txt', 'w') as f:
        f.write(str(last_id))

# Reading the last ID from a file
def load_last_id():
    try:
        with open('data/last_id.txt', 'r') as f:
            last_id = int(f.read())
    except Exception:
        last_id = 0
    return last_id

while True:
    poll_database()
    time.sleep(30)