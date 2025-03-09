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

1. Prepare following images in the ```imgs/``` folder.

```
How2Use-1.png
How2Use-2.png
How2Use-3.png
How2Use-4.png
How2Use-5.png
How2Use-6.png
How2Use-7.png
How2Use-8.png
How2Use.pptx
ImgComp_256x256.ico
```

2. Download pyinstaller directly from git and do the following command to install pyinstaller otherwise exe file will be tracked as Trojan horse virus. Following script should help the installation of pyinstaller.

```shell
git clone https://github.com/pyinstaller/pyinstaller.git
cd ./pyinstaller
pip install .
```

3. Edit pdf2image.py and replace the lines as follows or do Monkey Patch to achieve changes below so that the brink of consoles when you run the exe will be eliminated.

```shell
# Replace
proc = Popen(command, env=env, stdout=PIPE, stderr=PIPE)
# with
startupinfo = None
if platform.system() == "Windows":
   # this startupinfo structure prevents a console window from popping up on Windows
   startupinfo = subprocess.STARTUPINFO()
   startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
processes.append(
   (
       thread_output_file,
       Popen(
           args, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo
       ),
   )
)
```
