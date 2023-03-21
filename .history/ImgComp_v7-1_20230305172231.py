#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
---プログラム概要---
TIFFかPDFファイルの比較を行い、差分(違う部分)を抽出する。

---Ver.7.1---
・左上の文字色を変更
・保存先でファイルが開かれていたらエラー表示するようエラーメッセージ追加
・メインプログラムで予期せぬエラー発生時にプログラムを終了するExceptを作成(ERR_DETECT_IMGCOMP.txtが出力される)
・入力値のDPIを出力に渡すように修正(画像サイズが同じになる)
・メニュー追加
・出力選択用チェックボックス追加
・エントリーにファイル・フォルダーをドロップできるよう機能追加(conda install -c gagphil1 tkinterdnd2)
・タイトルを「図面比較」から「画像比較」に変更
・出力フォルダとチェックボックスをjson形式の設定ファイルに記憶させるようにした。

---pdf2imageモジュール内部の書き換え---
pyinstallerでGUI化した後、img2pdfでpopplerが呼び出される際にコンソールが立ち上がってしまう。
これを防ぐにはimg2pdfの中のimportに
「import subprocess」
を追加し、各
「if poppler_path is not None:」
の前に
「
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE
」
を追加。
Popenの引数にstartupinfo=startupinfoを追記。
例：
processes.append(
    (thread_output_file, Popen(args, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo))
)

このモジュール書き換え作業をしていなくても一応動くけどコンソールが表示されてしまうというだけ。
本当はモンキーパッチという作業をするべきですが手間なのでこのアプリケーションを開発している仮想環境内のモジュールを書き換えました。

