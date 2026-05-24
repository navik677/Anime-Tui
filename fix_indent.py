with open("/home/ona/.gemini/antigravity/scratch/anime-tui/anime_tui/ui.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_while = False
for line in lines:
    if line.strip() == "while True:":
        in_while = True
        new_lines.append(line)
        continue
    
    if in_while and line.startswith("def _cleanup"):
        in_while = False
        new_lines.append(line)
        continue
        
    if in_while and line.strip() != "":
        new_lines.append("    " + line)
    elif in_while and line.strip() == "":
        new_lines.append("\n")
    else:
        new_lines.append(line)

with open("/home/ona/.gemini/antigravity/scratch/anime-tui/anime_tui/ui.py", "w") as f:
    f.writelines(new_lines)
