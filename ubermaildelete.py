#!/usr/bin/env python3

import datetime
import mailbox



mailUserPath = os.path.join(os.getenv('HOME'),'users')
mailUserList = os.listdir(mailUserPath)
mailUserList = [os.path.join(mailUserPath, x) for x in mailUserList]

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
            #maildir.remove(key)


for maildirPath in mailUserList:
    print(maildirPath)
    maildir = mailbox.Maildir(maildirPath)
    deleteOldMails(maildir, 500)