"""

__appname__ = "画像比較"
__version__ = "7.1" #X.Y=Major Update (UI Change or Additional Function) . Minor Update (Bugfix etc.)
__date__    = "2021/02/03" #Latest Update Date
__deprecated__ = "Windows 10 64bit, Python 3.8.2, Poppler 0.68.0" #Recommended environment
__status__ = "Production" #Production=under updating
__author__ = ["国内第二設計課 合田瑛志<aida_e@khi.co.jp>", "北米第二設計課 近藤晃弘<kondo_akihiro@khi.co.jp>"] #who actually wrote code
__copyright__ = "Copyright 2021, Rolling Stock Company, Kawasaki Heavy Industries, Ltd."
__credits__ = ["Eiji Aida", "Akihiro Kondo"] #who advised
__license__ = "GPLv2 (https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)" #if somebody requests the code, authors must provide it while MIT did not force it.


import os
import TkinterDnD2 as tkdnd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import ImageTk, Image, ImageDraw,\
     ImageFont, ImageSequence, ImageChops #$conda install --force libtiff=4.0.10すること。
import pdf2image
import img2pdf
import io
import subprocess
import threading
import functools
import json

class Application(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.icon_file_path = "./imgs/ImgComp_256x256.ico".replace("/", os.sep)
        self.setting_file_path = os.environ["LOCALAPPDATA"]+r"\ImgComp\図面比較\settings.json" #Win版リリース用
        # self.setting_file_path = "./settings.json".replace("/", os.sep) #テスト用
        self.settings = self.init_settings(self.setting_file_path)

        self.master.title(__appname__+"Ver."+__version__)
        self.master.iconbitmap(self.icon_file_path) #Works only on Windows OS
        self.master.geometry("500x400")
        self.master.minsize(430, 200)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=0)
        self.master.grid_rowconfigure(1, weight=1)

        self.create_widgets()
        self.started = threading.Event() # Event Object

####################################### GUI作成 ###############################################
    # Create Widgets (GUI Parts)
    def create_widgets(self):
        # Frames Style Settings
        self.s=ttk.Style()
        self.s.theme_use('vista')
        self.s.configure('WFrame1.TFrame')#, background='red') #設定できるように残してるけど特に何も設定してない。
        self.s.configure('WFrame2.TFrame')#, background='green') #設定できるように残してるけど特に何も設定してない。

        #--------------- Menubar ---------------#
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # Create FileMenu
        self.file_menu = tk.Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="ファイル", menu=self.file_menu)
        self.file_menu.add_command(label="旧図ファイル選択", command=self.old_entry_dialogue)
        self.file_menu.add_command(label="改訂図ファイル選択", command=self.new_entry_dialogue)
        self.file_menu.add_command(label="出力先フォルダ選択", command=self.outdir_entry_dialogue)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="実行", command=self.start_thread_main)
        self.file_menu.add_command(label="中断", command=self.stop_program)
        self.file_menu.entryconfig("中断", state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="終了", command=self.master.quit)

        # Create EditMenu
        self.edit_menu = tk.Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="編集", menu=self.edit_menu)
        self.edit_menu.add_command(label="切り取り", accelerator="Ctrl+X", command=lambda: self.master.focus_get().event_generate("<<Cut>>"))
        self.edit_menu.add_command(label="コピー", accelerator="Ctrl+C", command=lambda: self.master.focus_get().event_generate("<<Copy>>"))
        self.edit_menu.add_command(label="貼り付け", accelerator="Ctrl+V", command=lambda: self.master.focus_get().event_generate("<<Paste>>"))
        self.edit_menu.add_command(label="全選択", accelerator="Ctrl+A", command=lambda: self.master.focus_get().event_generate("<<SelectAll>>"))
        self.edit_menu.add_command(label="選択項目をクリア", command=lambda: self.master.focus_get().delete(0, tk.END))
        self.edit_menu.add_command(label="全項目クリア", command=self.clear_all)

        # Create HelpMenu
        self.help_menu = tk.Menu(self.menubar, tearoff=False)
        self.menubar.add_cascade(label="ヘルプ", menu=self.help_menu)
        self.help_menu.add_command(label="使い方", command=self.show_how2use)
        self.help_menu.add_command(label="バージョン情報", command=self.show_about)


        #--------------- Frame 1 (Selection of Files and Directory) ---------------#
        # Create Frame1
        self.WFrame1 = ttk.Frame(self.master, style='WFrame1.TFrame')
        self.WFrame1.grid(row=0, column=0, padx=10, pady=5, sticky='EW')
        self.WFrame1.grid_columnconfigure(1, weight=1)
        self.WFrame1.grid_columnconfigure(2, weight=1)

        # Create Labels for Frame1
        self.old_dialogue_label = ttk.Label(self.WFrame1, text="旧図ファイル選択:")
        self.new_dialogue_label = ttk.Label(self.WFrame1, text="改訂図ファイル選択:")
        self.outdir_dialogue_label = ttk.Label(self.WFrame1, text="出力先フォルダ選択:")
        self.outext_label = ttk.Label(self.WFrame1, text="出力形式:")
        self.old_dialogue_label.grid(row=0, column=0, sticky='E')
        self.new_dialogue_label.grid(row=1, column=0, sticky='E')
        self.outdir_dialogue_label.grid(row=2, column=0, sticky='E')
        self.outext_label.grid(row=3, column=0, sticky='E')

        # Create Entry for Frame1
        self.old_entry = ttk.Entry(self.WFrame1, width=30)
        self.old_entry.grid(row=0, column=1, columnspan=2, sticky='EW')
        self.new_entry = ttk.Entry(self.WFrame1, width=30)
        self.new_entry.grid(row=1, column=1, columnspan=2, sticky='EW')
        self.outdir_entry = ttk.Entry(self.WFrame1, width=30)
        self.outdir_entry.insert(0, self.settings["output_dir"])
        self.outdir_entry.grid(row=2, column=1, columnspan=2, sticky='EW')

        self.old_entry.drop_target_register(tkdnd.DND_FILES)
        self.old_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_files, focus_entry=self.old_entry))
        self.new_entry.drop_target_register(tkdnd.DND_FILES)
        self.new_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_files, focus_entry=self.new_entry))
        self.outdir_entry.drop_target_register(tkdnd.DND_FILES)
        self.outdir_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_folder, focus_entry=self.outdir_entry))

        # Create Buttons for Frame1
        self.old_dialogue_button = ttk.Button(self.WFrame1, text="参照", command=self.old_entry_dialogue)
        self.new_dialogue_button = ttk.Button(self.WFrame1, text="参照", command=self.new_entry_dialogue)
        self.outdir_dialogue_button = ttk.Button(self.WFrame1, text="参照", command=self.outdir_entry_dialogue)
        self.old_clear_button = ttk.Button(self.WFrame1, text="クリア", command=lambda: self.old_entry.delete(0, tk.END))
        self.new_clear_button = ttk.Button(self.WFrame1, text="クリア", command=lambda: self.new_entry.delete(0, tk.END))
        self.outdir_clear_button = ttk.Button(self.WFrame1, text="クリア", command=lambda: self.outdir_entry.delete(0, tk.END))
        self.run_button = ttk.Button(self.WFrame1, text="実行", command=self.start_thread_main)
        self.stop_button = ttk.Button(self.WFrame1, text="中断", command=self.stop_program)
        self.stop_button.state(["disabled"]) #Disable the button.
        self.old_dialogue_button.grid(row=0, column=3)
        self.new_dialogue_button.grid(row=1, column=3)
        self.outdir_dialogue_button.grid(row=2, column=3)
        self.old_clear_button.grid(row=0, column=4)
        self.new_clear_button.grid(row=1, column=4)
        self.outdir_clear_button.grid(row=2, column=4)
        self.run_button.grid(row=4, column=1)
        self.stop_button.grid(row=4, column=2)

        # Create Check Button
        self.outext1 = tk.StringVar()
        self.outext2 = tk.StringVar()
        self.outext1.set(self.settings["outext1"])
        self.outext2.set(self.settings["outext2"])
        self.check_tiff = ttk.Checkbutton(self.WFrame1, text="tiff", variable=self.outext1, onvalue="tiff_on", offvalue="tiff_off")
        self.check_pdf = ttk.Checkbutton(self.WFrame1, text="pdf", variable=self.outext2, onvalue="pdf_on", offvalue="pdf_off")
        self.check_tiff.grid(row=3, column=1)
        self.check_pdf.grid(row=3, column=2)

        #--------------- Frame 2 (Progress Window) ---------------#
        # Create Frame2
        self.WFrame2 = ttk.Frame(self.master, borderwidth=3, relief="sunken", style='WFrame2.TFrame')
        self.WFrame2.grid(row=1, column=0, padx=10, pady=5, sticky='NSEW')
        self.WFrame2.grid_rowconfigure(0, weight=1)
        self.WFrame2.grid_columnconfigure(0, weight=1)

        # Set ScrolledText for Frame2
        self.Progress_Window = tk.Text(self.WFrame2, wrap=tk.NONE, fg="white", bg="black")
        self.Progress_Window.grid(row=0, column=0, sticky='NSEW')
        self.scrollbar_y = ttk.Scrollbar(self.WFrame2, orient=tk.VERTICAL, command=self.Progress_Window.yview)
        self.scrollbar_x = ttk.Scrollbar(self.WFrame2, orient=tk.HORIZONTAL, command=self.Progress_Window.xview)
        self.Progress_Window['yscrollcommand'] = self.scrollbar_y.set
        self.Progress_Window['xscrollcommand'] = self.scrollbar_x.set
        self.scrollbar_y.grid(row=0, column=1, sticky='NS')
        self.scrollbar_x.grid(row=1, column=0, sticky='EW')
        self.Progress_Window.insert(tk.END, "ファイルと出力先を選択し、「実行」をクリックしてください。")
        self.Progress_Window.configure(state="disable")

    #--------------- Functions for Widgets ---------------#
    def drop_files(self, event, focus_entry):
        # event.widget.focus_force()
        files = focus_entry.tk.splitlist(event.data)
        l_files = []
        for i_files in range(len(files)):
            if os.path.isfile(files[i_files]):
                l_files.append(files[i_files].replace("/", os.sep))
        focus_entry.delete(0, tk.END)
        focus_entry.insert(0, ','.join(l_files))

    def drop_folder(self, event, focus_entry):
        # event.widget.focus_force()
        folder = focus_entry.tk.splitlist(event.data)
        l_folders = []
        for i_folders in range(len(folder)):
            if os.path.isdir(folder[i_folders]):
                l_folders.append(folder[i_folders].replace("/", os.sep))
        focus_entry.delete(0, tk.END)
        focus_entry.insert(0, l_folders[0])

    def old_entry_dialogue(self):
        #self.init_dir = os.path.dirname(os.path.abspath(__file__)) #初期位置はexeファイルの階層
        init_dir = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH") + "\\Documents" #初期位置をマイドキュメントに設定(Windows Path)
        typ = [("すべての対応ファイル", ("*.tif", "*.tiff", "*.pdf")),
                    ("tiffファイル", ("*.tif", "*.tiff")),
                    ("pdfファイル", "*.pdf")]
        fname1 = filedialog.askopenfilenames(filetypes = typ, initialdir = init_dir, title="旧図ファイル選択（複数選択可）")
        l_fname1 = []
        for i_fname1 in range(len(fname1)): l_fname1.append(fname1[i_fname1].replace("/", os.sep))
        if fname1:
            self.old_entry.delete(0, tk.END)
            self.old_entry.insert(0, ','.join(l_fname1))
        #self.fname1 = tuple(self.old_entry.get().split(',')) #本文に入れた

    def new_entry_dialogue(self):
        typ = [("すべての対応ファイル", ("*.tif", "*.tiff", "*.pdf")),
                    ("tiffファイル", ("*.tif", "*.tiff")),
                    ("pdfファイル", "*.pdf")]
        fname2 = filedialog.askopenfilenames(filetypes = typ, initialdir = "", title="改訂図ファイル選択（複数選択可）")
        l_fname2 = []
        for i_fname2 in range(len(fname2)): l_fname2.append(fname2[i_fname2].replace("/", os.sep))
        if fname2:
            self.new_entry.delete(0, tk.END)
            self.new_entry.insert(0, ','.join(l_fname2))
        #self.fname2 = tuple(self.new_entry.get().split(',')) #本文に入れた

    def outdir_entry_dialogue(self):
        output_dir = filedialog.askdirectory(initialdir="", title="出力先フォルダ選択")
        output_dir = output_dir.replace("/", os.sep)
        if output_dir:
            self.outdir_entry.delete(0, tk.END)
            self.outdir_entry.insert(0, output_dir)
        #self.output_dir = self.outdir_entry.get() #本文に入れた

    def clear_all(self):
        self.old_entry.delete(0, tk.END)
        self.new_entry.delete(0, tk.END)
        self.outdir_entry.delete(0, tk.END)

    def init_settings(self, setting_file_path):
        # Make initial setting file
        if not os.path.exists(os.path.dirname(setting_file_path)):
            os.makedirs(os.path.dirname(setting_file_path))
        if not os.path.exists(setting_file_path):
            setting_data = {
                "output_dir": "",
                "outext1": "tiff_on",
                "outext2": "pdf_on"
            }
            with open(setting_file_path, "w") as _file:
                json.dump(setting_data, _file)
        with open(setting_file_path, "r") as _file:
            records = json.load(_file)
        return records

    def record_settings(self, setting_file_path):
        setting_data = {
            "output_dir": self.outdir_entry.get(),
            "outext1": self.outext1.get(),
            "outext2": self.outext2.get()
        }
        with open(setting_file_path, "w") as _file:
            json.dump(setting_data, _file)

    def show_how2use(self):
        self.how2use_window = tk.Toplevel(self.master)
        self.how2use_window.title("使い方")
        self.how2use_window.iconbitmap(self.icon_file_path) #Works only on Windows OS
        self.how2use_window.grid_rowconfigure(0, weight=1)
        self.how2use_window.grid_rowconfigure(1, weight=0)
        self.how2use_window.grid_rowconfigure(2, weight=0)
        self.how2use_window.grid_rowconfigure(3, weight=0)
        self.how2use_window.grid_columnconfigure(0, weight=1)
        self.how2use_window.grid_columnconfigure(1, weight=1)
        self.how2use_window.grid_columnconfigure(2, weight=1)
        self.img = [\
            Image.open("./imgs/How2Use-1.png"),\
            Image.open("./imgs/How2Use-2.png"),\
            Image.open("./imgs/How2Use-3.png"),\
            Image.open("./imgs/How2Use-4.png"),\
            Image.open("./imgs/How2Use-5.png"),\
            Image.open("./imgs/How2Use-6.png"),\
            Image.open("./imgs/How2Use-7.png"),\
            Image.open("./imgs/How2Use-8.png"),\
            ]
        self.copy_of_image = []
        self.how2_img = []
        for i_cp in range(len(self.img)):
            self.copy_of_image.append(self.img[i_cp].copy())
            self.how2_img.append(ImageTk.PhotoImage(self.img[i_cp]))
        im_width, im_height = self.img[0].size
        self.aspect = im_width/float(im_height)
        self.how2use_window.geometry(f'{int(im_width*0.75)}x{int(im_height*0.75)+46}') #ボタン・セパレータ・ページ進みの行の高さが46みたい
        self.how2use_window.minsize(f'{int(im_width*0.25)}',f'{int(im_height*0.25)+46}')

        self.img_label = ttk.Label(self.how2use_window, image=self.how2_img[0], anchor='center', background='white')
        self.img_label.bind('<Configure>', functools.partial(self.resize_image, image_number=0))
        self.button_back = ttk.Button(self.how2use_window, text = "<<", command=self.back, state = tk.DISABLED)
        self.button_exit = ttk.Button(self.how2use_window, text = "閉じる", command=self.how2use_window.destroy)
        self.button_forward = ttk.Button(self.how2use_window, text = ">>", command=lambda: self.forward(2))
        self.separator = ttk.Separator(self.how2use_window, orient=tk.HORIZONTAL)
        self.status = ttk.Label(self.how2use_window, text="ページ 1 / " + str(len(self.how2_img)), anchor='e')

        self.img_label.grid(row=0, column=0, columnspan=3, sticky='NSEW')
        self.button_back.grid(row=1, column=0)
        self.button_exit.grid(row=1, column=1)
        self.button_forward.grid(row=1, column=2)
        self.separator.grid(row=2, column=0, columnspan=3, sticky='EW')
        self.status.grid(row=3, column=0, columnspan=3, sticky='EW')

    def forward(self, image_number):
        self.image_number = image_number

        self.img_label.grid_forget()
        self.img_label = ttk.Label(self.how2use_window, image=self.how2_img[self.image_number-1], anchor='center', background='white')
        self.img_label.bind('<Configure>', functools.partial(self.resize_image, image_number=self.image_number-1))
        self.button_forward = ttk.Button(self.how2use_window, text=">>", command=lambda: self.forward(self.image_number+1))
        self.button_back = ttk.Button(self.how2use_window, text="<<", command=lambda: self.back(self.image_number-1))
        if self.image_number == len(self.how2_img):
            self.button_forward = ttk.Button(self.how2use_window, text =">>", state=tk.DISABLED)
        self.separator = ttk.Separator(self.how2use_window, orient=tk.HORIZONTAL)
        self.status = ttk.Label(self.how2use_window,\
             text="ページ " + str(self.image_number) + " / " + str(len(self.how2_img)), anchor='e')

        self.img_label.grid(row=0, column=0, columnspan=3, sticky='NSEW')
        self.button_back.grid(row=1, column=0)
        self.button_forward.grid(row=1, column=2)
        self.separator.grid(row=2, column=0, columnspan=3, sticky='EW')
        self.status.grid(row=3, column=0, columnspan=3, sticky='EW')

    def back(self, image_number):
        self.image_number = image_number

        self.img_label.grid_forget()
        self.img_label = ttk.Label(self.how2use_window, image=self.how2_img[self.image_number-1], anchor='center', background='white')
        self.img_label.bind('<Configure>', functools.partial(self.resize_image, image_number=self.image_number-1))
        self.button_forward = ttk.Button(self.how2use_window, text=">>", command=lambda: self.forward(self.image_number+1))
        self.button_back = ttk.Button(self.how2use_window, text="<<", command=lambda: self.back(self.image_number-1))
        if self.image_number == 1:
            self.button_back = ttk.Button(self.how2use_window, text="<<", state=tk.DISABLED)
        self.separator = ttk.Separator(self.how2use_window, orient=tk.HORIZONTAL)
        self.status = ttk.Label(self.how2use_window,\
             text="ページ " + str(self.image_number) + " / " + str(len(self.how2_img)), anchor='e')

        self.img_label.grid(row=0, column=0, columnspan=3, sticky='NSEW')
        self.button_back.grid(row=1, column=0)
        self.button_forward.grid(row=1, column=2)
        self.separator.grid(row=2, column=0, columnspan=3, sticky='EW')
        self.status.grid(row=3, column=0, columnspan=3, sticky='EW')

    def resize_image(self, event, image_number):
        new_height = event.height
        new_width = int(new_height*self.aspect)
        if new_width > event.width:
            new_width = event.width
            new_height = int(new_width/self.aspect)
        self.img[image_number] = self.copy_of_image[image_number].resize((new_width, new_height))
        self.how2_img[image_number] = ImageTk.PhotoImage(self.img[image_number])
        self.img_label.config(image = self.how2_img[image_number])
        self.img_label.image = self.how2_img[image_number] #avoid garbage collection

    def show_about(self):
        self.about_window = tk.Toplevel(self.master)
        self.about_window.title("このアプリケーションについて")
        self.about_window.iconbitmap(self.icon_file_path) #Works only on Windows OS
        self.about_window.resizable(tk.FALSE,tk.FALSE)
        # self.about_window.geometry("500x300")
        self.about_window.grid_columnconfigure(0, weight=1)
        self.about_window.grid_columnconfigure(1, weight=1)
        # self.about_window.grid_rowconfigure(0, weight=0)
        # self.about_window.grid_rowconfigure(1, weight=0)
        self.original_icon_img = Image.open(self.icon_file_path)
        self.original_icon_img = self.original_icon_img.resize((100, 100), Image.ANTIALIAS)
        self.tk_icon_img = ImageTk.PhotoImage(self.original_icon_img)

        self.icon_label = ttk.Label(self.about_window, image=self.tk_icon_img, anchor='e')
        self.title_label = ttk.Label(self.about_window, text=__appname__, font=("", 50, "italic"), anchor='w')
        self.separator = ttk.Separator(self.about_window, orient=tk.HORIZONTAL)
        self.date_label = ttk.Label(self.about_window, text="最終更新日: ", anchor='e')
        self.date_label2 = ttk.Label(self.about_window, text=__date__, anchor='w')
        self.ver_label = ttk.Label(self.about_window, text="アプリケーションバージョン: ", anchor='e')
        self.ver_label2 = ttk.Label(self.about_window, text=str(__version__), anchor='w')
        self.pyver_label = ttk.Label(self.about_window, text="Pythonバージョン: ", anchor='e')
        self.pyver_label2 = ttk.Label(self.about_window, text=str(__deprecated__.split(", ")[1]), anchor='w')
        self.popver_label = ttk.Label(self.about_window, text="Popplerバージョン: ", anchor='e')
        self.popver_label2 = ttk.Label(self.about_window, text=str(__deprecated__.split(", ")[2]), anchor='w')
        self.osver_label = ttk.Label(self.about_window, text="動作環境: ", anchor='e')
        self.osver_label2 = ttk.Label(self.about_window, text=str(__deprecated__.split(", ")[0]), anchor='w')
        self.author_label = ttk.Label(self.about_window, text="作者:\n", anchor='e')
        self.author_label2 = ttk.Label(self.about_window, text="\n".join(__author__), anchor='w')
        self.license_label = ttk.Label(self.about_window, text="ライセンス: ", anchor='e')
        self.license_label2 = ttk.Label(self.about_window, text=__license__, anchor='w')
        self.close_about_button = ttk.Button(self.about_window, text="閉じる", command=self.about_window.destroy)
        self.separator = ttk.Separator(self.about_window, orient=tk.HORIZONTAL)
        self.copyright_label = ttk.Label(self.about_window, text=__copyright__)

        self.icon_label.grid(row=0, column=0, padx=20, pady=10, sticky="NSEW")
        self.title_label.grid(row=0, column=1, padx=2, sticky="NSEW")
        self.separator.grid(row=1, column=0, pady=3, columnspan=2, sticky="NSEW")
        self.date_label.grid(row=2, column=0, pady=2, sticky="NSEW")
        self.date_label2.grid(row=2, column=1, padx=5, pady=2, sticky="NSEW")
        self.ver_label.grid(row=3, column=0, pady=2, sticky="NSEW")
        self.ver_label2.grid(row=3, column=1, padx=5, pady=2, sticky="NSEW")
        self.pyver_label.grid(row=4, column=0, pady=2, sticky="NSEW")
        self.pyver_label2.grid(row=4, column=1, padx=5, pady=2, sticky="NSEW")
        self.popver_label.grid(row=5, column=0, pady=2, sticky="NSEW")
        self.popver_label2.grid(row=5, column=1, padx=5, pady=2, sticky="NSEW")
        self.osver_label.grid(row=6, column=0, pady=2, sticky="NSEW")
        self.osver_label2.grid(row=6, column=1, padx=5, pady=2, sticky="NSEW")
        self.author_label.grid(row=7, column=0, pady=2, sticky="NSEW")
        self.author_label2.grid(row=7, column=1, padx=5, pady=2, sticky="NSEW")
        self.license_label.grid(row=8, column=0, pady=2, sticky="NSEW")
        self.license_label2.grid(row=8, column=1, padx=5, pady=2, sticky="NSEW")
        self.close_about_button.grid(row=9, column=0, pady=15, columnspan=2)
        self.separator.grid(row=10, column=0, columnspan=2, sticky="NSEW")
        self.copyright_label.grid(row=11, column=0, pady=5, columnspan=2)

    def start_thread_main(self):
        self.run_button.state(["disabled"]) #Disable run button.
        self.stop_button.state(["!disabled"]) #Enable stop button.
        self.file_menu.entryconfig("実行", state="disabled") #Disable run menu.
        self.file_menu.entryconfig("中断", state="normal") #Enable stop menu.
        thread_main = threading.Thread(target=self.run_program)
        self.started.set()
        thread_main.start()

    def textmessageinit(self):
        self.Progress_Window.configure(state="normal") #Enable scrolled text box.
        self.Progress_Window.delete(1.0, tk.END) #Clear text box.
        self.Progress_Window.configure(state="disable") #Disable scrolled text box.

    def textmessage(self, scrolltxt):
        self.Progress_Window.configure(state="normal") #Enable scrolled text box.
        self.Progress_Window.insert(tk.END, scrolltxt) #Adding text.
        self.Progress_Window.insert(tk.END, "\n")
        self.Progress_Window.yview(tk.END) #Autoscroll
        self.Progress_Window.configure(state="disable") #Disable scrolled text box.

    def stop_program(self):
        self.started.clear()
        self.stop_button.state(["disabled"]) #Disable stop button.
        self.file_menu.entryconfig("中断", state="disabled") #Disable stop menu.
        scrolltxt = "処理を中断しています..."
        self.textmessage(scrolltxt)

    def regular_error(self, str_msg):
        messagebox.showerror("エラーメッセージ", str_msg)
        self.run_button.state(["!disabled"]) #Enable run button.
        self.stop_button.state(["disabled"]) #Disable stop button.
        self.file_menu.entryconfig("実行", state="normal") #Enable run menu.
        self.file_menu.entryconfig("中断", state="disabled") #Disable stop menu.
        scrolltxt = "ファイルと出力先を選択し、「実行」をクリックしてください。"
        self.textmessage(scrolltxt)

    def opened_file_check(self, checking_file):
        if os.path.isfile(checking_file):
            while True:
                try:
                    os.rename(checking_file, checking_file)
                except:
                    response = messagebox.askretrycancel("エラーメッセージ", "保存先へのアクセスが拒否されました。\n"\
                        "保存先で同一名のファイルが使用中である可能性があります。\n"\
                            "ファイルが開かれていないことを確認ください。")
                    if response == False:
                        self.stop_program()
                        break
                else: break

###################################### ここから画像処理系メインプログラム #############################################
    def saveTiffStack(self, save_path, imgs_list, dpi_value):
        """Tiffファイルの保存
        :param save_path: 画像を保存するパス
        :param imgs_list: 保存したい画像のlist Ex)imgs_list=(img1, img2, img3, ...)=>imgs_list[1]=img2
        :return:
        参考(https://qiita.com/machisuke/items/0ca8a09d79bd5eba3cf3)
        """
        stack = []
        for img in imgs_list:
            stack.append(img)
        stack[0].save(save_path, compression="tiff_deflate",
                      save_all=True, append_images=stack[1:], dpi=dpi_value)

    def savePDFStack(self, save_path, imgs):
        """マルチTiffファイルを複数ページのPDFファイルに変換して保存
        :param save_path: PDFを保存するパス
        :param imgs: マルチTiffファイルフルパス
        :return:
        参考(https://gitlab.mister-muffin.de/josch/img2pdf/issues/50)
        """
        images = []
        return_data = io.BytesIO()
        tiffstack = Image.open(imgs)

        for i in range(tiffstack.n_frames):
            tiffstack.seek(i)
            tiffstack.save(return_data, 'TIFF')
            images.append(return_data.getvalue())

        with open(save_path, 'wb') as tmp:
            tmp.write(img2pdf.convert(images))
            tmp.close()

        tiffstack.close()

    def run_program(self):
        try:
            self.record_settings(self.setting_file_path)
            self.textmessageinit()
            ######################
            #Poppler読み込み
            #最新版のインストール(https://poppler.freedesktop.org/)
            ######################
            self.poppler_path = os.path.join(os.getcwd(), "poppler-0.68.0", "bin")#popplerをプログラムと同じディレクトリにインストールさせる必要がある。
            os.environ["PATH"] += os.pathsep + self.poppler_path

            ######################
            #ファイル名読み込み
            ######################
            self.fname1 = tuple(self.old_entry.get().split(','))
            self.fname2 = tuple(self.new_entry.get().split(','))
            self.output_dir = self.outdir_entry.get()

            ######################
            #エラーチェック
            ######################
            self.file_exts = [str.lower(os.path.splitext(self.ext)[1]) for self.ext in self.fname1+self.fname2]
            #エントリーボックスが空
            if self.fname1 == ('',) or self.fname2 == ('',) or len(self.output_dir) == 0:
                self.regular_error("ファイルか保存先が指定されていません。")
                return
            #読み込みファイル数エラー
            elif len(self.fname1) != len(self.fname2):
                self.regular_error("比較対象のファイル数が異なります。")
                return
            #非対応拡張子エラー(tiffかPDFファイル以外を選択した場合)
            elif not self.file_exts[0].endswith(".tif") and not self.file_exts[0].endswith(".tiff")\
                and not self.file_exts[0].endswith(".pdf"):
                self.regular_error("tiff形式かpdf形式のファイルを選択してください。")
                return
            #拡張子混在エラー(.tiffと.tifの混在はOKにしてる)
            elif len(set(self.file_exts)) != 1 and self.file_exts[0][0:4] != self.file_exts[1][0:4]:
                self.regular_error("異なる形式の拡張子が混在しています。\n"\
                    "同じ形式のファイルを選択してください。")
                return
            #tiffもpdfもどちらもチェックボックスがOFFの時
            elif self.outext1.get() == "tiff_off" and self.outext2.get() == "pdf_off":
                self.regular_error("出力形式が選択されていません。\n"\
                    "tiffまたはpdfまたは両方のチェックボックスにチェックを入れてください。")
                return

            ######################
            #比較⇒変換⇒出力
            ######################
            for j in range(len(self.fname1)):
                if self.started.is_set() == True:
                    scrolltxt = "ファイルの読み込み中..."
                    self.textmessage(scrolltxt)

                    #画像バイナリデータの読み込み
                    if self.file_exts[0].endswith(".tif") or self.file_exts[0].endswith(".tiff"):
                        self.drw1 = Image.open(self.fname1[j])
                        self.drw2 = Image.open(self.fname2[j])
                        self.itr1 = ImageSequence.Iterator(self.drw1)
                        self.itr2 = ImageSequence.Iterator(self.drw2)
                        num_frames = self.drw1.n_frames
                        self.dpi_value = self.drw1.info['dpi']
                    elif self.file_exts[0].endswith(".pdf"):
                        self.drw1 = pdf2image_personaledit.convert_from_path(self.fname1[j], dpi=300)
                        self.drw2 = pdf2image_personaledit.convert_from_path(self.fname2[j], dpi=300)
                        num_frames = len(self.drw1)
                        self.dpi_value = (300, 300)
                        #pdf2image上限エラー
                        if num_frames > 100:
                            self.regular_error("PDFファイルは100ページまでしか読み込めません。")
                            return

                    #配列の初期化
                    self.drw_out_4dim_pages = []
                    if self.started.is_set() == True:
                        #画像比較
                        for page in range(0, num_frames):
                            scrolltxt = str(j+1)+"/"+str(len(self.fname1))+"ファイルの" +\
                                str(page+1)+"/"+str(num_frames)+"ページ目を処理中..."
                            self.textmessage(scrolltxt)

                            #画像のグレースケール化＋出力用変数の準備
                            if self.file_exts[0].endswith(".tif") or self.file_exts[0].endswith(".tiff"):
                                self.drw1_gray = self.itr1[page].convert("L")
                                self.drw2_gray = self.itr2[page].convert("L")
                            elif self.file_exts[0].endswith(".pdf"):
                                self.drw1_gray = self.drw1[page].convert("L")
                                self.drw2_gray = self.drw2[page].convert("L")
                            self.drw_out = self.drw2_gray.convert("RGB")

                            if self.drw1_gray.size != self.drw2_gray.size:
                                self.regular_error("同じサイズの画像を選択してください")
                                return

                            #差分を色塗りするためのマスクの作成
                            self.mask_red = ImageChops.subtract(self.drw1_gray, self.drw2_gray)
                            self.mask_blue = ImageChops.subtract(self.drw2_gray, self.drw1_gray)

                            #マスク使用して差分箇所に色塗り
                            self.drw_out.paste(Image.new("RGB", self.drw_out.size, "red"), mask=self.mask_red)
                            self.drw_out.paste(Image.new("RGB", self.drw_out.size, "blue"), mask=self.mask_blue)

                            #出力画像データに、「前データ => 後データ」のテキスト挿入 #Works only on Windows OS. Mac OS requires full path.
                            self.fnt = ImageFont.truetype(
                                "C:\Windows\Fonts\msgothic.ttc", int(self.drw_out.size[1]/60))
                            self.drw_text = ImageDraw.Draw(self.drw_out)
                            self.txt = os.path.splitext(os.path.basename(self.fname1[j]))[0]+' => '\
                                + os.path.splitext(os.path.basename(self.fname2[j]))[0]
                            self.drw_text.text((50, 50), self.txt, fill="red", font=self.fnt)
                            self.txt = os.path.splitext(os.path.basename(self.fname1[j]))[0]+' => '
                            self.drw_text.text((50, 50), self.txt, fill="black", font=self.fnt)
                            self.txt = os.path.splitext(os.path.basename(self.fname1[j]))[0]
                            self.drw_text.text((50, 50), self.txt, fill="blue", font=self.fnt)

                            self.drw_out_4dim_pages.append(self.drw_out)

                        if self.started.is_set() == True:
                            #出力先に保存
                            scrolltxt = "出力先にファイルを保存しています..."
                            self.textmessage(scrolltxt)
                            self.tiff_name = os.path.join(self.output_dir, "Output_"
                                                                + os.path.splitext(os.path.basename(self.fname2[j]))[0] + ".tif")
                            self.opened_file_check(self.tiff_name) #保存先で同一名ファイルが開かれていないかチェックする
                            if self.started.is_set() == True:
                                self.saveTiffStack(self.tiff_name, self.drw_out_4dim_pages, self.dpi_value)
                            #pdfにチェックがあればPDFに変換する
                            if self.outext2.get() == "pdf_on":
                                self.save_path = os.path.join(self.output_dir, "Output_"
                                                        + os.path.splitext(os.path.basename(self.fname2[j]))[0] + ".pdf")
                                self.opened_file_check(self.save_path) #保存先で同一名ファイルが開かれていないかチェックする
                                if self.started.is_set() == True:
                                    self.savePDFStack(self.save_path, self.tiff_name)

                            if self.outext1.get() == "tiff_off":
                                self.opened_file_check(self.tiff_name) #保存先で同一名ファイルが開かれていないかチェックする
                                os.remove(self.tiff_name)

                            if self.started.is_set() == True:
                                scrolltxt = "保存しました。\n"
                                self.textmessage(scrolltxt)

            if self.started.is_set() == True:
                response = messagebox.askquestion("確認", "処理が完了しました。\n出力フォルダを開きますか？")
                if response == "yes":
                    subprocess.Popen(["explorer", self.output_dir])
                scrolltxt = "\n正常に処理を完了しました。\n"
                self.textmessage(scrolltxt)
            else:
                response = messagebox.askquestion("確認", "処理が中断されました。\n出力フォルダを開きますか？")
                if response == "yes":
                    subprocess.Popen(["explorer", self.output_dir])
                scrolltxt = "\n途中で処理を中断しました。\n"
                self.textmessage(scrolltxt)

            self.run_button.state(["!disabled"]) #Enable run button.
            self.stop_button.state(["disabled"]) #Disable stop button.
            self.file_menu.entryconfig("実行", state="normal") #Enable run menu.
            self.file_menu.entryconfig("中断", state="disabled") #Disable stop menu.

            scrolltxt = "続けて実行する場合は再度ファイルと出力先を選択し、「実行」をクリックしてください。"
            self.textmessage(scrolltxt)

        except:
            import traceback
            with open(os.path.join(self.output_dir, "ERR_DETECT_IMGCOMP.txt"), "w") as error_output:
                traceback.print_exc(file=error_output)
            self.regular_error("予期せぬエラーが発生しました。\nプログラムを終了します。")
            self.master.quit()

def main():
    root = tkdnd.TkinterDnD.Tk()
    app = Application(master=root)
    root.mainloop()


if __name__ == "__main__":
    main()
