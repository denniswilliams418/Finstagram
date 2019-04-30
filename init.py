from flask import Flask, render_template, request, session, redirect, url_for
import os
import pymysql.cursors

app = Flask(__name__)
app.secret_key = 'try to guess this key you wont'
IMAGES_DIR = os.path.join(os.getcwd(), 'images')

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             db='Finstagram',
                             charset='utf8mb4',
                             port=8889,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


# Landing page, returns homepage if already logged in
@app.route('/')
def hello():
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template('index.html')  # index.html is the landing page (Register/Login)


# Account registration page
@app.route('/register')
def register():
    return render_template('register.html')


# Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    # grabs information from the forms
    fname = request.form['firstName']
    lname = request.form['lastName']
    username = request.form['username']
    password = request.form['password']

    # cursor used to send queries
    cursor = connection.cursor()
    # executes query
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, username)
    # stores the results in a variable
    data = cursor.fetchone()
    error = None
    if data:
        # If the previous query returns data, then user exists
        error = "This username already exists"
        return render_template('register.html', error=error)
    else:
        ins = 'INSERT INTO Person (fname, lname, username, password) VALUES(%s, %s, %s, %s)'
        cursor.execute(ins, (fname, lname, username, password))
        connection.commit()
        cursor.close()
        return render_template('index.html')


# Login page
@app.route('/login')
def login():
    return render_template('login.html')


# Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    # grabs information from the forms
    user = request.form['username']
    password = request.form['password']
    # cursor used to send queries
    cursor = connection.cursor()
    # executes query
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (user, password))
    # stores the results in a variable
    data = cursor.fetchone()
    cursor.close()
    error = None
    if data:
        # creates a session for the the user
        # session is a built in function
        session['username'] = user
        return redirect(url_for('home'))
    else:
        # returns an error message to the html page
        error = 'Login Failed: Invalid login or email'
        return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')


# Homepage once logged in
@app.route('/home')
def home():
    return render_template('home.html', username=session['username'])


# Newsfeed
@app.route('/newsfeed', methods=["GET"])
def newsfeed():
    user = session['username']
    cursor = connection.cursor()
    query = 'SELECT Photo.photoOwner, Photo.photoID, Photo.timestamp, Photo.filePath, Photo.caption' \
            'FROM Photo JOIN Follow ON (Photo.photoOwner = Follow.followeeUsername) WHERE Follow.followerUsername ' \
            '= %s AND Photo.allFollowers = 1 AND Follow.acceptedfollow = 1 ORDER BY Photo.timestamp DESC'
    tagQuery = 'SELECT Tag.username, Tag.photoID FROM Photo JOIN Tag ON (Photo.photoID = Tag.photoID) JOIN Follow ' \
               'ON (Photo.photoOwner = Follow.followeeUsername) WHERE Follow.followerUsername = %s AND ' \
               'Tag.acceptedTag = 1'

    cursor.execute(query, user)
    data = cursor.fetchall()
    cursor.execute(tagQuery, user)
    tagData = cursor.fetchall()

    cursor.close()
    return render_template('newsfeed.html', images=data, tags=tagData)


# CloseFriendGroups
@app.route('/closeFriendGroup', methods=["GET"])
def closeFriendGroups():
    user = session['username']
    cursor = connection.cursor()
    query = 'SELECT Belong.groupName, Photo.photoOwner, Photo.photoID, Photo.timestamp, Photo.filePath, ' \
            'Photo.caption FROM Photo JOIN Share ON (Photo.photoID = Share.photoID) JOIN Belong ON' \
            '(Share.groupOwner = Belong.groupOwner) WHERE Belong.username = %s ORDER BY Photo.timestamp DESC'
    tagQuery = 'SELECT Tag.username, Tag.photoID FROM Photo JOIN Tag ON (Photo.photoID = Tag.photoID) JOIN Share ' \
               'ON (Tag.photoID = Share.photoID) JOIN Belong ON (Belong.groupName = Share.groupName) WHERE ' \
               'Belong.groupName = %s AND (Tag.acceptedTag = 1 OR Tag.acceptedTag = NULL)'
    cursor.execute(query, user)
    data = cursor.fetchall()
    cursor.execute(tagQuery, user)
    tagData = cursor.fetchall()
    cursor.close()
    return render_template('closeFriendGroup.html', images=data, tags=tagData)


