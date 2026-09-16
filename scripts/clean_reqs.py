import os

files = ["requirements-heavy.txt", "requirements-light.txt"]

for file in files:
    with open(file, "r") as f:
        lines = f.readlines()
    
    with open(file, "w") as f:
        for line in lines:
            line = line.strip()
            if not line:
                f.write("\n")
                continue
                
            if line.startswith("torch==") or line == "torch":
                f.write("torch==2.1.2+cu121\n")
            elif line.startswith("torchaudio==") or line == "torchaudio":
                f.write("torchaudio==2.1.2+cu121\n")
            elif line.startswith("torchvision==") or line == "torchvision":
                f.write("torchvision==0.16.2+cu121\n")
            elif "==" in line:
                pkg = line.split("==")[0]
                f.write(pkg + "\n")
            else:
                f.write(line + "\n")
