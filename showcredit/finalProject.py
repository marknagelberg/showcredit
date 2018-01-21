'''
All of the ShowCredit code for handling HTTP requests, querying
the database, and rendering templates.
'''

#Standard library imports
import random
import string
import json
import os
import time
from xml.etree.ElementTree import Element, SubElement, tostring

#Third party library imports
import httplib2
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import requests
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, Response
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from flask import session as login_session
from flask import make_response
from werkzeug import secure_filename

#Local application imports
from forms import CourseForm, ResumeForm, DeleteForm
from database_setup import Base, User, Course, Resume, ResumeCourse

app = Flask(__name__)

#A list of permitted extensions for the course image files.
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

#Get the Google OAuth Client ID for the application
dir_path = os.path.dirname(os.path.realpath(__file__))
CLIENT_ID = json.loads(
    open(os.path.join(dir_path, 'client_secrets.json'), 'r').read())['web']['client_id']
APPLICATION_NAME = "showcredit"

app.secret_key = 'super_secret_key'
# Connect to Database and create database session
engine = create_engine('postgresql:///showcredit')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def welcome():
    '''
    Display the landing page
    '''
    return render_template('welcome.html')

@app.route('/login')
def login():
    '''
    Display the login page.
    '''

    #Create a random string to prevent cross-site scripting.
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state, google_client_id = CLIENT_ID)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''
    Handles the POST request generated when the user approves the app
    to get data on their Google account via OAuth. It first ensures
    the state token matches (to prevent CSRF), exchanges the users
    authorization code and client secret for an access token, then
    requests the user's data from Google.
    '''
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        dir_path = os.path.dirname(os.path.realpath(__file__))
        oauth_flow = flow_from_clientsecrets(os.path.join(dir_path, 'client_secrets.json'), scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check to see if the user is already logged in.
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # See if user exists in database, if they don't - make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    flash("You are now logged in as %s" % login_session['username'])

    return render_template('logintransition.html', login_session = login_session)

########################
# User Helper Functions#
########################

def createUser(login_session):
    '''
    Add a new user to the database. Login session must have username, 
    email, and picture keys. Returns the id of the added user.
    '''
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    '''
    Returns the record for a user with a given user id from the
    User database table.
    '''
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    '''
    Use the user's email to retrieve their record id
    in the User database.
    '''
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

###############################
###############################

def allowed_file(filename):
    '''
    Return true or false depending on whether the filename is a
    valid course image file extension. Idea is borrowed from
    http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
    '''
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1]

@app.route('/allcourses')
def fullCourseList():
    '''
    Display the dashboard listing all of the user's courses and links
    to edit/delete/add new courses.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    else:
        courses = session.query(Course).filter_by(user_id=login_session['user_id'])

        #Must send time variable to template to ensure that new images appear when they are updated.
        #http://stackoverflow.com/questions/126772/how-to-force-a-web-browser-not-to-cache-images
        #Without this, you have to refresh page to see changed images.
        response = make_response(render_template('allcourses.html', courses = courses, time = time.time()))
        return response

