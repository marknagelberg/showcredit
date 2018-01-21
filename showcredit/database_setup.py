'''
Database schema for ShowCredit.
'''

from sqlalchemy import Column, ForeignKey, Integer, String, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    '''
    Information on each user.
    '''
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    courses = relationship('Course', backref = 'user', cascade = 'delete, delete-orphan')
    resumes = relationship('Resume', backref = 'user', cascade = 'delete, delete-orphan')

class Course(Base):
    '''
    Information on each course added.
    '''
    __tablename__ = 'course'
    id = Column(Integer, primary_key = True)
    title = Column(String(250), nullable = False)
    description = Column(String(250), nullable = False)
    provider = Column(String(250), nullable = False)
    website = Column(String(250))
    image = Column(String(250))
    user_id = Column(Integer, ForeignKey('user.id'))
    resume_courses = relationship('ResumeCourse', backref = 'course', cascade = 'delete, delete-orphan')

class Resume(Base):
    '''
    Information describing attributes of each resume,
    including code (unique random string for resume),
    title, and the user that generated it.
    '''
    __tablename__ = 'resume'
    id = Column(Integer, primary_key = True)
    code = Column(String(250), unique = True, nullable = False)
    title = Column(String(250), nullable = False)
    user_id = Column(Integer, ForeignKey('user.id'))
    resume_courses = relationship('ResumeCourse', backref = 'resume', cascade = 'delete, delete-orphan')

class ResumeCourse(Base):
    '''
    Connects the resume and course tables together to provide
    distinct course lists for each resume.
    '''
    __tablename__ = 'resumecourse'
    id = Column(Integer, primary_key = True)
    code = Column(String(250), ForeignKey('resume.code'), nullable = False)
    course_id = Column(Integer, ForeignKey('course.id'))

engine = create_engine('postgresql:///showcredit')
Base.metadata.create_all(engine)
