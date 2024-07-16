import smtplib
import datetime
import logging
import os
import json

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import abort
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
# from jproperties import Properties

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

def sendEmail(content):

    to_list = content.get("recipients", [])
    template_list = content.get("templateList", [])
    request_id = content.get("req_id", "")
    request_version = content.get("req_version", "")
    file_name = content.get('fileName', '')

    logger.info(f"Sending email to {', '.join(to_list)}")
    sender_email = configs.get("sender_email")
    # password = configs.get("password")

    
    templates = {each["templateName"]: "\n".join(each.get("message", [])) for each in template_list}
    body_message = templates.get("Email Body", "")
    subject_message = templates.get("Subject", "")
    signature_message = templates.get("Signature", "")
        
    body = body_message + "\n" + signature_message

    message = MIMEMultipart()
    message.attach(MIMEText(body, 'plain'))
    message['Subject'] = subject_message
    message['From'] = sender_email
    message['To'] = ', '.join(to_list)

    

    if file_name:
        # Validating the file path
        base_path = "/opt/jboss/C3PConfig/DownloadFilePath/"
        filename = os.path.basename(file_name)
        fullpath = os.path.normpath(os.path.join(base_path, filename))
        if not fullpath.startswith(base_path):
            logger.error(f"Invalid file path: {fullpath}")
            return jsonify({"error": f"Invalid file path: {fullpath}"})
        
        file_name = find_pdf_file(fullpath)
        try:
            with open(file_name, 'rb') as file:
                pdf = MIMEApplication(file.read())
                pdf.add_header('Content-Disposition', 'attachment', filename=f'{request_id}_Certification_Test_Report_V1.PDF')
                message.attach(pdf)
        except FileNotFoundError:
            logger.error("Unable to find the attachment")
            abort(400, description='Attachment not found, please check the file')
        except Exception as err:
            logger.error(f"Unknown error while attaching the file: {err}")
            abort(400, description='Unknown error while attaching the file')

    try:
        # server = smtplib.SMTP('smtp.gmail.com', 587)
        server = smtplib.SMTP('10.10.169.1', 25)
        server.ehlo()
        server.starttls()
        # server.login(sender_email, password)
        server.sendmail(sender_email, to_list, message.as_string())
        server.quit()
    except Exception as err:
        logger.error(f"Unable to send email: {err}")
        abort(400, description='Failed to send email')

    logger.info('Success: Email sent')

    storeEmailData(to_list, template_list, request_id, request_version)
    logger.info("Success: Stored email information to c3p_t_mailing_report")

    return {'status': 'Email sent successfully'}

def find_pdf_file(file_path):
    # Check if the file path exists
    if os.path.exists(file_path):
        return file_path

    # Check if the file exists with .PDF extension
    pdf_path_uppercase = file_path.rsplit('.', 1)[0] + '.PDF'
    if os.path.exists(pdf_path_uppercase):
        return pdf_path_uppercase

    # Check if the file exists with .pdf extension
    pdf_path_lowercase = file_path.rsplit('.', 1)[0] + '.pdf'
    if os.path.exists(pdf_path_lowercase):
        return pdf_path_lowercase

    # If none of the above conditions are met, return None
    return None

def storeEmailData(recipients, template_list, request_id, request_version):
    type = 'mail'
    created_date = datetime.datetime.now()
    recipients_str = ', '.join(recipients)
    template_json = json.dumps({sub['templateName']: "\n".join(sub['message']) for sub in template_list})
    comm_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')

    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        sql = "INSERT INTO c3p_t_mailing_report(mr_comm_id, mr_created_date, mr_reciepients, mr_req_id, mr_req_version, mr_template_json, mr_type) VALUES(%s,%s,%s,%s,%s,%s,%s)"
        val = (comm_id, created_date, recipients_str, request_id, request_version, template_json, type)
        mycursor.execute(sql, val)
        mydb.commit()
        mydb.close()

    except Exception as err:
        logger.error(f"Unable in storingEmailData: {err}")
        abort(400, description='Unable to store to database')