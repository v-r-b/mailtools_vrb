from mailtools_vrb import *

#################################################
# Sample usage: EasySSLSendmail
#################################################

# file mail_credentials.json: fill in correct information first!
filePath = "tests/mail_credentials.json"
# use correct address for email receiver
receiver = "me@mydomain.com"

with EasySSLSendmail(json_mail_info=filePath) as server:
    server.login()
    server.send_mail_message("Test Message (Text)", receiver, """\
This is a test message sent with EasySSLSendmail.
""")
    server.send_mail_message("Test Message (Multipart)", receiver, """\
This is the text part of a multipart test message
sent with EasySSLSendmail.
""", mail_html="""\
<html>
    <body>
        <h1>Multipart Message</h1>
        <p>This is the HTML part of a test message 
        sent with EasySSLSendmail.</p>
    </body>
</html>
""")