@app.route('/authUpload', methods=["GET", "POST"])
def authUpload():
    user = session['username']
    path = request.form['filepath']
    caption = request.form['caption']
    friendGroup = request.form['closeFriendGroup']
    cursor = connection.cursor()
    if friendGroup == '':
        uploadPhoto = 'INSERT INTO Photo (photoOwner, filePath, caption, allFollowers) VALUES (%s, ' \
                  '%s, %s, 1)'
        cursor.execute(uploadPhoto, (user, path, caption))
        cursor.close()
    else:
        inGroup = 'SELECT groupName FROM Belong WHERE groupName = %s AND username = %s'
        groupExists = cursor.execute(inGroup, (friendGroup, user))
        if groupExists > 0:
            validGroup = cursor.fetchone()
            validGroup = validGroup['groupName']
            if friendGroup == validGroup:
                uploadPhoto = 'INSERT INTO Photo (photoOwner, filePath, caption, allFollowers) VALUES (%s, ' \
                          '%s, %s, 0)'
                cursor.execute(uploadPhoto, (user, path, caption))

                getID = 'SELECT photoID FROM Photo WHERE photoOwner = %s AND filePath = %s'
                cursor.execute(getID, (user, path))
                photoID = cursor.fetchone()
                photoID = photoID['photoID']

                getOwner = 'SELECT DISTINCT CloseFriendGroup.groupOwner FROM CloseFriendGroup JOIN Belong ON' \
                    '(CloseFriendGroup.groupOwner = Belong.groupOwner) WHERE Belong.groupName = %s'
                cursor.execute(getOwner, validGroup)
                owner = cursor.fetchone()
                owner = owner['groupOwner']

                shareWithGroup = 'INSERT INTO Share (groupName, groupOwner, photoID) VALUES (%s, %s, %s)'
                cursor.execute(shareWithGroup, (validGroup, owner, photoID))
                cursor.close()
            else:
                error = 'You tried to share a photo with an invalid friend group!'
                return render_template('errorPage.html', error=error)
        else:
            cursor.close()
            error = 'You tried to share a photo with an invalid friend group!'
            return render_template('errorPage.html', error=error)
    return render_template('home.html')


# Upload a photo
@app.route('/upload', methods=["GET", "POST"])
def upload():
    return render_template('upload.html')


@app.route('/acceptRequest', methods=["GET", "POST"])
def acceptRequest():
    user = session['username']
    follower = request.form['followerUsername']
    query = 'UPDATE Follow SET acceptedFollow = 1 WHERE followeeUsername = %s AND followerUsername = %s'
    cursor = connection.cursor()
    cursor.execute(query, (user, follower))
    cursor.close()
    return render_template('seeRequests.html')


@app.route('/declineRequest', methods=["POST"])
def declineRequest():
    user = session['username']
    follower = request.form['followerUsername']
    query = 'DELETE FROM Follow WHERE followeeUsername = %s AND followerUsername = %s'
    cursor = connection.cursor()
    cursor.execute(query, (user, follower))
    cursor.close()
    return render_template('seeRequests.html')


@app.route('/seeRequests', methods=["GET"])
def seeRequests():
    user = session['username']
    requestQuery = 'SELECT Follow.followerUsername, Person.fname, Person.lname FROM Follow JOIN Person ON (' \
                   'Follow.followerUsername = Person.username) WHERE followeeUsername = %s AND acceptedFollow = 0'
    cursor = connection.cursor()
    cursor.execute(requestQuery, user)
    requests = cursor.fetchall()
    return render_template('seeRequests.html', username=user, seeReqs=requests)


@app.route('/authFollow', methods=["GET", "POST"])
def authFollow():
    user = session['username']
    followee = request.form['toFollow']
    followValid = 'SELECT followeeUsername FROM Follow WHERE followerUsername = %s AND followeeUsername = %s'
    # ^ Returns 0 if follow request does not currently exist
    cursor = connection.cursor()
    validFollow = cursor.execute(followValid, (user, followee))

    if validFollow == 0:
        query = 'INSERT INTO Follow (followerUsername, followeeUsername, acceptedFollow) VALUES (%s, %s, 0)'
        cursor.execute(query, (user, followee))
        cursor.close()
        return render_template('follow.html')
    else:
        errorReason = 'SELECT acceptedfollow FROM Follow WHERE followerUsername = %s AND followeeUsername = %s'
        cursor.execute(errorReason, (user, followee))
        accepted = cursor.fetchone()
        accepted = accepted['acceptedfollow']
        if accepted == 0:
            error = 'You have already requested to follow this person and your request is pending.'
        else:
            error = 'You are already following this person!'
        cursor.close()
        return render_template('errorPage.html', error=error)


@app.route('/follow', methods=["GET", "POST"])
def follow():
    return render_template('follow.html')


