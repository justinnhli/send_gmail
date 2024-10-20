#!/usr/bin/env python3
"""Simple library to send emails through Gmail."""

# pylint: disable = import-error, line-too-long

from argparse import ArgumentParser
from base64 import urlsafe_b64encode
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Union, Sequence

from commonmark import Parser as CommonMarkParser, HtmlRenderer
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from jinja2 import Environment as JinjaEnvironment

CLIENT_SECRET_PATH = Path('~/.secrets/gmail-client-secret.json').expanduser().resolve()
TOKEN_PATH = Path(__file__).parent / 'token.json'

# if modifying these scopes, delete TOKEN_PATH
# for all existing scopes, see https://developers.google.com/identity/protocols/oauth2/scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
]


def get_credentials():
    # type: () -> Credentials
    """Get Google credentials."""
    creds = None
    # read the credentials from the token file, if it exists
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    # ask the user to log in if there are no valid credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
    # check credentials
    if not creds and creds.valid:
        raise ValueError('unable to establish credentials')
    # save the valid credentials
    with TOKEN_PATH.open('w') as fd:
        fd.write(creds.to_json())
    return creds


def build_gmail_service():
    # type: () -> Resource
    """Build a Gmail API service.

    Returns:
        Resource: The Resource for interacting with a Google API.
    """
    return build('gmail', 'v1', credentials=get_credentials())


def create_message(addresses, subject, message_text, html=True, attachments=None):
    # type: (list[str], str, str, bool, list[Path]) -> MIMEMultipart
    """Create a message for an email, using the low-level API.

    Arguments:
        addresses (str): Email address(es) of the receiver.
        subject (str): The subject of the email message.
        message_text (str): The text of the email message.
        html (bool): If True, treat message as HTML instead of plain text. Defaults to True.
        attachments (List[Path]): A list of filepaths to attach to the email. Defaults to [].

    Returns:
        dict: A base64url encoded email JSON "object".
    """
    if attachments is None:
        attachments = []
    # create the initial message
    message = MIMEMultipart()
    message['to'] = ','.join(addresses)
    message['subject'] = subject
    # add the email body text
    if html:
        message.attach(MIMEText(message_text, 'html'))
    else:
        message.attach(MIMEText(message_text))
    # add each file attachment
    for attachment_path in attachments:
        with attachment_path.open('rb') as fd:
            attachment = MIMEApplication(fd.read(), Name=attachment_path.name)
        attachment['Content-Disposition'] = f'attachment; filename="{attachment_path.name}"'
        message.attach(attachment)
    # correctly encode and decode the message
    return message


def send_message(service, user_id, message):
    # type: (Resource, str, MIMEMultipart) -> dict[str, Any]
    """Send an email message, using the low-level API.

    Arguments:
        service (Resource): Authorized Gmail API service instance.
        user_id (str): User's email address. The special value "me"
            can be used to indicate the authenticated user.
        message (str): Message to be sent.

    Returns:
        dict: The sent message as a JSON-like object.
    """
    try:
        sent_message = service.users().messages().send(
            userId=user_id,
            body={
                'raw': urlsafe_b64encode(message.as_string().encode()).decode(),
            },
        ).execute()
        print(f'Message sent; id={sent_message["id"]}')
        return sent_message
    except HttpError as error:
        print(f'An error occurred: {error}')
    return None


def send_email(address, subject, body, html=True, attachments=None):
    # type: (Union[Sequence[str], str], str, str, bool, list[Path]) -> dict[str, Any]
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
        addresses = [address]
    else:
        addresses = list(address)
    if attachments is None:
        attachments = []
    return send_message(
        build_gmail_service(),
        'me',
        create_message(
            addresses=addresses,
            subject=subject,
            message_text=body,
            attachments=attachments,
            html=html,
        ),
    )


def markdown_render(markdown):
    # type: (str) -> str
    """Convert Markdown to HTML.

    Arguments:
        markdown (str): The Markdown document.

    Returns:
        str: The rendered HTML.
    """
    return HtmlRenderer().render(CommonMarkParser().parse(markdown))


def jinja_render(template, context):
    # type: (str, dict[str, Any]) -> str
    """Render a Jinja template.

    Arguments:
        template (str): The Jinja template string.
        context (Dict[str, obj]): A dictionary of variables for Jinja.

    Returns:
        str: The rendered string.
    """
    return JinjaEnvironment().from_string(template).render(**context)


def main():
    # type: () -> None
    """Send an email from the command line."""
    arg_parser = ArgumentParser()
    arg_parser.add_argument('addresses', metavar='TO', help='(Comma-separated) email address(es) of the recipient(s)')
    arg_parser.add_argument('subject', metavar='SUBJECT', help='Subject of the email')
    arg_parser.add_argument('body', metavar='BODY', help='body of the email')
    arg_parser.add_argument('--html', action='store_true', help='treat body as HTML (default False)')
    args = arg_parser.parse_args()
    send_email(
        address=args.addresses,
        subject=args.subject,
        body=args.body,
        html=args.html,
    )


if __name__ == '__main__':
    main()
