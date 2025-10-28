#!/usr/bin/env python3
"""
Code cleaning script to extract valid C code from LLM-generated content.
Removes explanatory text, comments, and duplicate code blocks.
"""

import re
import sys

def clean_c_code(input_file, output_file):
    """Clean LLM-generated C code by removing explanatory text and duplicates."""
    
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Remove any code block markers (```c, ```, etc.)
    content = re.sub(r'```[a-zA-Z0-9]*\n?', '', content)
    
    lines = content.split('\n')
    code_lines = []
    in_code = False
    brace_count = 0
    main_ended = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines before code starts
        if not in_code and not stripped:
            continue
        
        # Skip non-code lines before we detect C code
        # C code starts with #include, struct/typedef declarations, or function definitions
        if not in_code:
            # Check if this line looks like C code
            if (stripped.startswith('#include') or 
                stripped.startswith('#define') or
                stripped.startswith('typedef ') or
                stripped.startswith('struct ') or
                stripped.startswith('int ') or
                stripped.startswith('void ') or
                stripped.startswith('char ') or
                stripped.startswith('float ') or
                stripped.startswith('double ') or
                stripped.startswith('long ') or
                stripped.startswith('unsigned ') or
                stripped.startswith('static ') or
                ('{' in line and not any(c.isalpha() for c in line[:line.index('{')]))):
                in_code = True
                # Don't add this line if it's just a stray character like '.' or ';'
                if len(stripped) <= 2:
                    continue
            else:
                # This is explanatory text, skip it
                continue
        
        # Once we're in code
        if in_code:
            # Skip lines that are clearly explanatory text (not C code)
            # Common patterns: ends with colon, contains "A:", "Q:", etc., or is pure prose
            if (stripped and not any(c in stripped for c in '{}();,=<>/*#') and
                len(stripped) > 20 and not stripped.startswith('//')):
                # This looks like explanatory text, skip it
                continue
            
            code_lines.append(line)
            
            # Track braces to know when functions end
            brace_count += line.count('{') - line.count('}')
            
            # Mark when we've closed all braces (end of last function)
            if in_code and brace_count == 0 and ('{' in ''.join(code_lines)):
                main_ended = True
            
            # Stop after we've closed all braces and found a closing brace
            if main_ended and brace_count == 0 and '}' in stripped:
                break
    
    # Join the cleaned lines
    cleaned_content = '\n'.join(code_lines).strip()
    
    # Final cleanup: remove any trailing explanatory text after the last }
    # Find the last closing brace
    last_brace = cleaned_content.rfind('}')
    if last_brace != -1:
        cleaned_content = cleaned_content[:last_brace + 1]
    
    # Write cleaned content
    with open(output_file, 'w') as f:
        f.write(cleaned_content)
    
    print(f"✓ Code cleaned: {input_file} -> {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 clean_code.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        clean_c_code(input_file, output_file)
    except Exception as e:
        print(f"Error cleaning code: {e}")
        sys.exit(1)
