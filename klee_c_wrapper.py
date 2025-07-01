import os
import sys
import re

def parse_function_signature(code):
    func_regex = re.compile(
        r"(\w[\w\s\*]+)\s+(\w+)\s*\(([^)]*)\)\s*{",
        re.MULTILINE
    )
    match = func_regex.search(code)
    if not match:
        raise ValueError("Could not parse function signature.")

    return_type, func_name, args = match.groups()
    args = [arg.strip() for arg in args.split(",") if arg.strip()]
    arg_types = []
    arg_names = []

    for arg in args:
        # Match arrays: e.g., char name[10]
        array_match = re.match(r'(.*\S)\s+(\w+)\s*\[(\d+)\]', arg)
        if array_match:
            typ, name, length = array_match.groups()
            arg_types.append((typ.strip(), int(length)))
            arg_names.append(name)
        else:
            parts = arg.rsplit(" ", 1)
            if len(parts) != 2:
                raise ValueError(f"Can't parse argument: {arg}")
            arg_types.append((parts[0].strip(), None))
            arg_names.append(parts[1])

    return return_type.strip(), func_name.strip(), arg_types, arg_names

def add_includes(code):
    headers = ['#include <klee/klee.h>', '#include <stdio.h>']
    lines = code.splitlines()
    existing = {line.strip() for line in lines if line.strip().startswith('#include')}
    new_includes = [inc for inc in headers if inc not in existing]
    return "\n".join(new_includes + [""] + lines)

def generate_main(func_name, arg_types, arg_names):
    lines = ['int main() {']
    for (typ, length), name in zip(arg_types, arg_names):
        if length is not None:
            lines.append(f'    {typ} {name}[{length}];')
            lines.append(f'    klee_make_symbolic({name}, sizeof({name}), "{name}");')
        else:
            lines.append(f'    {typ} {name};')
            lines.append(f'    klee_make_symbolic(&{name}, sizeof({name}), "{name}");')
    lines.append(f'    {func_name}({", ".join(arg_names)});')
    lines.append('    return 0;')
    lines.append('}')
    return "\n".join(lines)

def main():
    if len(sys.argv) != 3:
        print("Usage: python generate_klee_main.py <dir> <filename.c>")
        sys.exit(1)

    directory = sys.argv[1]
    filename = sys.argv[2]
    filepath = os.path.join(directory, filename)

    if not os.path.exists(filepath):
        print(f"Error: File {filepath} does not exist.")
        sys.exit(1)

    with open(filepath, 'r') as f:
        code = f.read()

    return_type, func_name, arg_types, arg_names = parse_function_signature(code)
    code_with_includes = add_includes(code)
    main_func = generate_main(func_name, arg_types, arg_names)

    with open(filepath, 'w') as f:
        f.write(code_with_includes)
        f.write("\n\n")
        f.write(main_func)

    print(f"Updated: {filepath}")

if __name__ == "__main__":
    main()
