"""Routes for auto-generating timetable suggestions."""

from flask import Blueprint, request, jsonify, session, render_template
from models import db, Course, Slot, Faculty, Registration, User
from utils.timetable_generator import TimetableGenerator, GenerationPreferences
import uuid

generate_bp = Blueprint('generate', __name__)


@generate_bp.route('/page')
def generate_page():
    """Dedicated timetable generation page."""
    current_user = None
    
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
    else:
        if 'guest_id' not in session:
            session['guest_id'] = str(uuid.uuid4())
    
    return render_template('generate.html', current_user=current_user)


def get_user_scope():
    """Get current user/guest scope for queries."""
    user_id = session.get('user_id')
    guest_id = session.get('guest_id')
    return user_id, guest_id


@generate_bp.route('/available', methods=['GET'])
def get_available_courses():
    """
    Get list of courses and faculties available for generation.
    Returns courses that have been imported but not yet registered.
    """
    user_id, guest_id = get_user_scope()
    
    if not user_id and not guest_id:
        return jsonify({'error': 'No active session'}), 401
    
    # Get all courses for this user
    if user_id:
        courses = Course.query.filter_by(user_id=user_id).all()
        registrations = Registration.query.filter_by(user_id=user_id).all()
    else:
        courses = Course.query.filter_by(guest_id=guest_id).all()
        registrations = Registration.query.filter_by(guest_id=guest_id).all()
    
    # Get registered course IDs
    registered_course_ids = set()
    for reg in registrations:
        if reg.slot and reg.slot.course_id:
            registered_course_ids.add(reg.slot.course_id)
    
    # Filter to unregistered courses and collect faculty info
    available_courses = []
    all_faculty_names = set()
    
    for course in courses:
        # Get faculties teaching this course
        faculties = set()
        for slot in course.slots.all():
            if slot.faculty:
                faculties.add(slot.faculty.name)
                all_faculty_names.add(slot.faculty.name)
        
        available_courses.append({
            'id': str(course.id),  # String to prevent JS precision loss
            'code': course.code,
            'name': course.name,
            'credits': course.c,
            'is_registered': course.id in registered_course_ids,
            'slot_count': course.slots.count(),
            'faculties': list(faculties)
        })
    
    return jsonify({
        'courses': available_courses,
        'all_faculties': sorted(list(all_faculty_names)),
        'registered_count': len(registered_course_ids),
        'debug': {
            'user_id': user_id,
            'guest_id': guest_id
        }
    })


