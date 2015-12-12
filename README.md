# GuyPS
A GPS application for Guy written on top of Kivy

## Install dependencies

### Install Cython
pip doesn't seem to pickup Cython from requirements.txt before installing kivy, so it must be installed first.
    pip install $(grep Cython requirements.txt)

### Install requirements
Then requirements from requirements.txt can be installed.
    pip install -r requirements.txt

### Run on desktop
    python main.py

## Compile, deploy & run on Android
    buildozer -v android debug deploy run logcat
