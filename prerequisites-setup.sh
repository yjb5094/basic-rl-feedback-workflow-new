#!/bin/bash
# Install key libraries for LLM

#Install llama-cpp-python with CUBLAS, compatible to CUDA 12.2 which is the CUDA driver build above
export LLAMA_CUBLAS=1
export CMAKE_ARGS=-DLLAMA_CUBLAS=on
export FORCE_CMAKE=1

#Install llama-cpp-python, cuda-enabled package
python -m pip install llama-cpp-python==0.2.7 --prefer-binary --extra-index-url=https://jllllll.github.io/llama-cpp-python-cuBLAS-wheels/AVX2/cu122

#Install pytorch-related, cuda-enabled package
pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu121
# install CodeQL
wget https://github.com/github/codeql-cli-binaries/releases/download/v2.21.1/codeql-linux64.zip


# replace opt with any directory you want to install codeql to
unzip codeql-linux64.zip -d /opt

# Add to PATH
export PATH=$PATH:/opt/codeql
# Install CodeQL query packs
codeql pack download codeql/cpp-all

# Install GPU Requirements; ignore errors for torch and cuda, as we installed specific versions earlier

pip install -r gpu_requirements.txt

# Install KLEE
# KLEE Requirements
xargs -a klee_requirements.txt sudo apt install -y
# Donwload and Build KLEE; Alternatively, use docker implementation, but I have no idea how to implement docker with aws
git clone https://github.com/klee/klee.git
cd klee
git submodule update --init --recursive
# Build uClibc for KLEE 
mkdir klee-uclibc
cd klee-uclibc
../klee/scripts/build/build-uclibc.sh
cd ..
# Finally Build KLEE with default settings.
mkdir build
cd build
cmake .. \
  -DENABLE_SOLVER_STP=OFF \
  -DENABLE_SOLVER_Z3=ON \
  -DKLEE_RUNTIME_BUILD_TYPE=Debug \
  -DLLVM_CONFIG_BINARY=/usr/lib/llvm-14/bin/llvm-config \
  -DENABLE_KLEE_UCLIBC=ON \
  -DKLEE_UCLIBC_PATH=../klee-uclibc/klee-uclibc \
  -G Ninja

ninja
# Check installation
ninja check
# Add to Path
sudo ln -s $(pwd)/bin/klee /usr/local/bin/klee
# Confirm KLEE Install
klee --version

# Install LLMs

python3 install_llms.py

echo "Pre-requisite Installation Complete."
