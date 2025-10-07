#!/bin/bash
# Complete code generation and analysis pipeline
# Generates code with LLM, then runs CodeQL and KLEE analysis

# Check if virtual environment is activated

echo "🚀 Starting Secure Code Generation Pipeline"
echo "=========================================="

source /scratch/$(whoami)/klee-venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Please run prerequisites-setup.sh first to set up the environment."
    exit 1
fi

# Check configuration
if [ -f "config.json" ]; then
    if grep -q "your_username" config.json || grep -q "your_huggingface_token_here" config.json; then
        echo "⚠️  Configuration needed!"
        echo "Please edit config.json and update:"
        echo "  - MODEL_PATH: Set to your model path or HuggingFace model name"
        echo "  - HUGGINGFACE_TOKEN: Add your HuggingFace token (if needed)"
        echo ""
        echo "Example models you can use:"
        echo "  - microsoft/DialoGPT-medium (already set)"
        echo "  - codellama/CodeLlama-7b-hf"
        echo "  - /path/to/your/local/model.gguf"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "❌ config.json not found!"
    exit 1
fi

# Step 1: Generate code with LLM
echo ""
echo "Step 1: Generating C code with LLM..."
python run_llm.py

if [ $? -ne 0 ]; then
    echo "❌ LLM code generation failed!"
    exit 1
fi

echo "✅ LLM code generation complete"

# Step 2: Run complete analysis
echo ""
echo "Step 2: Running security and symbolic execution analysis..."

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

# Remove any remaining non-C text (lines that don't look like C code)
sed -i '/^[A-Z][a-z].*[^;{}]$/d' generated_code/clean_code.c
sed -i '/^Here.*:/d' generated_code/clean_code.c
sed -i '/^This.*:/d' generated_code/clean_code.c
sed -i '/^The.*:/d' generated_code/clean_code.c
sed -i '/^\/\*$/,/^\*\//d' generated_code/clean_code.c
# Remove duplicate return statements (keep only the last one before closing brace)
awk '/return 0;/{if(seen) next; seen=1} !/return 0;/{seen=0} 1' generated_code/clean_code.c > generated_code/temp_clean.c && mv generated_code/temp_clean.c generated_code/clean_code.c

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
echo "🎉 Pipeline Complete!"
echo "===================="
echo ""
echo "📁 Results:"
echo "  - Generated code: generated_code/generated_code.c"
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
echo "  - View generated code: cat generated_code/generated_code.c"
echo "  - View clean code: cat generated_code/clean_code.c"
echo "  - Check KLEE output: ls -la klee_output/"
echo "  - Read test cases: /scratch/$(whoami)/klee/build/bin/ktest-tool klee_output/test*.ktest"