#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinterdnd2 as tkdnd
from PIL import ImageTk, Image, ImageDraw,\
     ImageFont, ImageSequence, ImageChops #$conda install --force libtiff=4.0.10すること。
import pdf2image
import img2pdf
import io
import subprocess
import threading
import functools
import json

__appname__ = "画像比較"
__version__ = "8.0" #X.Y=Major Update (UI Change or Additional Function) . Minor Update (Bugfix etc.)
__date__    = "2023/02/26"
__deprecated__ = "Windows 10 64bit, Python 3.11.0, Poppler 23.01.0"
__status__ = "Production" #Production(正式リリース版) or Development(開発版)
__author__ = ["国内第二設計課 合田瑛志<aida_e@khi.co.jp>", "北米第二設計課 近藤晃弘<kondo_akihiro@khi.co.jp>"]
__copyright__ = "Copyright 2023, Kawasaki Railcar Manufacturing Corp., Ltd."
__credits__ = ["Eiji Aida", "Akihiro Kondo"]
__license__ = "GPLv3 (https://www.gnu.org/licenses/gpl-3.0.html)"

def main():
    app=Application()
    app.mainloop()

def do_nothing():
    pass

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(__appname__+"Ver."+__version__)
        self.iconbitmap(self.get_abs_path('./imgs/ImgComp_256x256.ico').replace('/', os.sep)) # Windows用アイコン設定
        self.geometry('500x400')
        self.minsize(430, 200)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.create_widgets()

    def create_widgets(self):
        self.menubar=Menubar(master=self)
        self.main_frame=MainFrame(master=self)
        self.progress_window_frame=ProgressWindowFrame(master=self)
        # self.how2use_window=How2UseWindow(master=self)
        # self.about_window=AboutWindow(master=self)

    def get_abs_path(self, relative_path): # 絶対パスを返す
        bundle_dir = os.path.abspath(os.path.dirname(__file__))
        absolute_path = os.path.join(bundle_dir, relative_path)
        return absolute_path

class Menubar(tk.Menu):
    def __init__(self, master):
        super().__init__(master)
        self.master.config(menu=self)
        self.create_file_menu()
        self.create_edit_menu()
        self.create_help_menu()

    def create_file_menu(self):
        self.file_menu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="ファイル", menu=self.file_menu)
        self.file_menu.add_command(label="旧図ファイル選択", command=do_nothing)
        self.file_menu.add_command(label="改訂図ファイル選択", command=do_nothing)
        self.file_menu.add_command(label="出力先フォルダ選択", command=do_nothing)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="実行", command=do_nothing)
        self.file_menu.add_command(label="中断", command=do_nothing)
        self.file_menu.entryconfig("中断", state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="終了", command=self.master.quit)

    def create_edit_menu(self):
        self.edit_menu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="編集", menu=self.edit_menu)
        self.edit_menu.add_command(label="切り取り", accelerator="Ctrl+X", command=do_nothing)
        self.edit_menu.add_command(label="コピー", accelerator="Ctrl+C", command=do_nothing)
        self.edit_menu.add_command(label="貼り付け", accelerator="Ctrl+V", command=do_nothing)
        self.edit_menu.add_command(label="全選択", accelerator="Ctrl+A", command=do_nothing)
        self.edit_menu.add_command(label="選択項目をクリア", command=do_nothing)
        self.edit_menu.add_command(label="全項目クリア", command=do_nothing)

    def create_help_menu(self):
        self.help_menu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="ヘルプ", menu=self.help_menu)
        self.help_menu.add_command(label="使い方", command=do_nothing)
        self.help_menu.add_command(label="バージョン情報", command=do_nothing)

class MainFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

class ProgressWindowFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

class How2UseWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

class AboutWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

class AidaCore:
    def save_tiff_stack(self, save_path, imgs_list, dpi_value):
        pass

    def save_pdf_stack(self, save_path, imgs):
        pass

    def img_comp(self):
        pass


if __name__ == "__main__":
    main()
