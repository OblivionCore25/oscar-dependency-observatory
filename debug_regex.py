import re

constraints = ["^2.4.3", "~1.0.0", ">= 3.4.5", "<2.0.0", "1.2.x", "3.0", "*", "latest"]
for c in constraints:
    match = re.search(r"(\d+\.\d+(?:\.\d+)?)", c)
    if match:
        print(f"{c:10} -> {match.group(1)}")
    else:
        print(f"{c:10} -> NONE")
