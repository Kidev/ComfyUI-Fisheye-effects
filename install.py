import os
import sys
import subprocess
import pkg_resources

def install_requirements():
    requirements_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")

    with open(requirements_path) as f:
        required = f.read().splitlines()

    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = [pkg for pkg in required if pkg.split('>=')[0] not in installed]

    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
        print("All requirements installed successfully!")
    else:
        print("All requirements already satisfied!")

if __name__ == "__main__":
    install_requirements()
