#!/usr/bin/env python3

import datetime
import mailbox


mattobox = mailbox.Maildir('/home/sehtms/users/bergholz/')

def deleteOldMails(maildir, maxAge=12):
    """
    delete mails from mailbox.maildir older than maxAge in days
    """
    for key, msg in maildir.iteritems():
        msgTime = datetime.datetime.fromtimestamp(msg.get_date())
        if msgTime + datetime.timedelta(days=maxAge) < datetime.datetime.now():
            print( msg.get('FROM') )
            print( msg.get('DATE') )
            print( msgTime )
            print('------------------------------')
            maildir.remove(key)



deleteOldMails(mattobox, 365)
