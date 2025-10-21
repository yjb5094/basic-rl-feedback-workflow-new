#!/bin/bash
# Analyze existing generated code with CodeQL and KLEE
# Use this when you want to re-analyze code without regenerating it

echo "🔍 Running Analysis on Existing Code"
echo "===================================="

# Check if generated code exists
if [ ! -f "generated_code/generated_code.c" ]; then
    echo "❌ No generated code found!"
    echo "Please run ./run_pipeline.sh first to generate code."
    exit 1
fi

# Clean up previous analysis
rm -rf klee_output

# Clean the generated code (remove any markdown or explanations if present)
if grep -q '```c' generated_code/generated_code.c; then
    # Extract code between ```c and ``` markers
    sed -n '/```c/,/```/p' generated_code/generated_code.c | sed '1d;$d' > generated_code/clean_code.c
else
    # If no markdown, just copy the file
    cp generated_code/generated_code.c generated_code/clean_code.c
fi

# Remove leading/trailing non-code lines
# Remove lines that are purely descriptive text (don't contain code-like patterns)
python3 << 'PYTHON_EOF'
import re

with open("generated_code/clean_code.c", "r") as f:
    content = f.read()

# First, remove any lines that are clearly instruction/prompt text
# These typically start with capital letters and have colpora of text
lines = content.split("\n")

# Remove leading lines that don't look like code
filtered = []
for line in lines:
    stripped = line.strip()
    # Skip empty lines at start
    if not filtered and not stripped:
        continue
    # Skip lines that start with "Write ", "Implement ", "Use ", etc (prompt echoes)
    if not filtered and any(stripped.startswith(prefix) for prefix in ["Write ", "Implement ", "Use ", "Create ", "Define ", "Building "]):
        continue
    filtered.append(line)

lines = filtered

# Find the first line that looks like C code
start_idx = 0
has_includes = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("#include"):
        has_includes = True
        start_idx = i
        break
    if (stripped.startswith("#define") or
        stripped.startswith("//") or
        re.match(r"^(int|void|char|float|double|struct|typedef|unsigned|signed|static|extern)", line) or
        stripped.startswith("/*")):
        start_idx = i
        break

# Find the last meaningful code line
end_idx = len(lines)
for i in range(len(lines) - 1, -1, -1):
    stripped = lines[i].strip()
    if stripped and (stripped[0] in ['}', '#'] or 'return' in stripped or ';' in stripped):
        end_idx = i + 1
        break

# Extract just the code
code_lines = lines[start_idx:end_idx]

# Clean up: remove very long lines of text (likely explanations)
cleaned = []
for line in code_lines:
    stripped = line.strip()
    # Skip lines that are clearly just prose/explanations (no code chars, and very long)
    if len(stripped) > 150 and not any(c in stripped for c in '(){};,=[]<>'):
        continue
    cleaned.append(line)

# Remove trailing comment-only lines at the end
while cleaned and cleaned[-1].strip().startswith("//"):
    cleaned.pop()

# If no includes were found, prepend standard ones
if not has_includes:
    cleaned = [
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "",
    ] + cleaned

# Write back
with open("generated_code/clean_code.c", "w") as f:
    f.write("\n".join(cleaned))
PYTHON_EOF

# Remove any remaining non-C text (lines that don't look like C code)
sed -i '/^[A-Z][a-z].*[^;{}]$/d' generated_code/clean_code.c
sed -i '/^Here.*:/d' generated_code/clean_code.c
sed -i '/^This.*:/d' generated_code/clean_code.c
sed -i '/^The.*:/d' generated_code/clean_code.c
sed -i '/^\/\*$/,/^\*\//d' generated_code/clean_code.c
# Remove duplicate return statements (keep only the last one before closing brace)
awk '/return 0;/{if(seen) next; seen=1} !/return 0;/{seen=0} 1' generated_code/clean_code.c > generated_code/temp_clean.c && mv generated_code/temp_clean.c generated_code/clean_code.c

# If the code doesn't have a main function, wrap it
if ! grep -q "int main" generated_code/clean_code.c; then
    # Just append a simple main - don't add includes again since they're already there
    {
        cat generated_code/clean_code.c
        echo ""
        echo "int main() {"
        echo "    return 0;"
        echo "}"
    } > generated_code/temp_clean.c && mv generated_code/temp_clean.c generated_code/clean_code.c
fi

echo "✓ Clean C code prepared: generated_code/clean_code.c"

