"""Routes for HTML file upload and parsing."""

from flask import Blueprint, request, jsonify, session
from models import db, Course, Faculty, Slot
from utils.html_parser import parse_vtop_html

upload_bp = Blueprint('upload', __name__)
@upload_bp.route('/parse', methods=['POST'])
def parse_html_file():
    """
    Parse uploaded HTML file and extract course/slot information.
    Returns parsed data without saving to database.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith(('.html', '.htm', '.mhtml')):
        return jsonify({'error': 'File must be HTML or MHTML'}), 400
    
    try:
        html_content = file.read().decode('utf-8')
        parsed = parse_vtop_html(html_content)
        
        if not parsed['course']:
            return jsonify({'error': 'Could not parse course information from HTML'}), 400
        
        return jsonify({
            'success': True,
            'course': parsed['course'],
            'slots': parsed['slots'],
            'slot_count': len(parsed['slots'])
        })
        
    except Exception as e:
        return jsonify({'error': f'Error parsing file: {str(e)}'}), 500

@upload_bp.route('/import', methods=['POST'])
def import_html_file():
    """
    Parse uploaded HTML file and save course/slot data to database.
    Scoped to current user or guest.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith(('.html', '.htm', '.mhtml')):
        return jsonify({'error': 'File must be HTML or MHTML'}), 400
        
    # Determine owner
    user_id = session.get('user_id')
    guest_id = session.get('guest_id')
    
    if not user_id and not guest_id:
        return jsonify({'error': 'No active session'}), 401
    
    try:
        html_content = file.read().decode('utf-8')
        parsed = parse_vtop_html(html_content)
        
        if not parsed['course']:
            return jsonify({'error': 'Could not parse course information from HTML'}), 400
        
        course_data = parsed['course']
        
        # Check if course already exists FOR THIS USER
        query = Course.query.filter_by(code=course_data['code'])
        if user_id:
            query = query.filter_by(user_id=user_id)
        else:
            query = query.filter_by(guest_id=guest_id)
            
        course = query.first()
        
        if not course:
            # Create new course
            course = Course(
                code=course_data['code'],
                name=course_data['name'],
                l=course_data['l'],
                t=course_data['t'],
                p=course_data['p'],
                j=course_data['j'],
                c=course_data['c'],
                course_type=course_data['course_type'],
                category=course_data['category'],
                user_id=user_id,
                guest_id=guest_id
            )
            db.session.add(course)
            db.session.flush()
        
        # Add slots
        slots_added = 0
        for slot_data in parsed['slots']:
            # Get or create faculty
            faculty = None
            if slot_data['faculty']:
                faculty = Faculty.query.filter_by(name=slot_data['faculty']).first()
                if not faculty:
                    faculty = Faculty(name=slot_data['faculty'])
                    db.session.add(faculty)
                    db.session.flush()
            
            # Check if slot already exists for this course with same slot code and venue
            existing_slot = Slot.query.filter_by(
                course_id=course.id,
                slot_code=slot_data['slot_code'],
                venue=slot_data['venue']
            ).first()
            
            if not existing_slot:
                slot = Slot(
                    slot_code=slot_data['slot_code'],
                    course_id=course.id,
                    faculty_id=faculty.id if faculty else None,
                    venue=slot_data['venue'],
                    available_seats=slot_data['available_seats'],
                    total_seats=70,
                    class_nbr=slot_data.get('class_nbr')
                )
                db.session.add(slot)
                slots_added += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Imported {course_data["code"]} with {slots_added} new slots',
            'course': course_data,
            'slots_added': slots_added
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error importing file: {str(e)}'}), 500