@app.route('/courses/new', methods = ['GET', 'POST'])
def addCourse():
    '''
    Add a new course to the course dashboard.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    form = CourseForm()
    if form.validate_on_submit():
        title = form.title.data
        user_id = login_session['user_id']
        description = form.description.data
        provider = form.provider.data
        website = form.website.data

        #If user uploaded an image file, ensure the filename is secure,
        #then save the file to the filesystem and create a path
        #to the file in the database.
        #http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
        file = form.image.data
        if file:
            filename = secure_filename(file.filename)
        if file and allowed_file(filename):

            newCourse = Course(title = request.form['title'], user_id = login_session['user_id'],
                               description = request.form['description'], provider = request.form['provider'],
                               website = request.form['website'])
            session.add(newCourse)

            session.commit()
            #The purpose of this line is to ensure that newCourse.id is
            #accessable - need it to name the image file on filesystem
            #http://stackoverflow.com/questions/1316952/sqlalchemy-flush-and-get-inserted-id
            session.refresh(newCourse)

            image_destination = 'static/course_images/%s_%s.%s' % (user_id, newCourse.id, get_file_extension(filename))
            file.save(dst = image_destination)
            newCourse.image = image_destination
            session.commit()
        else:
            newCourse = Course(title = request.form['title'], user_id = login_session['user_id'],
                               description = request.form['description'], provider = request.form['provider'],
                               website = request.form['website'], image = None)
            session.add(newCourse)
            session.commit()

        flash('New course %s added!' % newCourse.title)
        return redirect(url_for('fullCourseList'))
    else:
        return render_template('newcourse.html', form = form)

@app.route('/courses/<int:course_id>/edit_course', methods = ['GET','POST'])
def editCourse(course_id):
    '''
    Edit a course on the user's dashboard.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    editedCourse = session.query(Course).filter_by(id = course_id).one()
    if editedCourse.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this course. Please create your own course in order to edit.');}</script><body onload='myFunction()''>"
    form = CourseForm()
    if form.validate_on_submit():
        editedCourse.title = form.title.data
        editedCourse.user_id = login_session['user_id']
        editedCourse.description = form.description.data
        editedCourse.provider = form.provider.data
        editedCourse.website = form.website.data

        #http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
        file = form.image.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            session.add(editedCourse)
            session.commit()
            #The purpose of this line is to ensure that editedCourse.id is
            #accessable - need it to name the image file on filesystem
            #http://stackoverflow.com/questions/1316952/sqlalchemy-flush-and-get-inserted-id
            session.refresh(editedCourse)

            image_destination = 'static/course_images/%s_%s.%s' % (editedCourse.user_id, editedCourse.id, get_file_extension(filename))
            #If there existed a previous image for the course, delete it from filesystem.
            if editedCourse.image:
                os.remove(editedCourse.image)
            file.save(dst = image_destination)
            editedCourse.image = image_destination
            session.add(editedCourse)
            session.commit()
        session.add(editedCourse)
        session.commit()
        flash('Course successfully edited %s' % editedCourse.title)
        return redirect(url_for('fullCourseList'))
    else:
        #Since course description is TextArea input type, need to
        #prepopulate it with statement below.
        form.description.data = editedCourse.description
        return render_template('editcourse.html', course=editedCourse, time = time.time(), form = form)

@app.route('/courses/<int:course_id>/delete_course', methods = ['GET', 'POST'])
def deleteCourse(course_id):
    '''
    Delete a course from the user's course dashboard.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    deletedCourse = session.query(Course).filter_by(id = course_id).one()
    form = DeleteForm()
    if deletedCourse.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this course. Please create your own course in order to edit.');}</script><body onload='myFunction()''>"
    if form.validate_on_submit():
        if deletedCourse.image != None:
            os.remove(deletedCourse.image)
        session.delete(deletedCourse)
        flash('%s Successfully Deleted' % deletedCourse.title)
        session.commit()
        return redirect(url_for('fullCourseList'))
    else:
        return render_template('deleteCourse.html', course=deletedCourse, form = form)

@app.route('/allresumes')
def fullResumeList():
    '''
    Display the dashboard listing all of the user's resumes and links to
    view/delete/create new resumes.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    else:
        resumes = session.query(Resume).filter_by(user_id=login_session['user_id'])
        response = make_response(render_template('allresumes.html', resumes = resumes))
        return response

