##ShowCredit Online Course Resume Builder

ShowCredit is a web application that lets users keep track of online
courses they have taken and build resumes with permanent links that
they can send to employers, schools, etc. to show their online
course work all in one place.

The app was created in flask using a postgresql database and bootstrap
for the front end.

##Running the application on localhost
* Clone the repo `git clone https://github.com/marknagelberg/showcredit`
* Install required python packages: flask, sqlalchemy, httplib2, oauth2client, requests, werkzeug, wtforms, flask-wtf, psycopg2
* Download a Google OAuth 2.0 client ID information (from developers.google.com) and save as client_secrets.json in the app's root directory
* Ensure you have a postgresql database initialized entitled 'showcredit'
* Run database_setup.py
* Run finalProject.py
* Access the app in a web browser at http://localhost:5000

##Current features:
* Login with Google (via OAuth 2.0)
* Add, delete, and edit courses
* Include images with courses, such as course logos
* Generate one or more resume web pages presenting selected courses
* Add and delete resumes
* JSON and XML APIs for accessing resumes programmatically
* Cross site request forgery protection via the Flask-WTF

##Planned features:
* Custom page to handle 404 errors and other errors
* Use Udacity, Coursera, and other online course APIs to limit course details students can add
and autofill forms
* Use the Coursera API so the user can automatically upload all courses they have taken via OAuth
* User analytics on user resume views
* Uploading and downloading of course certificates http://flask.pocoo.org/docs/0.10/patterns/fileuploads/

##Pushing to Heroku:
* git subtree push --prefix showcredit heroku master
http://stackoverflow.com/questions/18669963/cannot-push-to-heroku-after-adding-a-remote-heroku-repo-to-my-existing-local-rep

##Creator

**Mark Nagelberg**

* <https://twitter.com/MarkNagelberg>
* <https://github.com/marknagelberg>
* <https://kaggle.com/marknagelberg>
