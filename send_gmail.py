#!/usr/bin/env python3

from base64 import urlsafe_b64encode
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import join as join_path, basename, realpath, expanduser, dirname

from apiclient import discovery, errors
from commonmark import Parser as CommonMarkParser, HtmlRenderer
from httplib2 import Http
from jinja2 import Environment as JinjaEnvironment
from oauth2client import client, tools
from oauth2client.file import Storage

REAL_PATH = realpath(expanduser(dirname(__file__)))
CREDENTIAL_PATH = join_path(REAL_PATH, 'stored-credentials.json')
CLIENT_SECRET_FILE = join_path(REAL_PATH, 'client_secret.json')

# If modifying these scopes, delete your previously saved credentials
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
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


def create_message(to, subject, message_text, html=True, attachments=None):
    """Create a message for an email, using the low-level API

    Arguments:
        to (str): Email address of the receiver.
        subject (str): The subject of the email message.
        message_text (str): The text of the email message.
        html (bool): If True, treat message as HTML instead of plain text. Defaults to True.
        attachments ([str]): A list of filepaths to attach to the email. Defaults to [].

    Returns:
        dict: A base64url encoded email JSON "object".
    """
    if attachments is None:
        attachments = []

    # create the initial message
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject

    # add the email body text
    if html:
        message.attach(MIMEText(message_text, 'html'))
    else:
        message.attach(MIMEText(message_text))

    # add each file attachment
    for filepath in attachments:
        with open(realpath(expanduser(filepath)), 'rb') as fd:
            attachment = MIMEApplication(fd.read(), Name=basename(filepath))
        attachment['Content-Disposition'] = 'attachment; filename="{}"'.format(basename(filepath))
        message.attach(attachment)

    # correctly encode and decode the message
    return {'raw': urlsafe_b64encode(message.as_string().encode()).decode()}


def send_message(service, user_id, message):
    """Send an email message, using the low-level API

    Arguments:
        service (Service): Authorized Gmail API service instance.
        user_id (str): User's email address. The special value "me"
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


def send_email(to, subject, body, html=True, attachments=None):
    """Send an email.

    Arguments:
        to (str): Email address of the receiver.
        subject (str): The subject of the email message.
        body (str): The text of the email message.
        html (bool): If True, treat message as HTML instead of plain text. Defaults to True.
        attachments ([str]): A list of filepaths to attach to the email. Defaults to [].

    Returns:
        Sent Message.
    """
    if attachments is None:
        attachments = []
    service = get_service()
    message = create_message(to=to, subject=subject, message_text=body, attachments=attachments, html=html)
    return send_message(service, 'me', message)


def markdown_render(md):
    """Convert Markdown to HTML.

    Arguments:
        md (str): The Markdown document.

    Returns:
        str: The rendered HTML.
    """
    return HtmlRenderer().render(CommonMarkParser().parse(md))


def jinja_render(template, context):
    """Render a Jinja template.

    Arguments:
        template (str): The Jinja template string.
        context ({str: *}): A dictionary of variables for Jinja.

    Returns:
        str: The rendered string.
    """
    return JinjaEnvironment().from_string(template).render(**context)


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
