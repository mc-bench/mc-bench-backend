import os


HERE = os.path.dirname(os.path.abspath(__file__))


build_script = os.path.join(HERE, "build.js")
export_script = os.path.join(HERE, "export.js")

def get_build_script():
    with open(build_script, "r") as f:
        return f.read()

def get_export_script():
    with open(export_script, "r") as f:
        return f.read()
