"""HTML Parser for VIT FFCS course pages."""

from bs4 import BeautifulSoup
import re


def parse_vtop_html(html_content):
    """
    Parse a VTOP course registration HTML page to extract course and slot information.
    Handles both registration page format and view slots format.
    
    Args:
        html_content: Raw HTML string from a saved VTOP page
        
    Returns:
        dict containing course info and list of slots
    """
    # Pre-process: Handle MHTML / Quoted-Printable
    if 'Content-Transfer-Encoding: quoted-printable' in html_content or 'MIME-Version:' in html_content:
        import quopri
        
        # Decode quoted-printable
        try:
            # Convert to bytes, decode, then back to string
            decoded_bytes = quopri.decodestring(html_content.encode('utf-8'))
            html_content = decoded_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"MHTML Decode Warning: {e}")

    # Strip headers looking for doctype or html tag
    match = re.search(r'(<!DOCTYPE html>|<html)', html_content, re.IGNORECASE)
    if match:
        html_content = html_content[match.start():]

    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        'course': None,
        'slots': []
    }
    
    # Try Format 1: Registration page (DIFFERENTIAL.html style)
    # Look for "Course Detail" header
    result = try_parse_registration_format(soup)
    
    if result['course']:
        return result
    
    # Try Format 2: View Slots page (CN.html / OS.html style)
    result = try_parse_view_slots_format(soup)
    
    return result


def try_parse_registration_format(soup):
    """Parse the registration page format (Course Detail header)."""
    result = {'course': None, 'slots': []}
    
    tables = soup.find_all('table')
    
    for table in tables:
        # Look for "Course Detail" header
        header = table.find(string=re.compile(r'Course Detail', re.IGNORECASE))
        if header:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    course_detail = cells[0].get_text(strip=True)
                    ltpjc = cells[1].get_text(strip=True)
                    course_type = cells[2].get_text(strip=True)
                    category = cells[3].get_text(strip=True)
                    
                    # Parse: "MAT2001 - Differential And Difference Equations - ..."
                    parts = course_detail.split(' - ')
                    if len(parts) >= 2:
                        course_code = parts[0].strip()
                        course_name = parts[1].strip()
                        
                        ltpjc_parts = ltpjc.split()
                        if len(ltpjc_parts) >= 5:
                            result['course'] = {
                                'code': course_code,
                                'name': course_name,
                                'l': int(ltpjc_parts[0]) if ltpjc_parts[0].isdigit() else 0,
                                't': int(ltpjc_parts[1]) if ltpjc_parts[1].isdigit() else 0,
                                'p': int(ltpjc_parts[2]) if ltpjc_parts[2].isdigit() else 0,
                                'j': int(ltpjc_parts[3]) if ltpjc_parts[3].isdigit() else 0,
                                'c': int(ltpjc_parts[4]) if ltpjc_parts[4].isdigit() else 0,
                                'course_type': course_type,
                                'category': category
                            }
                    break
            break
    
    if not result['course']:
        return result
    
    # Find slot table (Slot, Venue, Faculty headers)
    for table in tables:
        slot_header = table.find(string=re.compile(r'^Slot$', re.IGNORECASE))
        if slot_header:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    slot_code = cells[0].get_text(strip=True)
                    venue = cells[1].get_text(strip=True)
                    faculty = cells[2].get_text(strip=True)
                    
                    if slot_code.lower() in ['slot', 'slots', ''] or 'Slots' in slot_code:
                        continue
                    
                    available_seats = 0
                    for cell in cells:
                        span = cell.find('span')
                        if span:
                            seats_text = span.get_text(strip=True)
                            if seats_text.isdigit():
                                available_seats = int(seats_text)
                    
                    if slot_code and venue:
                        result['slots'].append({
                            'slot_code': slot_code,
                            'venue': venue,
                            'faculty': faculty,
                            'available_seats': available_seats,
                            'class_nbr': None
                        })
    
    return result


