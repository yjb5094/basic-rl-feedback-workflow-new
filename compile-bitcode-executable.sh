#!/bin/bash
set -e

SRC_DIR="generated_code"
OUT_DIR="gen_build"
FEEDBACK_DIR="feedback"

mkdir -p "$OUT_DIR"
mkdir -p "$FEEDBACK_DIR"

for SRC in "$SRC_DIR"/*.c; do
    BASENAME=$(basename "$SRC" .c)
    OUT_BC="$OUT_DIR/$BASENAME.bc"
    OUT_EXE="$OUT_DIR/$BASENAME.out"
    FEEDBACK_FILE="$FEEDBACK_DIR/$BASENAME.txt"

    echo "Compiling $SRC..."

    # Capture compilation output and status
    clang -g "$SRC" -o "$OUT_EXE" >"$FEEDBACK_FILE" 2>&1
    STATUS=$?

    if [ $STATUS -eq 0 ]; then
        echo "Compilation succeeded for $SRC" >>"$FEEDBACK_FILE"
        # Optional: compile to LLVM bitcode only if native compilation succeeded
        clang -emit-llvm -c -g "$SRC" -o "$OUT_BC" >>"$FEEDBACK_FILE" 2>&1
    else
        echo "Compilation failed for $SRC" >>"$FEEDBACK_FILE"
        # Skip .bc generation
        continue
    fi

    echo "Built $BASENAME.{bc,out} -> $OUT_DIR/"
done
