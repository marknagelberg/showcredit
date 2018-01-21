'''
All of the flask-wtf forms required by ShowCredit to add, edit, and delete
courses and resumes.
'''
from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import Required, URL

class CourseForm(Form):
    '''
    Form used to add new courses and edit existing courses.
    '''
    title = StringField('Title:', validators = [Required()])
    description = TextAreaField('Description:', validators = [Required()])
    provider = StringField('Course provider:', validators = [Required()])
    website = StringField('Website:', validators = [URL()])
    image = FileField('Image:')
    submit = SubmitField('Submit')

class ResumeForm(Form):
    '''
    Form to select courses in resume and give resume title.
    '''
    title = StringField('Title:', validators = [Required()])

class DeleteForm(Form):
    '''
    Form to delete courses and resumes.
    '''
    submit = SubmitField('Delete')
