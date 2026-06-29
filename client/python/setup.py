#!/usr/bin/env python3
import subprocess
import sys
import os

def setup_environment():
    """Setup virtual environment and install dependencies"""
    
    # Create virtual environment
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"])
    
    # Determine activation script path based on OS
    if os.name == 'nt':  # Windows
        activate_script = os.path.join("venv", "Scripts", "activate")
        pip_path = os.path.join("venv", "Scripts", "pip")
        python_path = os.path.join("venv", "Scripts", "python")
    else:  # Unix/Linux/macOS
        activate_script = os.path.join("venv", "bin", "activate")
        pip_path = os.path.join("venv", "bin", "pip")
        python_path = os.path.join("venv", "bin", "python")
    
    # Upgrade pip and build tools first to improve wheel resolution
    print("Upgrading pip/setuptools/wheel in the virtual environment...")
    upgrade = subprocess.run(
        [
            python_path,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        check=False,
    )
    if upgrade.returncode != 0:
        print(
            "Warning: Failed to upgrade pip/setuptools/wheel. "
            "Continuing anyway..."
        )

    # Install dependencies
    print("Installing dependencies...")
    install = subprocess.run(
        [pip_path, "install", "-r", "requirements.txt"], check=False
    )
    if install.returncode != 0:
        print("\nDependency installation failed.")
        print(
            "Make sure pip is up to date and that your system has any native "
            "build prerequisites needed by the dependencies."
        )
        sys.exit(install.returncode)
    
    print("\nSetup complete!")
    print("To activate the environment:")
    if os.name == 'nt':
        print("  .\\venv\\Scripts\\activate")
    else:
        print("  source venv/bin/activate")
    print("To run the application:")
    print("  python window_monitor.py")


if __name__ == "__main__":
    setup_environment()