@app.route('/create_resume', methods = ['GET', 'POST'])
def createResume():
    '''
    Add a new resume to the resume dashboard. Resumes are
    given a unique URL that users can share them. They are accessible
    to anyone with the URL.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    form = ResumeForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = getUserInfo(user_id=login_session['user_id'])
        #Create unique code for resume to use in the resume's URL.
        code = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(6))

        #In the unlikely event resume code already exists, create a new one.
        while session.query(Resume).filter_by(code = code).first():
            code = ''.join(random.choice(string.ascii_uppercase + string.digits)
                            for x in xrange(6))

        #Store the courses required for the resume.
        course_ids_for_resume = request.form.getlist('course')
        for course_id in course_ids_for_resume:
            courseAndResume = ResumeCourse(code = code, course_id = course_id)
            session.add(courseAndResume)
        newResume = Resume(code = code, user_id = user.id, title = form.title.data)
        session.add(newResume)
        session.commit()
        flash('New Resume Successfully Created')
        return redirect(url_for('fullResumeList', code=code, user_id = login_session['user_id']))
    else:
        courses = session.query(Course).filter_by(user_id = login_session['user_id'])
        return render_template('newresume.html', courses = courses, time = time.time(), form = form)

@app.route('/delete_resume/<code>', methods = ['GET', 'POST'])
def deleteResume(code):
    '''
    Delete a resume from the user's resume dashboard.
    '''
    if 'username' not in login_session:
        return redirect(url_for('welcome'))
    deletedResume = session.query(Resume).filter_by(code = code).one()
    form = DeleteForm()

    if deletedResume.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this resume. Please create your own course in order to edit.');}</script><body onload='myFunction()''>"
    if form.validate_on_submit():
        session.delete(deletedResume)
        session.commit()
        flash('Successfully Deleted Resume')
        return redirect(url_for('fullResumeList'))
    else:
        return render_template('deleteResume.html', resume=deletedResume, form = form)

@app.route('/<int:user_id>/<code>')
def showResume(user_id, code):
    '''
    Display the resume with the given user id and code.
    '''
    resumeExists = session.query(Resume).filter_by(user_id = user_id).filter_by(code = code)
    if resumeExists:
        courses = session.query(ResumeCourse,Course).join(Course).filter(ResumeCourse.code == code)
        resume = session.query(Resume).filter_by(code = code).one()
        return render_template('resume.html', courses = courses, resume = resume, time = time.time())
    else:
        return redirect(url_for('welcome'))

@app.route('/<int:user_id>/<code>/JSON')
def showResumeJSON(user_id, code):
    '''
    Make a JSON API endpoint to access resume data (GET request)
    '''
    resumeExists = session.query(Resume).filter_by(user_id=user_id).filter_by(code=code)
    if resumeExists.all():
        courses = session.query(ResumeCourse,Course).join(Course).filter(ResumeCourse.code == code)
        resume = session.query(Resume).filter_by(code = code).one()
        json_dict = {'resume_title': resume.title,
                     'courses': []}
        for course in courses:
            json_dict['courses'].append({'title': course.Course.title,
                                         'description': course.Course.description,
                                         'provider':course.Course.provider,
                                         'website': course.Course.website,
                                         'image_path':course.Course.image})
        return jsonify(json_dict)
    else:
        return "Incorrect url - no resume to return"

@app.route('/<int:user_id>/<code>/XML')
def showResumeXML(user_id, code):
    '''
    Make an XML API endpoint (GET request) to access resume data.
    Note that the following stack exchange threads were
    helpful for building this routine:
    http://stackoverflow.com/questions/11773348/python-flask-how-to-set-content-type
    http://stackoverflow.com/questions/3844360/best-way-to-generate-xml-in-python
    '''
    resumeExists = session.query(Resume).filter_by(user_id=user_id).filter_by(code=code)
    if resumeExists.all():
        courses = session.query(ResumeCourse,Course).join(Course).filter(ResumeCourse.code == code)
        resume = session.query(Resume).filter_by(code = code).one()
        resume_root = Element('resume')
        title = SubElement(resume_root, 'title')
        title.text = resume.title
        courses_tag = SubElement(resume_root, 'courses')

        for course in courses:
            course_tag = SubElement(courses_tag, 'course')
            course_title = SubElement(course_tag, 'title')
            course_title.text = course.Course.title
            course_description = SubElement(course_tag, 'description')
            course_description.text = course.Course.description
            course_provider = SubElement(course_tag, 'provider')
            course_provider.text = course.Course.provider
            course_website = SubElement(course_tag, 'website')
            course_website.text = course.Course.website
            course_image = SubElement(course_tag, 'image_path')
            course_image.text = course.Course.image
        return Response(tostring(resume_root), mimetype='text/xml')
    else:
        return "Incorrect url - no resume to return"

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
