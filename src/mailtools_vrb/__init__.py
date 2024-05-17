"""
# mailtools_vrb

Mail handling tools.

This module defines:

```class EasySSLSendmail```
  
Class for sending out eMails using an SMTP connection over SSL
"""

from __future__ import annotations

import json, smtplib, ssl, logging
from datetime import datetime, timezone

# simple textmessage and multipart message
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from typing import TYPE_CHECKING 
if TYPE_CHECKING: 
    from _typeshed import FileDescriptorOrPath as FileDescriptorOrPath

logger = logging.getLogger(__name__)

class EasySSLSendmail(smtplib.SMTP_SSL):
    """Class for sending out eMails using an SMTP connection over SSL
    """

    SSMTP_PORT_DEFAULT = 465
    """ standard server port for SMTP oder SSL """
    
    @classmethod
    def make_credentials_dict(cls, *, json_mail_info: dict|FileDescriptorOrPath|None = None,
                 host: str|None = None, port: int|None = None, 
                 user: str|None = None, password: str|None = None,
                 sender: str|None = None, minpause: int|None = None) -> dict:
        """ Create dictionary with information either read from a json file
        if json_mail_info is a FileDescriptorOrPath oder copied from a given
        dict if json_mail_info is a dict. Afterwards all arguments which
        are not None are added to this dictionary using the argument name as
        a key. Plus, if no sender is provided but a user is known, the sender
        entry of the dictionary is set to the same value as the user entry.
        If no port is provided, _SSMTP_PORT_DEFAULT is used.

        Args:
            json_mail_info (dict | FileDescriptorOrPath | None, optional): credentials, either JSON file or dict. Defaults to None.
            host (str | None, optional): hostname or IP of mailserver. Defaults to None.
            port (int | None, optional): port to be used. Defaults to None.
            user (str | None, optional): uername for mailserver login. Defaults to None.
            password (str | None, optional): password for mailserver login. Defaults to None.
            sender (str | None, optional): sender address for outgoing mails. Defaults to None.
            minpause (int, optional): minimum timespan between two sentout mails.

        Returns:
            dict: dictionary with the gathered information
        """
        # read connection information from dict or file
        if isinstance(json_mail_info, dict):
            # create deep copy of info dict to leave the original untouched
            credentials = json.loads(json.dumps(json_mail_info))
        elif json_mail_info is not None:
            # if not dict and not None, we should have a FileDescriptorOrPath
            with open(json_mail_info) as fp: # type: ignore
                credentials = json.load(fp)
        else:
            # start with empty dict
            credentials = {}    
        # process argument list and eventually overwrite file/dict info
        if host is not None:
            credentials["host"] = host
        if port is not None:
            credentials["port"] = port
        if user is not None:
            credentials["user"] = user
        if password is not None:
            credentials["password"] = password
        if sender is not None:
            credentials["sender"] = sender
        if minpause is not None:
            credentials["minpause"] = minpause

        # take user for sender, if user is given, but no sender is provided
        if "user" in credentials and not "sender" in credentials:
            credentials["sender"] = credentials["user"]
        # use default port, if not provided
        if not "port" in credentials:
            credentials["port"] = cls.SSMTP_PORT_DEFAULT
        return credentials

    def __init__(self, *, json_mail_info: dict|FileDescriptorOrPath|None = None,
                 host: str|None = None, port: int|None = None, 
                 user: str|None = None, password: str|None = None,
                 sender: str|None = None, minpause: int|None = None,
                 ssl_context: ssl.SSLContext|None = None):
        """ Create new SSL Mail server instance. 
        Calls EasySSLSendmail.make_credentials_dict to gather the needed information.

        If no ssl_context ist passed (default is None), ssl.create_default_context() 
        will be called and used as context.

        Args:
            any except ssl_context: see make_credentials_dict()
            ssl_context (ssl.SSLContext, optional): Defaults to None (see above)
        """
        self._credentials = EasySSLSendmail.make_credentials_dict(
                                    json_mail_info=json_mail_info,
                                    host=host, port=port, 
                                    user=user, password=password,
                                    sender=sender, minpause=minpause)
        
        # Use default context if argument is omitted
        if (ssl_context is None):
            ssl_context = ssl.create_default_context()
        
        # Set timestamp of last mail to 0 (first mail shall be sent out any way)
        self._last_mail_utc_ts = 0

        super().__init__(self._credentials["host"], self._credentials["port"], context=ssl_context)

    def login(self, user: str|None = None, password: str|None = None, 
              initial_response_ok: bool = True) -> tuple[int, bytes]:
        """Login to the mail server. If no user and password arguments
        are passed, the credentials from the json_mail_info_file passed 
        to the constructor will be used.  

        Args:
            see args to smtplib.SMTP_SSL.login()

        Returns:
            tuple: see smtplib.SMTP_SSL.login()
        """
        # use values from _credentials (or "") if not provided as arguments
        if user is None:
            if "user" in self._credentials:
                user = self._credentials["user"]
            else:
                logger.warning("username neither passed as argument "
                               "nor found in credentials dict -> using empty string")
                user = ""
        if password is None:
            if "password" in self._credentials:
                password = self._credentials["password"]
            else:
                logger.warning("password neither passed as argument "
                               "nor found in credentials dict -> using empty string")
                password = ""
        return super().login(user, password, initial_response_ok=initial_response_ok)
    
    def send_mail_message(self, mail_subject: str, mail_to: str, 
                    mail_text: str, *, mail_html: str|None = None,
                    sender: str|None = None, minpause: int|None = None) -> dict:
        """Send a text or multipart eMail message. If mail_html is passed as 
        an argument, a multipart message (type "alternative") with plain text
        and html is sent, a plain text message otherwise. If sender and/or minpause 
        is omitted, the information passed to the constructor will be taken.

        If minpause hat a valid value, the message is sent only, if the minimum
        timespan between this message and the preceeding message is longer
        than minpause seconds. If not, a warning message will be logged.

        Args:
            mail_subject (str): Message subject
            mail_to (str): Receiver of the eMail
            mail_text (str): Plain text eMail body
            mail_html (str, optional): HTML eMail body. Defaults to None.
            sender (str, optional): sender address. Defaults to None (use self._credentials["sender"]).
            minpause (int, optional): minimum timespan between two sentout mails.
                                      Defaults to None (use self._credentials["minpause"]).

        Raises:
            exc: any exception raised by smtplib.SMTP_SSL.send_message()

        Returns:
            dict: see smtplib.SMTP_SSL.send_message()
        """
        # Get value for minpause
        if minpause is None:
            if "minpause" in self._credentials:
                minpause = self._credentials["minpause"]
        # Get value for sender
        if sender is None:
            if "sender" in self._credentials:
                sender = self._credentials["sender"]
            else:
                logger.warning("sender address neither passed as argument "
                               "nor found in credentials dict!")
                sender = "(unknown sender)"

        # if found, check if mail shall be sent
        if isinstance(minpause, int):
            timediff = int(datetime.timestamp(datetime.now(timezone.utc))) - self._last_mail_utc_ts
            if timediff < minpause:
                # if mail is suppressed, log warning
                logger.warning(f"minpause of {minpause} s prevents mail from being sent. "
                               f"time since last mail: {timediff} s")
                return {}
        
        try:
            if not isinstance(mail_html, str):   
                # send text message
                tmsg = EmailMessage()
                tmsg["Subject"] = mail_subject
                tmsg["From"] = sender
                tmsg["To"] = mail_to
                tmsg.set_content(mail_text)
                return super().send_message(tmsg)
            else:   
                # send multipart message with HTML part
                # and an alternative text part
                hmsg: MIMEMultipart = MIMEMultipart("alternative")  # default is "mixed"
                hmsg["Subject"] = mail_subject
                hmsg["From"] = sender
                hmsg["To"] = mail_to
                hmsg.attach(MIMEText(mail_text, "plain"))
                hmsg.attach(MIMEText(mail_html, "html"))
                return super().send_message(hmsg)
        except BaseException as exc:
            self.quit()
            # in case of an exception, log error and reraise exception
            logger.error(f"{type(exc).__name__}: {exc}", exc_info=exc)
            raise
