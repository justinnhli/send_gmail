#!/usr/bin/env python3

from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from os.path import join as join_path, realpath, expanduser, dirname

from apiclient import discovery, errors
from httplib2 import Http
from oauth2client import client, tools
from oauth2client.file import Storage

# If modifying these scopes, delete your previously saved credentials
CREDENTIAL_PATH = join_path(realpath(expanduser(dirname(__file__))), 'stored-credentials.json')
CLIENT_SECRET_FILE = join_path(realpath(expanduser(dirname(__file__))), 'client_secret.json')

#SCOPES = 'https://mail.google.com/'
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose'
]
APPLICATION_NAME = 'Python Gmail Sender'


def get_credentials():
    """Get valid user credentials from storage, or create it.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    store = Storage(CREDENTIAL_PATH)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + CREDENTIAL_PATH)
    return credentials


def get_service():
    """Get a Service object for Gmail.

    Returns:
        A valid Service object.
    """
    credentials = get_credentials()
    http = credentials.authorize(Http())
    return discovery.build('gmail', 'v1', http=http)


def create_message(sender, to, subject, message_text, html=True):
    """Create a message for an email, using the low-level API

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.
        html: If True, treat message as HTML instead of plain text. Defaults to True.

    Returns:
        An object containing a base64url encoded email object.
    """
    if html:
        message = MIMEText(message_text, 'html')
    else:
        message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = subject
    return {'raw': urlsafe_b64encode(message.as_string().encode()).decode()}


def send_message(service, user_id, message):
    """Send an email message, using the low-level API

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message sent; id={}'.format(message['id']))
        return message
    except errors.HttpError as error:
        print('An error occurred: {}'.format(error))


def send_email(to, subject, body, html=True):
    """Send an email.

    Args:
        to: Email address of the receiver.
        subject: The subject of the email message.
        body: The text of the email message.
        html: If True, treat message as HTML instead of plain text. Defaults to True.

    Returns:
        Sent Message.
    """
    service = get_service()
    sender = service.users().getProfile(userId='me').execute()['emailAddress']
    message = create_message(sender=sender, to=to, subject=subject, message_text=body, html=html)
    return send_message(service, 'me', message)


def main():
    """Send an email from the command line."""
    from argparse import ArgumentParser
    arg_parser = ArgumentParser()
    arg_parser.add_argument('to', metavar='TO', help='Email address of the receiver')
    arg_parser.add_argument('subject', metavar='SUBJECT', help='Subject of the email')
    arg_parser.add_argument('body', metavar='BODY', help='body of the email')
    arg_parser.add_argument('--html', action='store_true', help='treat body as HTML (default False)')
    args = arg_parser.parse_args()
    send_email(
        to=args.to,
        subject=args.subject,
        body=args.body,
        html=args.html,
    )


if __name__ == '__main__':
    main()
