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
    
    # Remove any code block markers (```c, ```)
    content = re.sub(r'```[a-zA-Z]*\n?', '', content)
    
    # Find the start and end of the main C code block
    lines = content.split('\n')
    code_lines = []
    
    # First pass: extract everything up to the first explanatory comment after main function
    main_started = False
    brace_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines at the beginning
        if not code_lines and not stripped:
            continue
        
        # Detect start of main function
        if 'int main(' in line:
            main_started = True
        
        # Skip explanatory comments that clearly indicate end of code
        if stripped.startswith('// This is') or stripped.startswith('// Note:') or stripped.startswith('// Warning:'):
            # If we're past the main function, this is explanatory text
            if main_started and brace_count == 0:
                break
            else:
                continue
        
        # Track braces only after main starts
        if main_started:
            brace_count += line.count('{') - line.count('}')
        
        code_lines.append(line)
        
        # If we've completed the main function (brace count back to 0), we can stop
        if main_started and brace_count == 0 and '}' in line:
            break
    
    # Join the cleaned lines
    cleaned_content = '\n'.join(code_lines)
    
    # Remove any duplicate code blocks that might appear after
    # Look for patterns like duplicate return statements and extra closing braces
    lines = cleaned_content.split('\n')
    final_lines = []
    main_function_ended = False
    
    for line in lines:
        stripped = line.strip()
        
        # If we see a standalone return 0; after the main function has ended, skip it
        if main_function_ended and stripped == 'return 0;':
            continue
        
        # If we see a standalone closing brace after main has ended, skip it
        if main_function_ended and stripped == '}':
            continue
            
        final_lines.append(line)
        
        # Mark when main function ends (closing brace at root level after return)
        if 'return 0;' in line and not main_function_ended:
            # Look ahead to see if next non-empty line is just a closing brace
            for j in range(len(final_lines), len(lines)):
                next_line = lines[j].strip()
                if next_line == '}':
                    main_function_ended = True
                    final_lines.append(lines[j])  # Add the closing brace
                    break
                elif next_line:  # Non-empty, non-brace line
                    break
            if main_function_ended:
                break
    
    # Final cleanup - ensure proper ending
    cleaned_content = '\n'.join(final_lines).rstrip()
    
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