# Create Makefile for CodeQL build in generated_code directory
cat > generated_code/Makefile << 'EOF'
all: clean_code.out

clean_code.out: clean_code.c
	gcc -g clean_code.c -o clean_code.out

clean:
	rm -f clean_code.out *.bc

.PHONY: all clean
EOF

# Run CodeQL analysis in generated_code directory
cd generated_code
source /scratch/$(whoami)/klee-venv/bin/activate
python ../run_codeql.py
deactivate
cd ..

# Generate bitcode for future KLEE analysis
export PATH="/scratch/$(whoami)/llvm-14/bin:$PATH"
if command -v clang >/dev/null 2>&1; then
    echo "Generating LLVM bitcode..."
    if clang -emit-llvm -c -g generated_code/clean_code.c -o generated_code/clean_code.bc 2>/dev/null; then
        echo "✓ Bitcode generated: generated_code/clean_code.bc"
    else
        echo "❌ Bitcode generation failed - C code has syntax errors"
        echo "Please check generated_code/clean_code.c for issues"
        exit 1
    fi
    
    # Run KLEE symbolic execution
    KLEE_BIN="/scratch/$(whoami)/klee/build/bin/klee"
    if [ -f "$KLEE_BIN" ]; then
        echo "Running KLEE symbolic execution..."
        KLEE_OUTPUT="klee_output"
        
        # Clean previous KLEE output
        rm -rf "$KLEE_OUTPUT"

        export LD_LIBRARY_PATH="/scratch/$(whoami)/z3-build/lib:/scratch/$(whoami)/sqlite/lib:$LD_LIBRARY_PATH"
        timeout 30s "$KLEE_BIN" --output-dir="$KLEE_OUTPUT" --write-test-info --write-kqueries generated_code/clean_code.bc
        
        if [ -d "$KLEE_OUTPUT" ] && [ "$(ls -A $KLEE_OUTPUT 2>/dev/null)" ]; then
            echo "✓ KLEE analysis complete: $KLEE_OUTPUT/"
            echo "Generated test cases:"
            TEST_COUNT=$(ls -1 "$KLEE_OUTPUT"/*.ktest 2>/dev/null | wc -l)
            ERROR_COUNT=$(ls -1 "$KLEE_OUTPUT"/*.err 2>/dev/null | wc -l)
            echo "  Test files: $TEST_COUNT"
            echo "  Error files: $ERROR_COUNT"
            
            if [ -f "$KLEE_OUTPUT/info" ]; then
                echo ""
                echo "KLEE Statistics:"
                grep -E "done:|Elapsed:" "$KLEE_OUTPUT/info" | head -5
            fi
        else
            echo "! KLEE completed but no output generated"
        fi
    else
        echo "! KLEE not available - bitcode ready for manual analysis"
    fi
else
    echo "! Clang not available - cannot generate bitcode"
fi

echo ""
echo "🎉 Analysis Complete!"
echo "==================="
echo ""
echo "📁 Results:"
echo "  - Original code: generated_code/generated_code.c"
echo "  - Clean C code: generated_code/clean_code.c"
echo "  - LLVM bitcode: generated_code/clean_code.bc"
echo "  - KLEE results: klee_output/"
echo ""

# Show summary statistics
if [ -d "klee_output" ] && [ "$(ls -A klee_output 2>/dev/null)" ]; then
    TEST_COUNT=$(ls -1 klee_output/*.ktest 2>/dev/null | wc -l)
    ERROR_COUNT=$(ls -1 klee_output/*.err 2>/dev/null | wc -l)
    
    echo "📊 KLEE Statistics:"
    echo "  - Test cases generated: $TEST_COUNT"
    echo "  - Error traces: $ERROR_COUNT"
    
    if [ -f "klee_output/info" ]; then
        echo "  - Execution time: $(grep 'Elapsed:' klee_output/info | cut -d' ' -f2)"
        echo "  - Paths explored: $(grep 'explored paths' klee_output/info | cut -d'=' -f2 | tr -d ' ')"
    fi
else
    echo "⚠️  No KLEE results found"
fi

echo ""
echo "🔍 To examine results:"
echo "  - View original code: cat generated_code/generated_code.c"
echo "  - View clean code: cat generated_code/clean_code.c"
echo "  - Check KLEE output: ls -la klee_output/"
echo "  - Read test cases: /scratch/$(whoami)/klee/build/bin/ktest-tool klee_output/test*.ktest"