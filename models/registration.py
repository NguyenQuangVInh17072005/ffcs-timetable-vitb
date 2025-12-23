from datetime import datetime
from .database import db


class Registration(db.Model):
    """Registration model for user's registered course slots."""
    
    __tablename__ = 'registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_id = db.Column(db.String(100), nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to slot
    slot = db.relationship('Slot', backref=db.backref('registrations', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Registration {self.id} - Slot {self.slot_id}>'
    
    def to_dict(self):
        slot_data = self.slot.to_dict() if self.slot else None
        return {
            'id': str(self.id),
            'slot_id': str(self.slot_id),
            'slot': slot_data,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None
        }
