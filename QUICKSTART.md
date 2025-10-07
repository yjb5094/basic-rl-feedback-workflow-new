# Quick Start Guide

## 🚀 Get Running in 3 Steps

### 1. Setup (One Time Only)
```bash
# Edit prerequisites-setup.sh and change USER_ID to your username
prerequisites-setup.sh

# Run complete setup (takes ~30-45 minutes)
chmod +x prerequisites-setup.sh
./prerequisites-setup.sh
```

### 2. Configure Your Model
```bash
# Edit config.json with your model path and HuggingFace token
nano config.json
```

### 3. Generate & Analyze Code
```bash
# Activate environment
source /scratch/your_username/klee-venv/bin/activate

# Run complete pipeline
./analysis.sh
```

## 📊 Expected Output
```
✓ Clean C code prepared: gen_build/clean_code.c
✓ CodeQL analysis complete
✓ Bitcode generated: gen_build/clean_code.bc
✓ KLEE analysis complete: klee_output/
Generated test cases: 3
Error files: 0
```

## 🔍 View Results
- **Generated Code**: `gen_build/clean_code.c`
- **Test Cases**: `klee_output/test*.ktest`
- **Security Analysis**: CodeQL results in terminal
- **Statistics**: `klee_output/info`

## ❓ Need Help?
See the full [README.md](README.md) for detailed documentation.