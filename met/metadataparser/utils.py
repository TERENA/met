#################################################################
# MET v2 Metadate Explorer Tool
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
# Current version of MET has been revised for performance improvements by Andrea Biancini,
# Consortium GARR, http://www.garr.it
#########################################################################################

import hashlib, smtplib
from email.mime.text import MIMEText
from django.conf import settings
from slackclient import SlackClient

def compare_filecontents(a, b):
    if a is None:
        return b is None
    if b is None:
        return a is None

    md5_a = hashlib.md5(a).hexdigest()
    md5_b = hashlib.md5(b).hexdigest()
    return md5_a == md5_b

def _connect_to_smtp(server, port=25, login_type=None, username=None, password=None):
    smtp_send = smtplib.SMTP(server, port)
    smtp_send.ehlo()

    if smtp_send.has_extn('STARTTLS'):
        smtp_send.starttls()
        smtp_send.ehlo()

    if username and password:
        try:
            if login_type:
                smtp_send.esmtp_features['auth'] = login_type
            smtp_send.login(username, password)
        except Exception, errorMessage:
            print('Error occurred while trying to login to the email server with user %s: %s' % (username, errorMessage))
            raise

    return smtp_send

def send_slack(message):
    slack_config_dict = getattr(settings, "SLACK_CONFIG")
    if slack_config_dict and 'token' in slack_config_dict:
        slack_token = slack_config_dict['token']
        slack_channel = slack_config_dict['channel'] if 'channel' in slack_config_dict else '#devops'
        sc = SlackClient(slack_token)

        sc.api_call(
          "chat.postMessage",
          channel=slack_channel,
          text=message
        )

def send_mail(from_email_address, subject, message):
    mail_config_dict = getattr(settings, "MAIL_CONFIG")
    server = mail_config_dict['email_server']
    smtp_send = None

    if server is None:
        return
    
    smtp_send = _connect_to_smtp(server, mail_config_dict['email_server_port'], mail_config_dict['login_type'], mail_config_dict['username'], mail_config_dict['password'])
        
    try:
        message = MIMEText(message.encode("utf-8"), "plain", _charset = "UTF-8")
        message['From'] = from_email_address
        message['To'] = ",".join(mail_config_dict['to_email_address'])
        message['Subject'] = subject
            
        smtp_send.sendmail(
            from_email_address, 
            mail_config_dict['to_email_address'],
            message.as_string()
        )
    except Exception, errorMessage:
        print('Error occurred while trying to send an email to %s: %s' % (mail_config_dict['to_email_address'], errorMessage))
        raise
    finally:
        if smtp_send:
            smtp_send.quit()