def try_parse_view_slots_format(soup):
    """Parse the View Slots page format (Course Code, Course Title headers)."""
    result = {'course': None, 'slots': []}
    
    tables = soup.find_all('table')
    
    # Find course info table (has Course Code and Course Title headers)
    for table in tables:
        code_header = table.find('th', string=re.compile(r'Course Code', re.IGNORECASE))
        title_header = table.find('th', string=re.compile(r'Course Title', re.IGNORECASE))
        
        if code_header and title_header:
            # Found course info table
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 8:  # Need Course Owner, Code, Title, L, T, P, J, C
                    # Find the cells with course code and title
                    # Structure: Course Owner, Course Code, Course Title, L, T, P, J, C, Pre-Requisite, Co-Requisite, Anti-Requisite
                    course_code = None
                    course_name = None
                    l_val = t_val = p_val = j_val = c_val = 0
                    
                    for i, cell in enumerate(cells):
                        text = cell.get_text(strip=True)
                        # Course codes are like CSE3006, MAT2001
                        if re.match(r'^[A-Z]{3}\d{4}$', text):
                            course_code = text
                            if i + 1 < len(cells):
                                course_name = cells[i + 1].get_text(strip=True)
                            # L, T, P, J, C should be next
                            if i + 2 < len(cells):
                                l_text = cells[i + 2].get_text(strip=True)
                                l_val = int(l_text) if l_text.isdigit() else 0
                            if i + 3 < len(cells):
                                t_text = cells[i + 3].get_text(strip=True)
                                t_val = int(t_text) if t_text.isdigit() else 0
                            if i + 4 < len(cells):
                                p_text = cells[i + 4].get_text(strip=True)
                                p_val = int(p_text) if p_text.isdigit() else 0
                            if i + 5 < len(cells):
                                j_text = cells[i + 5].get_text(strip=True)
                                j_val = int(j_text) if j_text.isdigit() else 0
                            if i + 6 < len(cells):
                                c_text = cells[i + 6].get_text(strip=True)
                                c_val = int(c_text) if c_text.isdigit() else 0
                            break
                    
                    if course_code and course_name:
                        result['course'] = {
                            'code': course_code,
                            'name': course_name,
                            'l': l_val,
                            't': t_val,
                            'p': p_val,
                            'j': j_val,
                            'c': c_val,
                            'course_type': 'LTP',
                            'category': ''
                        }
                        break
            break
    
    if not result['course']:
        return result
    
    # Find slots table (has Slot, Venue, Faculty headers)
    for table in tables:
        slot_header = table.find('th', string=re.compile(r'^Slot$', re.IGNORECASE))
        venue_header = table.find('th', string=re.compile(r'^Venue$', re.IGNORECASE))
        faculty_header = table.find('th', string=re.compile(r'^Faculty$', re.IGNORECASE))
        
        if slot_header and venue_header and faculty_header:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    # Structure: Course Type, Slot, Venue, Faculty, Slot Status, Total Seats, Alloted Seats, Available Seats
                    slot_code = cells[1].get_text(strip=True)
                    venue = cells[2].get_text(strip=True)
                    faculty = cells[3].get_text(strip=True)
                    
                    # Skip header-like rows
                    if not slot_code or slot_code.lower() in ['slot', 'slots']:
                        continue
                    
                    # Get available seats (last cell)
                    available_seats = 0
                    if len(cells) >= 8:
                        seats_text = cells[7].get_text(strip=True)
                        if seats_text.isdigit():
                            available_seats = int(seats_text)
                    
                    result['slots'].append({
                        'slot_code': slot_code,
                        'venue': venue,
                        'faculty': faculty,
                        'available_seats': available_seats,
                        'class_nbr': None
                    })
    
    return result


def parse_multiple_html_files(html_contents):
    """
    Parse multiple HTML files and combine results.
    """
    all_courses = []
    
    for html in html_contents:
        parsed = parse_vtop_html(html)
        if parsed['course']:
            all_courses.append(parsed)
    
    return {'courses': all_courses}
