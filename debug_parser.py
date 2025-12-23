from utils.html_parser import parse_vtop_html
import os

def test_file(filename):
    print(f"Testing {filename}...")
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        result = parse_vtop_html(content)
        if result['course']:
            print(f"SUCCESS: Parsed {result['course']['code']}")
            print(f"Slots found: {len(result['slots'])}")
        else:
            print("FAILURE: No course info found.")
    except Exception as e:
        print(f"CRASH: {e}")

if __name__ == "__main__":
    test_file("CSE3010.html")
    test_file("VIT.mhtml")
