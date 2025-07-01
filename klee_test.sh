#!/bin/bash
set -e

BITCODE_DIR="gen_build"
KLEE_OUT_DIR="klee_output"

mkdir -p "$KLEE_OUT_DIR"

for BC_FILE in "$BITCODE_DIR"/*.bc; do
    BASENAME=$(basename "$BC_FILE" .bc)
    OUT_DIR="$KLEE_OUT_DIR/$BASENAME"

    echo "Running KLEE on $BC_FILE -> $OUT_DIR"
    mkdir -p "$OUT_DIR"

    klee --output-dir="$OUT_DIR" "$BC_FILE"
done
