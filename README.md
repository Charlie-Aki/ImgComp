# ImgComp

GUI Application to Compare TIFF/PDF Images

# Usage

```shell
conda create -n ImgComp python=3.11.0
pip install -r requirements.txt
```

## Create ImgComp.exe

```shell
pyinstaller ImgComp.spec
```

## Remark

1. Download pyinstaller directly from git and do the following command to install pyinstaller otherwise exe file will be tracked as Trojan horse virus. Following script should help the installation of pyinstaller.

```shell
git clone https://github.com/pyinstaller/pyinstaller.git
cd ./pyinstaller
pip install .
```

2. Edit pdf2image.py and replace the lines as follows so that the brink of consoles when you run the exe will be eliminated.

```shell
# Replace
proc = Popen(command, env=env, stdout=PIPE, stderr=PIPE)
# with
proc = Popen(command, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo)
```

or do Monkey Patch to achieve above changes.
