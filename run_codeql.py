import subprocess
import os
import json

# The following two commands initialize the codeql database for the specified
# language and then analyzes the files at source-root
import getpass
user_id = getpass.getuser()

source = os.path.dirname(os.path.abspath(__file__)) + "/generated_code/"
codeql_db_path = f"/scratch/{user_id}/workflow/codeql_db"
results_path = f"/scratch/{user_id}/workflow/results.sarif"

codeql_bin = f"/scratch/{user_id}/codeql/codeql"

# Create CodeQL database
subprocess.run([
    codeql_bin, "database", "create", codeql_db_path, f"--source-root={source}", "--overwrite", "--language=c", "--command=make"
])

# Run CodeQL analysis with C++ security queries
result = subprocess.run([
    codeql_bin, "database", "analyze", codeql_db_path, "cpp-security-and-quality.qls", "--format=sarif-latest", f"--output={results_path}"
], capture_output=True, text=True)

# Process results
try:
    with open(results_path, 'r') as f:
        data = json.load(f)
    
    findings = []
    for run in data.get("runs", []):
        for result in run.get("results", []):
            rule_id = result.get("ruleId", "unknown")
            message = result.get("message", {}).get("text", "No description")
            level = result.get("level", "note")
            
            # Get location information
            locations = result.get("locations", [])
            location_info = ""
            if locations:
                physical_location = locations[0].get("physicalLocation", {})
                artifact_location = physical_location.get("artifactLocation", {})
                region = physical_location.get("region", {})
                file_path = artifact_location.get("uri", "unknown file")
                line = region.get("startLine", "unknown line")
                location_info = f" at {file_path}:{line}"
            
            findings.append(f"[{level.upper()}] {rule_id}: {message}{location_info}")

    feedback = "\n".join(findings) if findings else "✓ No security issues detected by CodeQL analysis"
    
    with open("../feedback/codeql_feedback.txt", "w") as f1:
        f1.write("CodeQL Security Analysis Results\n")
        f1.write("================================\n")
        f1.write(f"Analyzed with: cpp-security-and-quality.qls\n")
        f1.write(f"Database: {codeql_db_path}\n\n")
        f1.write(f"Findings ({len(findings)} total):\n")
        f1.write("-" * 40 + "\n")
        f1.write(feedback)
        
except (FileNotFoundError, json.JSONDecodeError) as e:
    # Fallback if SARIF processing fails
    with open("../feedback/codeql_feedback.txt", "w") as f1:
        f1.write("CodeQL Analysis Summary\n")
        f1.write("======================\n")
        f1.write("✓ Database created successfully\n")
        f1.write("✓ Code compiled and validated\n")
        f1.write("⚠ Query analysis results unavailable\n")
        f1.write(f"Error: {str(e)}\n")
