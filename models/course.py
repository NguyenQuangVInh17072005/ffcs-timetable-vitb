from datetime import datetime
from .database import db


class Course(db.Model):
    """Course model representing a course in the curriculum."""
    
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    l = db.Column(db.Integer, default=0)  # Lecture hours
    t = db.Column(db.Integer, default=0)  # Tutorial hours
    p = db.Column(db.Integer, default=0)  # Practical hours
    j = db.Column(db.Integer, default=0)  # Project hours
    c = db.Column(db.Integer, default=0)  # Total credits
    course_type = db.Column(db.String(100), nullable=False)  # LT, ETH, ELA, etc.
    category = db.Column(db.String(50), nullable=False)  # UENSE, PC, etc.
    
    # Ownership
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to slots
    slots = db.relationship('Slot', backref='course', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Course {self.code}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'l': self.l,
            't': self.t,
            'p': self.p,
            'j': self.j,
            'c': self.c,
            'course_type': self.course_type,
            'category': self.category,
            'ltpjc': f'{self.l} {self.t} {self.p} {self.j} {self.c}'
        }
