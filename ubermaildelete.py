#!/usr/bin/env python3

import datetime
import mailbox
import os
import configparser
import flask
import flask

# ---------------------------------------------------
# read configfile
# ---------------------------------------------------

UMDPath = os.path.dirname(os.path.realpath(__file__))
UMDConfig = configparser.ConfigParser()
UMDConfig.read(os.path.join(UMDPath,'ubermaildelete.conf'))

UMDAdminName = UMDConfig['UMD']['admin']
UMDAdminPassword = UMDConfig['UMD']['password']

mailUserPath = os.path.join(os.getenv('HOME'),'users')


# ---------------------------------------------------
# flask
# ---------------------------------------------------

app = flask.Flask(__name__)
app.secret_key = UMDConfig['UMD']['SECRET']
app.permanent_session_lifetime = 3600

# ---------------------------------------------------


def getMailUserList():
    mailUserList = os.listdir(mailUserPath)
    mailUserList = [os.path.join(mailUserPath, x) for x in mailUserList]
    return mailUserList


def getMailUserDiskUsage(mailUser):
    start_path = os.path.join(mailUserPath, mailUser)
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def deleteOldMails(maildir, maxAge=None, maxSize=None):
    """
    delete mails from mailbox.maildir older than maxAge in days
    and/or bigger than size in kB
    """
    for key, msg in maildir.iteritems():
        # calculate age and size of message
        msgTime = datetime.datetime.fromtimestamp(msg.get_date())
        msgSize = len(msg.as_bytes()) / 1024 
        # boolean functions 
        def _olderThan():
            return msgTime + datetime.timedelta(days=maxAge) < datetime.datetime.now()
        def _biggerThan():
            return msgSize > maxSize
        # delte and be verbose
        def __deleteMail():
                print( msg.get('FROM') )
                print( str(msgSize) + " kB" )
                print( msg.get('DATE') )
                print( msgTime )
                print('------------------------------')
                maildir.remove(key)
        # check which filters to use
        if maxAge and maxSize:
            if _biggerThan() and _olderThan():
                __deleteMail()
        elif maxAge and not maxSize:
            if _olderThan():
                __deleteMail()
        elif not maxAge and maxSize:
            if _biggerThan():
                __deleteMail()



@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST':
        userName = flask.request.form['username']
        if userName == UMDAdminName and flask.request.form['password'] == UMDAdminPassword:
            flask.session.permanent = True
            flask.session['username'] = userName
            return flask.redirect(flask.url_for('main'))
    return '''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    '''


@app.route('/logout')
def logout():
    flask.session.pop('username', None)
    return flask.redirect(flask.url_for('main'))


@app.route('/', strict_slashes=False, methods=['GET', 'POST'])
def main():
    if 'username' in flask.session:
        if flask.request.method == 'POST':
            for mailUser in flask.request.form.getlist('mailUsers'):
                print('=' * 44)
                print(mailUser)
                print('-' * 44)
                print('-' * 44)
                maxAge, maxSize = None, None
                if 'maxAgeFilter' in flask.request.form:
                    maxAge = int(flask.request.form['maxAge'])
                if 'maxSizeFilter' in flask.request.form:
                    maxSize = int( float(flask.request.form['maxSize']) *1024 )
                maildir = mailbox.Maildir(mailUser)
                deleteOldMails(maildir,maxAge=maxAge, maxSize=maxSize)
        mailDirStats = [ {'name': x, 'size': str(getMailUserDiskUsage(x)/1000000) + ' MB'} for x in getMailUserList() ]
        return flask.render_template("list.html", mailusers=mailDirStats)
    return 'You are not logged in <br><a href="' + flask.url_for('login') + '">login</a>'


if __name__ == '__main__':
    app.run(host='localhost', debug=True, port=64003)

