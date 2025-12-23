from .database import db


class Slot(db.Model):
    """Slot model representing a course slot with timing, faculty, and venue."""
    
    __tablename__ = 'slots'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_code = db.Column(db.String(50), nullable=False)  # e.g., "A11+A12", "B21+E14"
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'), nullable=False)
    venue = db.Column(db.String(50), nullable=False)  # e.g., "CR-011", "AB02-330"
    available_seats = db.Column(db.Integer, default=0)
    total_seats = db.Column(db.Integer, default=70)
    class_nbr = db.Column(db.String(50), nullable=True)  # Unique class identifier
    
    def __repr__(self):
        return f'<Slot {self.slot_code} - {self.venue}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'slot_code': self.slot_code,
            'course_id': str(self.course_id),
            'course': self.course.to_dict() if self.course else None,
            'faculty_id': str(self.faculty_id),
            'faculty_name': self.faculty.name if self.faculty else None,
            'venue': self.venue,
            'available_seats': self.available_seats,
            'total_seats': self.total_seats,
            'class_nbr': self.class_nbr,
            'is_full': False  # No seat limit - always allow registration
        }
    
    def get_individual_slots(self):
        """Parse slot_code like 'A11+A12' into list ['A11', 'A12']."""
        return self.slot_code.replace('/', '+').split('+')


# Slot timing reference - maps slot codes to day and period
# Slot timing reference - matches timetable_grid.html
SLOT_TIMINGS = {
    # MONDAY
    'A11': {'day': 'MON', 'period': 1, 'start': '08:30', 'end': '10:00'},
    'B11': {'day': 'MON', 'period': 2, 'start': '10:05', 'end': '11:35'},
    'C11': {'day': 'MON', 'period': 3, 'start': '11:40', 'end': '13:10'},
    'A21': {'day': 'MON', 'period': 4, 'start': '13:15', 'end': '14:45'},
    'A14': {'day': 'MON', 'period': 5, 'start': '14:50', 'end': '16:20'},
    'B21': {'day': 'MON', 'period': 6, 'start': '16:25', 'end': '17:55'},
    'C21': {'day': 'MON', 'period': 7, 'start': '18:00', 'end': '19:30'},

    # TUESDAY
    'D11': {'day': 'TUE', 'period': 1, 'start': '08:30', 'end': '10:00'},
    'E11': {'day': 'TUE', 'period': 2, 'start': '10:05', 'end': '11:35'},
    'F11': {'day': 'TUE', 'period': 3, 'start': '11:40', 'end': '13:10'},
    'D21': {'day': 'TUE', 'period': 4, 'start': '13:15', 'end': '14:45'},
    'E14': {'day': 'TUE', 'period': 5, 'start': '14:50', 'end': '16:20'},
    'E21': {'day': 'TUE', 'period': 6, 'start': '16:25', 'end': '17:55'},
    'F21': {'day': 'TUE', 'period': 7, 'start': '18:00', 'end': '19:30'},

    # WEDNESDAY
    'A12': {'day': 'WED', 'period': 1, 'start': '08:30', 'end': '10:00'},
    'B12': {'day': 'WED', 'period': 2, 'start': '10:05', 'end': '11:35'},
    'C12': {'day': 'WED', 'period': 3, 'start': '11:40', 'end': '13:10'},
    'A22': {'day': 'WED', 'period': 4, 'start': '13:15', 'end': '14:45'},
    'B14': {'day': 'WED', 'period': 5, 'start': '14:50', 'end': '16:20'},
    'B22': {'day': 'WED', 'period': 6, 'start': '16:25', 'end': '17:55'},
    'A24': {'day': 'WED', 'period': 7, 'start': '18:00', 'end': '19:30'},

    # THURSDAY
    'D12': {'day': 'THU', 'period': 1, 'start': '08:30', 'end': '10:00'},
    'E12': {'day': 'THU', 'period': 2, 'start': '10:05', 'end': '11:35'},
    'F12': {'day': 'THU', 'period': 3, 'start': '11:40', 'end': '13:10'},
    'D22': {'day': 'THU', 'period': 4, 'start': '13:15', 'end': '14:45'},
    'F14': {'day': 'THU', 'period': 5, 'start': '14:50', 'end': '16:20'},
    'E22': {'day': 'THU', 'period': 6, 'start': '16:25', 'end': '17:55'},
    'F22': {'day': 'THU', 'period': 7, 'start': '18:00', 'end': '19:30'},

    # FRIDAY
    'A13': {'day': 'FRI', 'period': 1, 'start': '08:30', 'end': '10:00'},
    'B13': {'day': 'FRI', 'period': 2, 'start': '10:05', 'end': '11:35'},
    'C13': {'day': 'FRI', 'period': 3, 'start': '11:40', 'end': '13:10'},
    'A23': {'day': 'FRI', 'period': 4, 'start': '13:15', 'end': '14:45'},
    'C14': {'day': 'FRI', 'period': 5, 'start': '14:50', 'end': '16:20'},
    'B23': {'day': 'FRI', 'period': 6, 'start': '16:25', 'end': '17:55'},
    'B24': {'day': 'FRI', 'period': 7, 'start': '18:00', 'end': '19:30'},

    # SATURDAY
    'D13': {'day': 'SAT', 'period': 1, 'start': '08:30', 'end': '10:00'},
    'E13': {'day': 'SAT', 'period': 2, 'start': '10:05', 'end': '11:35'},
    'F13': {'day': 'SAT', 'period': 3, 'start': '11:40', 'end': '13:10'},
    'D23': {'day': 'SAT', 'period': 4, 'start': '13:15', 'end': '14:45'},
    'D14': {'day': 'SAT', 'period': 5, 'start': '14:50', 'end': '16:20'},
    'D24': {'day': 'SAT', 'period': 6, 'start': '16:25', 'end': '17:55'},
    'E23': {'day': 'SAT', 'period': 7, 'start': '18:00', 'end': '19:30'},
}




def get_slot_timing(slot_code):
    """Get timing info for a slot code."""
    return SLOT_TIMINGS.get(slot_code, None)
