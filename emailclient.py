import smtplib
import logging as log
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# TODO apply PEP8 class naming convention
# TODO add annotations and docstrings to class methods
# TODO change prints for logs
class email:
    def __init__(self, data: dict):
        self.email: str = data['email']['sender']['email']
        self.password: str = data['email']['sender']['password']
        self.receiver: str = data['email']['receiver']
        self.smtpClient: str = data['email']['client']

    # NOTE the message parameter is wrong, it doesn't defines the
    # message of the email, the html parameter is the one that defines
    # what message will be attached to the email. Remove message
    # parameter and use html parameter as messageinstead in the future
    def sendMail(
        self, subject: str, message: str, html: str | None = None
    ) -> None:
        """Sends a email with the given subject and message to the stored
        reciever from the stored email address
        """

        log.info('Sending Email...')

        # TODO use specific exception catching
        try:
            self.smtpObj = smtplib.SMTP(self.smtpClient, 587)
        except:
            self.smtpObj = smtplib.SMTP_SSL(self.smtpClient, 465)

        self.smtpObj.ehlo()
        self.smtpObj.starttls()

        message = MIMEMultipart(message)
        message['Subject'] = subject
        message['From'] = self.email
        message['To'] = self.receiver

        if html:
            htmlText = MIMEText(html, 'html')
            message.attach(htmlText)

        self.smtpObj.login(self.email, self.password)
        self.smtpObj.sendmail(self.email, self.receiver,  message.as_string())

        self.smtpObj.quit()

