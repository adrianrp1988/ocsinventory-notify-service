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

        # Format message
        message = EmailMessage()
        message['Subject'] = "Cambio de Hardware detectado"
        message['From'] = email_sender

        body = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        </head>
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
        for section_data in hardware_change_event_data_list:
            if current_event_id != section_data["EVENT_ID"]:
                if (current_event_id):
                    body +=f"""     </td>
                                </tr>
                            </table>
                            <table style="border-style: solid;border-width: 1px;margin:30px 0 0;">
                                <tr>
                                    <td>"""
                current_event_id = section_data["EVENT_ID"]
                event_data = event_list_dictionary[current_event_id]

                body +=f"""     <table width="100%" cellspacing="0" cellpadding="0">
                                    <tr style="height: 17px;background-color: #4fc3f7">
                                        <td class="sessionDetails" style="height: 35px;font-size: 24px;vertical-align: middle;padding: 5px 0 0 15px; font-family: Tahoma;">
                                            <span>PC: {str(event_data["NAME"])} - IP: {str(event_data["IP_ADDRESS"])} - Usuario: {str(event_data["USERNAME"])} - Ultimo scan: {str(event_data["LAST_SCAN_DATETIME"])}</span>
                                        </td>
                                        <td align="right" style="height: 35px;font-size: 24px;vertical-align: middle;padding: 0 20px; font-family: Tahoma;">
                                            <span><a href="{str(ocsinventory_server_url)}/ocsreports/index.php?function=computer&head=1&systemid={str(event_data["HARDWARE_ID"])}" target=”_blank”>Ver equipo en OCSInventory </a></span>
                                        </td>
                                    </tr>
                                </table>"""
            body += f"""        <table style="margin: 0px;border-collapse: collapse;" width="100%" cellspacing="0" cellpadding="0">
                                    <tr style="height: 17px;">
                                        <td style="font-size: 20px;vertical-align: middle;padding: 5px 0 0 15px; font-family: Tahoma;" nowrap="nowrap">{section_data["SECTION"]}</td>
                                    </tr>
                                </table>"""
            body += f"""        <table style="margin: 0px;border-collapse: collapse;" width="100%" cellspacing="0" cellpadding="0">
                                    <tr style="height: 17px;">
                                        <td style="padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;"
                                            nowrap="nowrap"><b>Descripcion</b>
                                        </td>"""
            for field in section_data["FIELDS"].split(","):
                body+=f"""          <td style="padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;"
                                        nowrap="nowrap"><b>{field.strip("'").strip('"')}</b>
                                    </td>"""
            body += f"""            </tr>
                                    <tr style="height: 17px; background-color: #c4f9b1">
                                        <td style="padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;"
                                            nowrap="nowrap"><b>Hardware Anadido</b>
                                        </td>""" 
            for added in section_data["HARDWARE_ADDED"].split(","):
                body+=f"""              <td style="padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;"
                                            nowrap="nowrap"><b>{added.strip("'").strip('"')}</b>
                                        </td>"""
            body += f"""            </tr>          
                                    <tr style="height: 17px; background-color: #e57373">
                                        <td style="padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;"
                                            nowrap="nowrap"><b>Hardware Removido</b>
                                        </td>"""
            for removed in section_data["HARDWARE_REMOVED"].split(","):
                body+=f"""              <td style="padding: 2px 3px 2px 3px;vertical-align: top;border: 1px solid #a7a9ac;font-family: Tahoma;font-size: 12px;"
                                            nowrap="nowrap"><b>{removed.strip("'").strip('"')}</b>
                                        </td>"""
            body += """             </tr>
                                </table>"""
        body +="""          </td>
                        </tr>
                    </table>
                </td>
            </tr>
    </table>
</body>
</html>"""
        message.set_content(body, subtype='html')

        # Send email
        smtp_server = smtplib.SMTP_SSL(email_server, email_server_port) if email_server_use_ssl else smtplib.SMTP(email_server, email_server_port)
        smtp_server.ehlo()
        smtp_server.login(email_sender, email_password)
        
        for recipient in email_recipients.split(","):
           sendmail(smtp_server, recipient, message) 
        smtp_server.close()

        last_id = hardware_change_event_list[-1]["ID"]
        save_last_id(last_id)
    
    return last_id

def sendmail(mail_server, recipient, message: EmailMessage):
    message['To'] = recipient
    mail_server.sendmail(email_sender, recipient, message.as_string())
    del message['To']
    
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