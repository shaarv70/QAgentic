from pathlib import Path
from config import OUTPUT_FOLDER

folder = Path(OUTPUT_FOLDER)

def save_to_file(requirement, answer):
    filename= requirement.lower().replace(" ","_")+".md"
    folder = Path(OUTPUT_FOLDER)
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/filename
    with open(path,"w") as file:

        file.write("Requirement\n")
        file.write("====================\n\n")
        file.write("requirement\n")  
        file.write("\n\n")
        file.write("Generated Test Cases\n")
        file.write("\n\n")
        file.write(answer)
    return path    
           
def read_file(path):
     with open(path,"r") as file:
        content=file.read()
        return content