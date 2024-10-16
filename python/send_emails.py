import os
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(message, next_gameweek_api):
    # Load environment variables from .env file
    load_dotenv('../.env')

    # Get the email credentials from environment variables
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')
    
    # set up the SMTP server
    smtp_server = smtplib.SMTP(host='smtp.gmail.com', port=587)
    smtp_server.starttls()
    smtp_server.login(email_address, email_password)

    # create a message
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = email_address
    msg['Subject'] = f"FPL Transfer Recommendations - GW {next_gameweek_api}"

    # format the message as HTML
    html_message = f"""
    <html>
    <body>
    <p>{message}</p>
    </body>
    </html>
    """

    # add in the message body
    msg.attach(MIMEText(html_message, 'html'))

    # send the message via the server
    smtp_server.send_message(msg)
    smtp_server.quit()