@generate_bp.route('/count', methods=['POST'])
def count_timetables():
    """
    Count total valid timetable combinations.
    
    Request body:
    {
        "course_ids": ["1", "2", "3"],
        "preferences": {...}
    }
    """
    user_id, guest_id = get_user_scope()
    
    if not user_id and not guest_id:
        return jsonify({'error': 'No active session'}), 401
    
    data = request.get_json() or {}
    course_ids = data.get('course_ids', [])
    pref_data = data.get('preferences', {})
    
    if not course_ids:
        return jsonify({'count': 0, 'capped': False})
    
    # Convert string IDs to integers (handles JS precision issue)
    try:
        course_ids = [int(cid) for cid in course_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    # Get courses (scoped to user)
    if user_id:
        courses = Course.query.filter(
            Course.id.in_(course_ids),
            Course.user_id == user_id
        ).all()
    else:
        courses = Course.query.filter(
            Course.id.in_(course_ids),
            Course.guest_id == guest_id
        ).all()
    
    if not courses:
        return jsonify({'count': 0, 'capped': False})
    
    # Build preferences
    # Build preferences
    preferences = GenerationPreferences(
        avoid_early_morning=pref_data.get('avoid_early_morning', False),
        avoid_late_evening=pref_data.get('avoid_late_evening', False),
        prefer_morning=pref_data.get('prefer_morning', False),
        prefer_afternoon=pref_data.get('prefer_afternoon', False),
        preferred_faculties=pref_data.get('preferred_faculties', []),
        avoided_faculties=pref_data.get('avoided_faculties', []),
        exclude_slots=pref_data.get('exclude_slots', []),
        time_mode=pref_data.get('time_mode', 'none'),
        course_faculty_preferences=pref_data.get('course_faculty_preferences', {})
    )
    
    # Count solutions
    generator = TimetableGenerator(courses, preferences)
    max_count = 100000
    
    # Check for distinct mode
    mode = data.get('mode', 'std')
    if mode == 'distinct':
        count = generator.count_distinct_solutions(max_count=max_count)
    else:
        count = generator.count_solutions(max_count=max_count)
    
    # Debug: show slots per course after filtering
    slots_per_course = {}
    for course in courses:
        course_slots = generator.slot_map.get(course.id, [])
        slots_per_course[course.code] = len(course_slots)
    
    return jsonify({
        'count': count,
        'capped': count >= max_count,
        'debug': {
            'courses_count': len(courses),
            'slots_per_course': slots_per_course,
            'preferences': {
                'avoided_faculties': preferences.avoided_faculties
            }
        }
    })


@generate_bp.route('/suggest', methods=['POST'])
def suggest_timetable():
    """
    Generate initial batch of timetable suggestions.
    
    Request body:
    {
        "course_ids": [1, 2, 3],
        "preferences": {
            "time_mode": "morning",
            "avoid_early_morning": false,
            "avoid_late_evening": false,
            "preferred_faculties": ["FACULTY NAME"],
            "avoided_faculties": ["ANOTHER FACULTY"],
            "exclude_slots": ["A11", "B12"],
            "course_faculty_preferences": {"course_id": ["Fac1", "Fac2"]}
        }
    }
    """
    user_id, guest_id = get_user_scope()
    
    if not user_id and not guest_id:
        return jsonify({'error': 'No active session'}), 401
    
    data = request.get_json() or {}
    course_ids = data.get('course_ids', [])
    pref_data = data.get('preferences', {})
    
    if not course_ids:
        return jsonify({'error': 'No courses selected'}), 400
    
    # Ensure course_ids are integers
    try:
        course_ids = [int(cid) for cid in course_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    # Get courses (scoped to user)
    if user_id:
        courses = Course.query.filter(
            Course.id.in_(course_ids),
            Course.user_id == user_id
        ).all()
    else:
        courses = Course.query.filter(
            Course.id.in_(course_ids),
            Course.guest_id == guest_id
        ).all()
    
    if not courses:
        # Debug: provide more info about what exists
        all_user_courses = []
        if user_id:
            all_user_courses = Course.query.filter_by(user_id=user_id).all()
        else:
            all_user_courses = Course.query.filter_by(guest_id=guest_id).all()
        
        # Also check unscoped
        unscoped_courses = Course.query.filter(Course.id.in_(course_ids)).all()
        
        return jsonify({
            'error': 'No valid courses found',
            'debug': {
                'requested_ids': course_ids,
                'user_id': user_id,
                'guest_id': guest_id,
                'user_course_count': len(all_user_courses),
                'user_course_ids': [c.id for c in all_user_courses[:10]],  # First 10
                'unscoped_match_count': len(unscoped_courses),
                'unscoped_owner_info': [(c.id, c.user_id, c.guest_id) for c in unscoped_courses[:5]]
            }
        }), 404
    
    # Build preferences
    # Build preferences
    preferences = GenerationPreferences(
        avoid_early_morning=pref_data.get('avoid_early_morning', False),
        avoid_late_evening=pref_data.get('avoid_late_evening', False),
        prefer_morning=pref_data.get('prefer_morning', False),
        prefer_afternoon=pref_data.get('prefer_afternoon', False),
        preferred_faculties=pref_data.get('preferred_faculties', []),
        avoided_faculties=pref_data.get('avoided_faculties', []),
        exclude_slots=pref_data.get('exclude_slots', []),
        time_mode=pref_data.get('time_mode', 'none'),
        course_faculty_preferences=pref_data.get('course_faculty_preferences', {})
    )
    
    
    # Generate DIVERSE solutions (very different from each other)
    limit = data.get('limit', 5)
    try:
        limit = int(limit)
        limit = max(1, min(limit, 100))  # Clamp between 1 and 100
    except (ValueError, TypeError):
        limit = 5
        
    generator = TimetableGenerator(courses, preferences)
    
    # Unified Generation Strategy:
    # Handles all 4 scenarios internally:
    # 1. NO FILTERS: Random 100
    # 2. TIME ONLY: 20k random → rank by time → top 100
    # 3. TEACHER ONLY: 20k random → tier by teacher count → rank by priority → top 100
    # 4. TIME + TEACHER: 20k random → tier by teacher count → rank by time → top 100
    
    solutions = generator.generate_unified(target_size=limit)
    
    # Extract method from first solution's details
    generation_method = solutions[0].details.get('method', 'unknown') if solutions else 'none'
    pool_size = solutions[0].details.get('pool_size', 0) if solutions else 0
    
    return jsonify({
        'success': True,
        'suggestions': [s.to_dict() for s in solutions],
        'count': len(solutions),
        'has_more': False,
        'generation_method': generation_method,
        'total_combinations': pool_size,
        'relaxed_constraints': False  # Deprecated but kept for frontend compat
    })



@generate_bp.route('/more', methods=['POST'])
def generate_more():
    """
    Generate next batch of suggestions (progressive loading).
    
    Request body:
    {
        "course_ids": [1, 2, 3],
        "preferences": {...},
        "offset": 5
    }
    """
    user_id, guest_id = get_user_scope()
    
    if not user_id and not guest_id:
        return jsonify({'error': 'No active session'}), 401
    
    data = request.get_json() or {}
    course_ids = data.get('course_ids', [])
    pref_data = data.get('preferences', {})
    offset = data.get('offset', 0)
    
    if not course_ids:
        return jsonify({'error': 'No courses selected'}), 400
    
    # Ensure course_ids are integers
    try:
        course_ids = [int(cid) for cid in course_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid course ID format'}), 400
    
    # Get courses (scoped to user)
    if user_id:
        courses = Course.query.filter(
            Course.id.in_(course_ids),
            Course.user_id == user_id
        ).all()
    else:
        courses = Course.query.filter(
            Course.id.in_(course_ids),
            Course.guest_id == guest_id
        ).all()
    
    # Fallback if no courses found with scope filter
    if not courses:
        return jsonify({'error': 'No valid courses found'}), 404
    
    # Build preferences
    preferences = GenerationPreferences(
        avoid_early_morning=pref_data.get('avoid_early_morning', False),
        avoid_late_evening=pref_data.get('avoid_late_evening', False),
        prefer_morning=pref_data.get('prefer_morning', False),
        prefer_afternoon=pref_data.get('prefer_afternoon', False),
        preferred_faculties=pref_data.get('preferred_faculties', []),
        avoided_faculties=pref_data.get('avoided_faculties', []),
        exclude_slots=pref_data.get('exclude_slots', []),
        time_mode=pref_data.get('time_mode', 'none'),
        course_faculty_preferences=pref_data.get('course_faculty_preferences', {})
    )
    
    # Generate more solutions
    generator = TimetableGenerator(courses, preferences)
    solutions = generator.generate_batch(limit=5, offset=offset)
    
    return jsonify({
        'success': True,
        'suggestions': [s.to_dict() for s in solutions],
        'count': len(solutions),
        'offset': offset,
        'has_more': len(solutions) == 5
    })


@generate_bp.route('/apply', methods=['POST'])
def apply_suggestion():
    """
    Apply a timetable suggestion by registering all its slots.
    
    Request body:
    {
        "slot_ids": [1, 2, 3, 4]
    }
    """
    user_id, guest_id = get_user_scope()
    
    if not user_id and not guest_id:
        return jsonify({'error': 'No active session'}), 401
    
    data = request.get_json() or {}
    slot_ids = data.get('slot_ids', [])
    
    if not slot_ids:
        return jsonify({'error': 'No slots provided'}), 400
    
    # Convert string IDs to integers (handles JS precision issue)
    try:
        slot_ids = [int(sid) for sid in slot_ids]
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid slot ID format'}), 400
    
    # Get slots with their courses for ownership verification
    slots = Slot.query.filter(Slot.id.in_(slot_ids)).all()
    
    if len(slots) != len(slot_ids):
        return jsonify({'error': 'Some slots not found'}), 404
    
    # Security: Verify all slots belong to courses owned by this user/guest
    for slot in slots:
        if slot.course:
            course_owner_match = False
            if user_id and slot.course.user_id == user_id:
                course_owner_match = True
            elif guest_id and slot.course.guest_id == guest_id:
                course_owner_match = True
            
            if not course_owner_match:
                return jsonify({'error': 'Unauthorized: slot does not belong to your courses'}), 403
    
    try:
        # Clear existing registrations for this user (optional - could make this configurable)
        if user_id:
            Registration.query.filter_by(user_id=user_id).delete()
        else:
            Registration.query.filter_by(guest_id=guest_id).delete()
        
        # Create new registrations
        registrations = []
        for slot in slots:
            reg = Registration(slot_id=slot.id)
            if user_id:
                reg.user_id = user_id
            else:
                reg.guest_id = guest_id
            registrations.append(reg)
        
        db.session.add_all(registrations)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully registered {len(registrations)} courses',
            'registration_count': len(registrations)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
