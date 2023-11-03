import configparser
import smtplib
import mysql.connector
import time
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage

config = configparser.ConfigParser()
config.read("data/config.conf")

#General config
ocsinventory_server_url = config.get('general', 'ocsinventory_server_url')
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

def main():
    events_list, events_data_list = poll_database()
    if len(events_list) == 0 :
        return
    
    last_event_id = -1
    while len(events_list) > 0 :
        events_data_to_process_list = []
        events_to_process_dictionary = dict(events_list[:3])
        last_event_id = list(events_to_process_dictionary)[-1]
        events_list = events_list[3:]
        for event_data in events_data_list:
            if event_data['EVENT_ID'] <= last_event_id:
                events_data_to_process_list.append(event_data)
                events_data_list = events_data_list[1:]

        body = buildContent(events_to_process_dictionary, events_data_to_process_list)
    
        sendmail(body)

    if last_event_id:    
        save_last_id(last_event_id)

def poll_database():
    last_id = str(load_last_id())
    query = "SELECT * FROM hardware_change_events WHERE ID > " + last_id + " ORDER BY ID"
    cursor.execute(query)
    hardware_change_event_list = cursor.fetchall()

    # Send email if there are new results
    if hardware_change_event_list:
        event_list_dictionary = {event["ID"]: event for event in hardware_change_event_list}
        query = "SELECT * FROM hardware_change_events_data WHERE EVENT_ID >= "+ str(hardware_change_event_list[0]["ID"]) + " ORDER BY EVENT_ID"
        cursor.execute(query)
        hardware_change_event_data_list = cursor.fetchall()
    
        return list(event_list_dictionary.items()), hardware_change_event_data_list
 
    return {}, {}
    
def buildContent(events_list, events_data_list):
    body ="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
        <style>
            .sessionDetails {
                height: 35px;font-size: 24px;vertical-align: middle;padding: 5px 0 0 15px; font-family: Tahoma;
            }
            .viewOcsLink {
                height: 35px;font-size: 24px;vertical-align: middle;padding: 0 20px; font-family: Tahoma;
            }
            .session {
                font-size: 20px;vertical-align: middle;padding: 5px 0 0 15px; font-family: Tahoma;
            }
            .column {
                padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;
            }
        </style>
    <body>
        <table style="border-collapse: collapse;" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="border: none;background-color: #fb9895;color: White;font-weight: bold;font-size: 16px;padding: 10px;font-family: Tahoma;">Alerta: Cambio de Hardware detectado</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 0px;font-family: Tahoma;font-size: 12px;">
                        <table style="border-style: solid;border-width: 1px;margin:30px 0 0;">
                            <tr>
                                <td>"""
    current_event_id = 0
    for event_data in events_data_list:
        if current_event_id != event_data["EVENT_ID"]:
            if (current_event_id):
                body +="""     </td>
                            </tr>
                        </table>
                        <table style="border-style: solid;border-width: 1px;margin:30px 0 0;">
                            <tr>
                                <td>"""
            current_event_id = event_data["EVENT_ID"]
            event = events_list[current_event_id]

            body +=f"""             <table width="100%" cellspacing="0" cellpadding="0">
                                        <tr style="height: 17px;background-color: #4fc3f7">
                                            <td class="sessionDetails">
                                                <span>EventId: { str(current_event_id) } - PC: {str(event["NAME"])} - IP: {str(event["IP_ADDRESS"])} - Usuario: {str(event["USERNAME"])} - Ultimo scan: {str(event["LAST_SCAN_DATETIME"])}</span>
                                            </td>
                                            <td class="viewOcsLink">
                                                <span><a href="{str(ocsinventory_server_url)}/ocsreports/index.php?function=computer&head=1&systemid={str(event["HARDWARE_ID"])}" target=”_blank”>Ver equipo en OCSInventory </a></span>
                                            </td>
                                        </tr>
                                    </table>"""
        body += f"""                <table style="margin: 0px;border-collapse: collapse;" width="100%" cellspacing="0" cellpadding="0">
                                        <tr style="height: 17px;">
                                            <td class="session">{event_data["SECTION"]}</td>
                                        </tr>
                                    </table>"""
        body += """                 <table style="margin: 0px;border-collapse: collapse;" width="100%" cellspacing="0" cellpadding="0">
                                        <tr style="height: 17px;">
                                            <td class="column"><b>Descripcion</b></td>"""
        for field in event_data["FIELDS"].split(","):
            body+=f"""                     <td class="column"><b>{field.strip("'").strip('"')}</b></td>"""
        body += """                     </tr>"""
        
        for added in event_data["HARDWARE_ADDED"].replace("'","").replace('", "',"|").replace('"',"").split("|"):
            body+=f"""                  <tr style="height: 17px; background-color: #c4f9b1">
                                            <td class="column"><b>Hardware Anadido</b></td>"""
            for cell in added.split(","):
                body+=f"""                  <td class="column"><b>{cell}</b></td>"""
            body+=f"""                  </tr>"""
        
        for removed in event_data["HARDWARE_REMOVED"].replace("'","").replace('", "',"|").replace('"',"").split("|"):
            body+=f"""                  <tr style="height: 17px; background-color: #e57373">
                                            <td class="column"><b>Hardware Removido</b></td>"""
            for cell in removed.split(","):
                body+=f"""                  <td class="column"><b>{cell}</b></td>"""
            body+=f"""                  </tr>"""

    body +="""                      </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
        </table>
    </body>
    </html>"""
    return body

def sendmail(body):
    #Send email
    smtp_server = smtplib.SMTP_SSL(email_server, email_server_port) if email_server_use_ssl else smtplib.SMTP(email_server, email_server_port)
    smtp_server.ehlo()
    smtp_server.login(email_sender, email_password)

    message = EmailMessage()
    message['Subject'] = "Cambio de Hardware detectado"
    message['From'] = email_sender
    message.set_content(body, subtype='html')
    
    for recipient in email_recipients.split(","):
        message['To'] = recipient
        smtp_server.sendmail(email_sender, recipient, message.as_string())
        del message['To']
    smtp_server.close()

    
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
    main()
    time.sleep(30)
