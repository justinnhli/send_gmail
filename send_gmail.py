#!/usr/bin/env python3

import webbrowser
from base64 import urlsafe_b64encode
from functools import lru_cache
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import join as join_path, basename, realpath, expanduser, dirname

from apiclient import discovery, errors
from commonmark import Parser as CommonMarkParser, HtmlRenderer
from google_auth_oauthlib.flow import Flow
from jinja2 import Environment as JinjaEnvironment

REAL_PATH = realpath(expanduser(dirname(__file__)))
CLIENT_SECRET_FILE = join_path(REAL_PATH, 'client_secret.json')

# If modifying these scopes, delete your previously saved credentials
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
]


@lru_cache()
def get_credentials():
    # Create the flow using the client secrets file from the Google API Console.
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob', # FIXME this should be read from client secret as well
    )

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')

    webbrowser.open(auth_url)

    # The user will get an authorization code. This code is used to get the
    # access token.
    code = input('Enter the authorization code: ')
    flow.fetch_token(code=code)

    return flow.credentials


def get_service():
    """Build a Gmail API service.

    Returns:
        Resource: The Resource for interacting with a Google API.
    """
    credentials = get_credentials()
    return discovery.build('gmail', 'v1', credentials=credentials)


def create_message(address, subject, message_text, html=True, attachments=None):
    """Create a message for an email, using the low-level API.

    Arguments:
        address (str): Email address(es) of the receiver.
        subject (str): The subject of the email message.
        message_text (str): The text of the email message.
        html (bool): If True, treat message as HTML instead of plain text. Defaults to True.
        attachments (List[str]): A list of filepaths to attach to the email. Defaults to [].

    Returns:
        dict: A base64url encoded email JSON "object".
    """
    if attachments is None:
        attachments = []

    # create the initial message
    message = MIMEMultipart()
    message['to'] = address
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
        message (str): Message to be sent.

    Returns:
        dict: The sent message as a JSON-like object.
    """
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print('Message sent; id={}'.format(message['id']))
        return message
    except errors.HttpError as error:
        print('An error occurred: {}'.format(error))


def send_email(address, subject, body, html=True, attachments=None):
    """Send an email.

    Arguments:
        address (Union[Seq[str], str]): Email address of the receiver.
        subject (str): The subject of the email message.
        body (str): The text of the email message.
        html (bool): If True, treat message as HTML instead of plain text. Defaults to True.
        attachments (List[str]): A list of filepaths to attach to the email. Defaults to [].

    Returns:
        Message: The sent message.
    """
    if isinstance(address, str):
        address = [address]
    assert hasattr(address, '__iter__')
    if attachments is None:
        attachments = []
    service = get_service()
    address = ', '.join(address)
    message = create_message(address=address, subject=subject, message_text=body, attachments=attachments, html=html)
    return send_message(service, 'me', message)


def markdown_render(markdown):
    """Convert Markdown to HTML.

    Arguments:
        markdown (str): The Markdown document.

    Returns:
        str: The rendered HTML.
    """
    return HtmlRenderer().render(CommonMarkParser().parse(markdown))


def jinja_render(template, context):
    """Render a Jinja template.

    Arguments:
        template (str): The Jinja template string.
        context (Dict[str, obj]): A dictionary of variables for Jinja.

    Returns:
        str: The rendered string.
    """
    return JinjaEnvironment().from_string(template).render(**context)


def main():
    """Send an email from the command line."""
    from argparse import ArgumentParser
    arg_parser = ArgumentParser()
    arg_parser.add_argument('addresses', metavar='TO', help='(Comma-separated) email address(es) of the recipient(s)')
    arg_parser.add_argument('subject', metavar='SUBJECT', help='Subject of the email')
    arg_parser.add_argument('body', metavar='BODY', help='body of the email')
    arg_parser.add_argument('--html', action='store_true', help='treat body as HTML (default False)')
    args = arg_parser.parse_args()
    send_email(
        address=args.to,
        subject=args.subject,
        body=args.body,
        html=args.html,
    )


if __name__ == '__main__':
    main()
