import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import COMMASPACE
from email import encoders

class EmailBotException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class EmailBot:
    def __init__(self, SMTPServer:str, botEmail:str, botPswd:str, SMTPPort:int = 587):
        '''
        Initialize Email Bot with the provided credentials.
        - `server` is the email server for the bot e.g. 'smtp.gmail.com'
        '''
        self.__SMTPServer = SMTPServer
        self.__SMTPPort = SMTPPort
        self.__email = botEmail
        self.__password = botPswd

    def sendEmail(self, subject: str, body: str, mainRecipient: str, otherRecipients: list = [], files:list =[], important:bool =False, content="text"):
        '''
            Sends an email using the credentials and server initialized with the object.
            - `subject` is the title of the email
            - `body` is the body of the email
            - `mainRecipient` is the email address of the main reciepient
            - `otherRecipients` is the list of email addresses that will be CC-ed in the email
            - `files` is the list of file addresses that will be opened and attached with the emai;
            - `important` for if the email should be marked as important
            - `content` is the type of content in the body, can be "text" for standard text, or "html"
        '''
        if mainRecipient not in otherRecipients: otherRecipients.insert(0, mainRecipient)
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.__email
        msg['To'] = mainRecipient
        msg['Cc'] = ( ";".join(otherRecipients) ).replace("\n\r ", "")
        if important:
            msg['X-Priority'] = "1"
            msg['X-MSMail-Priority'] = "High"

        if content == "text":
            msg.attach( MIMEText(body) )
        else:
            msg.attach( MIMEText(body, content) )
        
        for filename in files:
            with open(filename, "rb") as file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload( file.read() )
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(filename)))
                msg.attach(part)
        
        # connect to email smpt server with this port
        session = smtplib.SMTP(self.__SMTPServer, self.__SMTPPort)

        #enable security
        session.starttls()

        #log in with the credentials of the bot
        session.login(self.__email, self.__password)

        session.sendmail(self.__email, otherRecipients, msg.as_string())
        
        session.quit()