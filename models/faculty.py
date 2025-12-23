from .database import db


class Faculty(db.Model):
    """Faculty model representing a teacher/professor."""
    
    __tablename__ = 'faculties'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    
    # Relationship to slots
    slots = db.relationship('Slot', backref='faculty', lazy='dynamic')
    
    def __repr__(self):
        return f'<Faculty {self.name}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'department': self.department
        }
