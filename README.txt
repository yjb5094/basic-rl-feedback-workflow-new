Current to-know info:
	* KLEE does not support:
	 	 fork(), exec()
		 Threads
		 Most malloc() patterns (unless simple or modeled)
		 Inline assembly
		 System calls (unless modeled by KLEE)
	* Also: KLEE can’t simulate I/O directly. You need to inject symbolic data with klee_make_symbolic()
	* For example: replace argv[10] with:
		 char* s[10];
		 klee_make_symbolic(s, sizeof(s), "input");
		 s[9] = '\0'

	* If you want to run CodeQL and KLEE, you need to manually make the Makefile. Currently, all generated c programs will need their own Makefile with the following requirements for both KLEE and CodeQL.
	
	clang -emit-llvm -c -g "$SRC" -o "${BASENAME}.bc"
	clang -g "$SRC" -o "${BASENAME}.out"
	klee "${BASENAME}.bc"
	
	
KLEE Script for testing in klee_test.sh: run in bitcode directory


Final Note: I wasn't able to effectively test the performance of running the LLM, merely that most of the code works to set up the env and the toolchain with codeql and KLEE.;


////

LLM uses a config.json to store parameters for LLM generation, as well as HF key for model download