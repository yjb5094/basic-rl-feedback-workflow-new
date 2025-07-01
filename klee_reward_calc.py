import os
import glob

def collect_errors(feedback_dir, klee_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Compile errors
    for filepath in glob.glob(os.path.join(feedback_dir, '*.txt')):
        basename = os.path.basename(filepath).replace('.txt', '')
        with open(filepath) as f, open(os.path.join(output_dir, f"{basename}_compile_errors.txt"), "w") as out:
            for line in f:
                if 'error' in line.lower() or 'warning' in line.lower():
                    out.write(line)

    # KLEE errors
    for subdir in os.listdir(klee_dir):
        err_files = glob.glob(os.path.join(klee_dir, subdir, '*.err'))
        if err_files:
            with open(os.path.join(output_dir, f"{subdir}_klee_errors.txt"), "w") as out:
                for err_file in err_files:
                    with open(err_file) as ef:
                        out.write(ef.read())
# This is a test-code created to initially parse errors from KLEE and the compiler.
# This snippet can be used in the final reward calculation script, but as is, it just
# has a function to read klee output and provide feedback in form of txt in feedback folder.
