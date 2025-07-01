import subprocess
import os
import json

# The following two commands initialize the codeql database for the specified
# language and then analyzes the files at source-root
source = os.path.dirname(os.path.abspath(__file__)) + "/gen_build/"
subprocess.run([
    "/opt/codeql/codeql", "database", "create", "codeql_db", f"--source-root={source}", "--overwrite", "--language=c", "--command=make"
])
subprocess.run([
    "/opt/codeql/codeql", "database", "analyze", "codeql_db", "--format=sarif-latest", "--output=results.sarif"
])

with open("results.sarif", 'r') as f:
    data = json.load(f)
# print(json.dumps(data, indent=4))
findings = []
for run in data.get("runs", []):
    for result in run.get("results", []):
        rule_id = result.get("ruleId")
        findings.append(rule_id)

feedback = "\n".join(findings)
#Can print here or save to a file
# print(feedback)
with open("feedback/codeql_feedback.txt", "w") as f1:
    f1.write(feedback)
