import os
import imaplib
import email
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
from get_fpl_team import get_source_data_path

def fetch_new_source_data_from_gmail(next_gameweek_api, last_gameweek_api_deadline_date):
    is_found = False
    is_updated = False
    
    # Load environment variables from .env file
    load_dotenv('../.env')

    # Get the email credentials from environment variables
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')

    # Connect to Gmail IMAP server
    imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
    imap_server.login(email_address, email_password)
    imap_server.select('inbox')

    # Search for emails from bingo@patreon.com with the specified attachment
    status, email_ids = imap_server.search(None, f'(FROM "bingo@patreon.com" SUBJECT "GW {next_gameweek_api} - the Transfer Algorithm" SINCE "05-OCT-2024")')
    email_ids = email_ids[0].split()

    # Select the last email ID
    latest_email_id = email_ids[-1]

    # Fetch the email data
    status, email_data = imap_server.fetch(latest_email_id, '(RFC822)')
    raw_email = email_data[0][1]
    email_message = email.message_from_bytes(raw_email)

    for part in email_message.walk():
        content_type = part.get_content_type()
        if content_type == 'text/html':
            html_content = part.get_payload(decode=True)
            soup = BeautifulSoup(html_content, 'html.parser')
            links = soup.find_all('a', href=True)
            unique_links = list(set(link['href'] for link in links))
            csv_links = [link for link in unique_links if '.csv' in link]
            if len(csv_links) != 1:
                print("Did not find exactly one CSV link in the last email")
                break
            else:
                is_found = True
                url = csv_links[0]
                response = requests.get(url)
                temp_file_path = f"{get_source_data_path()}\\TransferAlgorithm_temp.csv"
                with open(temp_file_path, 'wb') as f:
                    f.write(response.content)
            
            # Check if the content of the attachment is different from the existing file
            existing_file_path = f"{get_source_data_path()}\\TransferAlgorithm.csv"
            
            if os.path.exists(existing_file_path):
                with open(existing_file_path, 'rb') as f:
                    existing_content = f.read()
                with open(temp_file_path, 'rb') as f:
                    new_content = f.read()
                if existing_content != new_content:
                    is_updated = True
            else:
                print(f"The file path '{existing_file_path}' does not exist")
            
            # If the content is updated, overwrite the existing file
            if is_updated:
                os.replace(temp_file_path, existing_file_path)
            else:
                os.remove(temp_file_path)
            
            break
        else:
            print("Did not find HTML content in the last email")
            break

    # Close the connection to the IMAP server
    imap_server.close()
    imap_server.logout()

    # Return the boolean variable indicating if the content is updated
    return is_found, is_updated
