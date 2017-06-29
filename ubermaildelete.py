#!/usr/bin/env python3

import datetime
import mailbox
import os
import configparser
import flask
from threading import Thread
import functools

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
# flask settings
# ---------------------------------------------------

app = flask.Flask(__name__)
app.secret_key = UMDConfig['UMD']['SECRET']
app.permanent_session_lifetime = 3600

# ---------------------------------------------------
# statistics and delete functions
# ---------------------------------------------------


def getMailUserList():
    mailUserList = os.listdir(mailUserPath)
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
    returns a function, returning freed size in kb
    """
    def inner(maildir=maildir, maxAge=maxAge, maxSize=maxSize):
        count = 0 
        age_time = datetime.timedelta(days=maxAge) 
        now_time = datetime.datetime.now()
        for key, msg in maildir.iteritems():
            # calc size and time 
            msgTime = datetime.datetime.fromtimestamp(msg.get_date())
            msgSize = len(msg.as_bytes()) / 1024 
            # boolean functions 
            def _olderThan():
                return msgTime + age_time < now_time
            def _biggerThan():
                return msgSize > maxSize
            # delte and be verbose
            def __deleteMail():
                nonlocal count
                count += 1
                nonlocal freedSpace
                freedSpace += msgSize
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
        print("deleted " + str(count))
        print("freed " + str(freedSpace))
        return freedSpace
    return inner


# ---------------------------------------------------
# session decorator
# ---------------------------------------------------

def loggedIn(fail='html'):
    # Here we areactually using a decorator which creates two diffrent
    # decorators with diffrent fail responses.
    def umdSession(wrapped):
        # This is the Session decorator
        @functools.wraps(wrapped)
        def umdRequest(*args, **kwargs):
            if 'username' in flask.session:
                return wrapped(*args, **kwargs)
            else:
                if fail == 'html':
                    return 'You are not logged in <br><a href="' + flask.url_for('login') + '">login</a>'
                else:
                    return flask.abort(403)
        return umdRequest
    return umdSession

# ---------------------------------------------------
# ajax routes
# ---------------------------------------------------

@app.route('/ajax/diskusage', methods=['GET'])
@loggedIn(fail='ajax')
def ajaxDiskusage():
    mailDirStats = [ {'name': x.split('/')[-1], 'size': str(getMailUserDiskUsage(x)/1000000) + ' MB'} for x in getMailUserList() ]
    return flask.jsonify(mailDirStats)


@app.route('/ajax/diskusage/<userName>', methods=['GET'])
@loggedIn(fail='ajax')
def ajaxUserDiskusage(userName):
    # mailDirStats = {'name': userName.split('/')[-1], 'size': str(getMailUserDiskUsage(userName)/1000000) + ' MB'}
    mailDirStats = {'name': userName, 'size': str(getMailUserDiskUsage(userName)/1000000) + ' MB'}
    return flask.jsonify(mailDirStats)


@app.route('/ajax/delete/<userName>', methods=['POST'])
@loggedIn(fail='ajax')
def ajaxDelete(userName):
    print('\\'*20 + 'AJAX' + '/'*20)
    print(userName)
    print('-' * 44)
    print('-' * 44)
    maxAge, maxSize = None, None
    if 'maxAgeFilter' in flask.request.form:
        maxAge = int(flask.request.form['maxAge'])
    if 'maxSizeFilter' in flask.request.form:
        maxSize = int( float(flask.request.form['maxSize']) *1024 )
    maildir_path = os.path.join(mailUserPath, userName)
    maildir = mailbox.Maildir(maildir_path)
    freedMailSpace = deleteOldMails(maildir,maxAge=maxAge, maxSize=maxSize)
    freedMailSpace = round(freedMailSpace/1024, 2)
    response = {'name': userName.split('/')[-1], 'freed': str(freedMailSpace) + ' MB' }
    return flask.jsonify(response)


# ---------------------------------------------------
#  html routes
# ---------------------------------------------------

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
@loggedIn(fail='html')
def main():
    if flask.request.method == 'POST':
        del_threads = []
        for mailUser in flask.request.form.getlist('mailUsers'):
            maxAge, maxSize = None, None
            if 'maxAgeFilter' in flask.request.form:
                maxAge = int(flask.request.form['maxAge'])
            if 'maxSizeFilter' in flask.request.form:
                maxSize = int( float(flask.request.form['maxSize']) *1024 )
            maildir = mailbox.Maildir(mailUser)
            #freedMailSpace = deleteOldMails(maildir,maxAge=maxAge, maxSize=maxSize)
            #freedMailSpace = round(freedMailSpace/1024, 2)
            #print(freedMailSpace)
            #flask.flash(str(freedMailSpace) + ' MB freigegeben')
            del_threads.append(Thread(target=deleteOldMails(maildir,maxAge=maxAge, maxSize=maxSize), name=mailUser, daemon=True))
            del_threads[-1].start()
        return "Das kann jetzt etwas dauern, lösche mail in den postfächern von :</br> "
                + str(flask.request.form['mailUsers'])
                + "</br>du kannst die <a href='/'>startseite</a> immer wieder aktualisieren um zu sehen, was passiert."
    mailDirStats = [ {'name': x, 'size': str(getMailUserDiskUsage(x)/1000000) + ' MB'} for x in getMailUserList() ]
    return flask.render_template("list.html", mailusers=mailDirStats)


if __name__ == '__main__':
    app.run(host='localhost', debug=True, port=64003)