# Manage follows
@app.route('/manageFollows', methods=["POST", "GET"])
def manageFollows():
    return render_template('manageFollows.html')


# Accept tag requests
@app.route('/acceptTagRequest', methods=["POST"])
def acceptTagRequest():
    user = session['username']
    photo = request.form['photoID']
    query = 'UPDATE Tag SET acceptedTag = 1 WHERE username = %s AND photoID = %s'
    cursor = connection.cursor()
    cursor.execute(query, (user, photo))
    cursor.close()
    return render_template('manageTags.html')


# Decline tag requests
@app.route('/declineTagRequest', methods=["POST"])
def declineTagRequest():
    user = session['username']
    photo = request.form['photoID']
    query = 'DELETE FROM Tag WHERE username = %s AND photoID = %s'
    cursor = connection.cursor()
    cursor.execute(query, (user, photo))
    cursor.close()
    return render_template('manageTags.html')


# Manage tags
@app.route('/manageTags', methods=["GET"])
def manageTags():
    user = session['username']
    tagQuery = 'SELECT Photo.photoOwner, Photo.timestamp, Photo.filePath, Photo.caption FROM Tag JOIN Photo ON ' \
               '(Tag.photoID = Photo.photoID) WHERE Tag.username = %s AND Tag.acceptedTag = 0'
    cursor = connection.cursor()
    cursor.execute(tagQuery, user)
    tagData = cursor.fetchall()
    cursor.close()
    return render_template('manageTags.html', username=user, tags=tagData)


# Tag someone
@app.route('/tagUser', methods=["POST", "GET"])  # App route is newsfeed because tag option is on newsfeed ???
def tagSomeone():
    tagUser = request.form['taggedUsername']
    photo = request.form['photoID']
    cursor = connection.cursor()

    validUser = 'SELECT DISTINCT Person.username FROM Person JOIN Follow ON (Person.username = ' \
                'Follow.followeeUsername) WHERE Follow.followeeUsername = %s AND acceptedFollow = 1'
    isValidUser = cursor.execute(validUser, tagUser)

    if isValidUser > 0:
        isValidUser = cursor.fetchone()
        isValidUser = isValidUser['username']
        query = 'INSERT INTO Tag (username, photoID, acceptedTag) VALUES (%s, %s, 0)'
        cursor.execute(query, (isValidUser, photo))
        cursor.close()
        return render_template('manageTags.html')
    else:
        error = 'You did not enter a valid username!'
        cursor.close()
        return render_template('errorPage.html', error=error)


# Add a friend to a closeFriendGroup
@app.route('/addCloseFriend')
def addCloseFriend():
    return render_template('addCloseFriend.html')


@app.route('/authAddCloseFriend', methods=["POST", "GET"])
def authAddCloseFriend():
    user = session['username']
    friend = request.form['closeFriend']
    group = request.form['friendGroup']
    cursor = connection.cursor()

    valid = 'SELECT username FROM Belong WHERE groupName = %s AND username = %s'
    # ^Checks to see if user is already in group
    owner = "SELECT groupOwner FROM CloseFriendGroup WHERE groupName = %s AND groupOwner = %s"
    # ^Checks that the owner of the group is the one adding a friend
    following = 'SELECT acceptedFollow FROM Follow WHERE followeeUsername = %s AND followerUsername = %s'

    inGroup = cursor.execute(valid, (group, friend))  # Should return 0 rows
    # inGroup = cursor.fetchone()

    cursor.execute(owner, (group, user))
    isOwner = cursor.fetchone()['groupOwner']

    cursor.execute(following, (friend, user))
    isFriend = cursor.fetchone()
    isFriend = isFriend['acceptedFollow']

    if (user == isOwner) and (inGroup == 0) and (isFriend == 1):
        addFriend = 'INSERT INTO Belong (groupName, groupOwner, username) VALUES (%s, %s, %s)'
        cursor.execute(addFriend, (group, user, friend))
        cursor.close()
    else:
        if user != isOwner:
            error = 'You do not have permission to add someone to this group!'
        elif inGroup > 0:
            error = 'This person is already in this group!'
        elif isFriend == 0:
            error = 'You are not friends with this person.  You can only add users you are friends with!'
        else:
            error = 'There was an error!  Either the user you tried to add does not exist, is already in this group, ' \
                    'or you do not have permissions to add users to this group.'
        cursor.close()
        return render_template('errorPage.html', error=error)
    return render_template('home.html')


if __name__ == "__main__":
    if not os.path.isdir('images'):
        os.mkdir(IMAGES_DIR)
    # app.run('127.0.0.1', 5000, debug=True)
    app.run(debug=True)
    # app.run()
