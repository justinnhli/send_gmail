# `gmailer`

A simple script/library to send emails using the Gmail API. To use:

1. Clone this repository.

2. Follow Steps 1 and 2 on the [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python). Save `client_secret.json` into the directory of the cloned repo.

3. Test the script by running:

	```
	gmailer.py <YOUR_EMAIL> 'Python Gmail Send Test' 'It works!'
	```
	
	You will be asked to authenticate this app. If the script prints `Message sent` and you receive an email from yourself, everything works.
