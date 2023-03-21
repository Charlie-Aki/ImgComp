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

class Application(tkdnd.TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        aida_func=AidaCore()
        self.icon_image=aida_func.get_abs_path("./imgs/ImgComp_256x256.ico")
        self.title(__appname__+"Ver."+__version__)
        self.iconbitmap(self.icon_image) # Windows用アイコン設定
        self.geometry('500x400')
        self.minsize(430, 200)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        # self.setting_file_path = os.environ["LOCALAPPDATA"]+r"\ImgComp\図面比較\settings.json" #Win版リリース用
        setting_file_path = "./settings.json".replace("/", os.sep) #テスト用
        self.settings = self.init_settings(setting_file_path)
        self.create_widgets()

    def create_widgets(self):
        progress_window_frame=ProgressWindowFrame(master=self)
        main_frame=MainFrame(master=self, ctrl_frame=progress_window_frame)
        menubar=Menubar(master=self, ctrl_frame=main_frame)

    def init_settings(self, setting_file_path):
        """
        初期設定ファイル作成
        """
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

class Menubar(tk.Menu):
    def __init__(self, master, ctrl_frame):
        super().__init__(master)
        self.master=master
        self.master.config(menu=self)
        self.ctrl_frame=ctrl_frame # main_frame
        self.create_file_menu()
        self.create_edit_menu()
        self.create_help_menu()

    def create_file_menu(self):
        file_menu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="旧図ファイル選択", command=do_nothing)
        file_menu.add_command(label="改訂図ファイル選択", command=do_nothing)
        file_menu.add_command(label="出力先フォルダ選択", command=do_nothing)
        file_menu.add_separator()
        file_menu.add_command(label="実行", command=do_nothing)
        file_menu.add_command(label="中断", command=do_nothing)
        file_menu.entryconfig("中断", state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.master.quit)

    def create_edit_menu(self):
        edit_menu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="切り取り", accelerator="Ctrl+X", command=lambda: self.master.focus_get().event_generate("<<Cut>>"))
        edit_menu.add_command(label="コピー", accelerator="Ctrl+C", command=lambda: self.master.focus_get().event_generate("<<Copy>>"))
        edit_menu.add_command(label="貼り付け", accelerator="Ctrl+V", command=lambda: self.master.focus_get().event_generate("<<Paste>>"))
        edit_menu.add_command(label="全選択", accelerator="Ctrl+A", command=lambda: self.master.focus_get().event_generate("<<SelectAll>>"))
        edit_menu.add_command(label="選択項目をクリア", command=self.delete_focus)
        edit_menu.add_command(label="全項目クリア", command=self.clear_all)

    def delete_focus(self):
        focused_widget=self.master.focus_get()
        focused_widget.delete(0, tk.END)

    def clear_all(self):
        self.ctrl_frame.clear_all()

    def create_help_menu(self):
        help_menu = tk.Menu(self, tearoff=False)
        self.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方", command=self.show_how2use_window)
        help_menu.add_command(label="バージョン情報", command=self.show_about_window)

    def show_how2use_window(self):
        how2use_window=How2UseWindow(master=self.master)

    def show_about_window(self):
        about_window=AboutWindow(master=self.master)

class MainFrame(ttk.Frame):
    def __init__(self, master, ctrl_frame):
        super().__init__(master)
        self.master=master
        self.settings=self.master.settings
        self.ctrl_frame=ctrl_frame # progress_frame
        # s=self.specify_style()
        self.create_widgets()

    # def specify_style(self):
    #     s=ttk.Style()
    #     s.theme_use('vista')
    #     s.configure('main_frame.theme', background='red')
    #     return s

    def create_widgets(self):
        self.grid(row=0, column=0, padx=10, pady=5, sticky='EW')
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Create Labels for Main Frame
        old_dialogue_label = ttk.Label(self, text="旧図ファイル選択:")
        new_dialogue_label = ttk.Label(self, text="改訂図ファイル選択:")
        outdir_dialogue_label = ttk.Label(self, text="出力先フォルダ選択:")
        outext_label = ttk.Label(self, text="出力形式:")
        old_dialogue_label.grid(row=0, column=0, sticky='E')
        new_dialogue_label.grid(row=1, column=0, sticky='E')
        outdir_dialogue_label.grid(row=2, column=0, sticky='E')
        outext_label.grid(row=3, column=0, sticky='E')

        # Create Entry for Main Frame
        self.old_entry = ttk.Entry(self, width=30)
        self.old_entry.grid(row=0, column=1, columnspan=2, sticky='EW')
        self.new_entry = ttk.Entry(self, width=30)
        self.new_entry.grid(row=1, column=1, columnspan=2, sticky='EW')
        self.outdir_entry = ttk.Entry(self, width=30)
        self.outdir_entry.insert(0, self.settings["output_dir"])
        self.outdir_entry.grid(row=2, column=1, columnspan=2, sticky='EW')

        self.old_entry.drop_target_register(tkdnd.DND_FILES)
        self.old_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_files, focus_entry=self.old_entry))
        self.new_entry.drop_target_register(tkdnd.DND_FILES)
        self.new_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_files, focus_entry=self.new_entry))
        self.outdir_entry.drop_target_register(tkdnd.DND_FILES)
        self.outdir_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_folder, focus_entry=self.outdir_entry))

        # Create Buttons for Main Frame
        old_dialogue_button = ttk.Button(self, text="参照", command=self.old_entry_dialogue)
        new_dialogue_button = ttk.Button(self, text="参照", command=self.new_entry_dialogue)
        outdir_dialogue_button = ttk.Button(self, text="参照", command=self.outdir_entry_dialogue)
        old_clear_button = ttk.Button(self, text="クリア", command=lambda: self.old_entry.delete(0, tk.END))
        new_clear_button = ttk.Button(self, text="クリア", command=lambda: self.new_entry.delete(0, tk.END))
        outdir_clear_button = ttk.Button(self, text="クリア", command=lambda: self.outdir_entry.delete(0, tk.END))
        run_button = ttk.Button(self, text="実行", command=self.start_thread_main)
        stop_button = ttk.Button(self, text="中断", command=self.stop_program)
        stop_button.state(["disabled"]) #Disable the button.
        old_dialogue_button.grid(row=0, column=3)
        new_dialogue_button.grid(row=1, column=3)
        outdir_dialogue_button.grid(row=2, column=3)
        old_clear_button.grid(row=0, column=4)
        new_clear_button.grid(row=1, column=4)
        outdir_clear_button.grid(row=2, column=4)
        run_button.grid(row=4, column=1)
        stop_button.grid(row=4, column=2)

        # Create Check Button
        outext1 = tk.StringVar()
        outext2 = tk.StringVar()
        outext1.set(self.settings["outext1"])
        outext2.set(self.settings["outext2"])
        check_tiff = ttk.Checkbutton(self, text="tiff", variable=outext1, onvalue="tiff_on", offvalue="tiff_off")
        check_pdf = ttk.Checkbutton(self, text="pdf", variable=outext2, onvalue="pdf_on", offvalue="pdf_off")
        check_tiff.grid(row=3, column=1)
        check_pdf.grid(row=3, column=2)

    def drop_files(self, event, focus_entry):
        files = focus_entry.tk.splitlist(event.data)
        l_files = []
        for i_files in range(len(files)):
            if os.path.isfile(files[i_files]):
                l_files.append(files[i_files].replace("/", os.sep))
        focus_entry.delete(0, tk.END)
        focus_entry.insert(0, ','.join(l_files))

    def drop_folder(self, event, focus_entry):
        folder = focus_entry.tk.splitlist(event.data)
        l_folders = []
        for i_folders in range(len(folder)):
            if os.path.isdir(folder[i_folders]):
                l_folders.append(folder[i_folders].replace("/", os.sep))
        focus_entry.delete(0, tk.END)
        focus_entry.insert(0, l_folders[0])

    def old_entry_dialogue(self):
        #self.init_dir = os.path.dirname(os.path.abspath(__file__)) #初期位置はexeファイルの階層
        # 初期位置をマイドキュメントに設定(Windows Path)
        init_dir = os.getenv("HOMEDRIVE") + \
            os.getenv("HOMEPATH") + "\\Documents"
        typ = [("すべての対応ファイル", ("*.tif", "*.tiff", "*.pdf")),
               ("tiffファイル", ("*.tif", "*.tiff")),
               ("pdfファイル", "*.pdf")]
        file_name = filedialog.askopenfilenames(
            filetypes=typ, initialdir=init_dir, title="旧図ファイル選択（複数選択可）")
        l_file_name = []
        for i_file_name in range(len(file_name)):
            l_file_name.append(file_name[i_file_name].replace("/", os.sep))
        if file_name:
            self.old_entry.delete(0, tk.END)
            self.old_entry.insert(0, ','.join(l_file_name))
        #self.fname1 = tuple(self.self.old_entry.get().split(',')) #本文に入れた

    def new_entry_dialogue(self):
        typ = [("すべての対応ファイル", ("*.tif", "*.tiff", "*.pdf")),
               ("tiffファイル", ("*.tif", "*.tiff")),
               ("pdfファイル", "*.pdf")]
        file_name = filedialog.askopenfilenames(
            filetypes=typ, initialdir="", title="改訂図ファイル選択（複数選択可）")
        l_file_name = []
        for i_file_name in range(len(file_name)):
            l_file_name.append(file_name[i_file_name].replace("/", os.sep))
        if file_name:
            self.new_entry.delete(0, tk.END)
            self.new_entry.insert(0, ','.join(l_file_name))
        #self.fname2 = tuple(self.self.new_entry.get().split(',')) #本文に入れた

    def outdir_entry_dialogue(self):
        output_dir = filedialog.askdirectory(initialdir="", title="出力先フォルダ選択")
        output_dir = output_dir.replace("/", os.sep)
        if output_dir:
            self.outdir_entry.delete(0, tk.END)
            self.outdir_entry.insert(0, output_dir)
        #self.output_dir = self.self.outdir_entry.get() #本文に入れた

    def clear_all(self):
        self.old_entry.delete(0, tk.END)
        self.new_entry.delete(0, tk.END)
        self.outdir_entry.delete(0, tk.END)

    def record_settings(self, setting_file_path):
        # setting_data = {
        #     "output_dir": self.self.outdir_entry.get(),
        #     "outext1": self.outext1.get(),
        #     "outext2": self.outext2.get()
        # }
        # with open(setting_file_path, "w") as _file:
        #     json.dump(setting_data, _file)
        pass

    def start_thread_main(self):
        # self.run_button.state(["disabled"])  # Disable run button.
        # self.stop_button.state(["!disabled"])  # Enable stop button.
        # self.file_menu.entryconfig("実行", state="disabled")  # Disable run menu.
        # self.file_menu.entryconfig("中断", state="normal")  # Enable stop menu.
        # thread_main = threading.Thread(target=self.run_program)
        # self.started.set()
        # thread_main.start()
        pass

    def stop_program(self):
        # self.started.clear()
        # self.stop_button.state(["disabled"])  # Disable stop button.
        # # Disable stop menu.
        # self.file_menu.entryconfig("中断", state="disabled")
        # scrolltxt = "処理を中断しています..."
        # self.textmessage(scrolltxt)
        pass

    def regular_error(self, str_msg):
        # messagebox.showerror("エラーメッセージ", str_msg)
        # self.run_button.state(["!disabled"])  # Enable run button.
        # self.stop_button.state(["disabled"])  # Disable stop button.
        # self.file_menu.entryconfig("実行", state="normal")  # Enable run menu.
        # # Disable stop menu.
        # self.file_menu.entryconfig("中断", state="disabled")
        # scrolltxt = "ファイルと出力先を選択し、「実行」をクリックしてください。"
        # self.textmessage(scrolltxt)
        pass

    def run_program(self):
        pass

class ProgressWindowFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master=master
        # s=self.specify_style()
        self.create_widgets()

    # def specify_style(self):
    #     s=ttk.Style()
    #     s.theme_use('vista')
    #     s.configure('main_frame.theme', background='red')
    #     return s

    def create_widgets(self):
        self.grid(row=1, column=0, padx=10, pady=5, sticky='NSEW')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Set ScrolledText for Frame2
        self.progress_window = tk.Text(self, wrap=tk.NONE, fg="white", bg="black")
        self.progress_window.grid(row=0, column=0, sticky='NSEW')
        scrollbar_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.progress_window.yview)
        scrollbar_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.progress_window.xview)
        self.progress_window['yscrollcommand'] = scrollbar_y.set
        self.progress_window['xscrollcommand'] = scrollbar_x.set
        scrollbar_y.grid(row=0, column=1, sticky='NS')
        scrollbar_x.grid(row=1, column=0, sticky='EW')
        self.progress_window.insert(tk.END, "ファイルと出力先を選択し、「実行」をクリックしてください。")
        self.progress_window.configure(state="disable")

    def text_message_init(self):
        # Enable scrolled text box.
        self.progress_window.configure(state="normal")
        self.progress_window.delete(1.0, tk.END)  # Clear text box.
        # Disable scrolled text box.
        self.progress_window.configure(state="disable")

    def text_message(self, scroll_txt):
        # Enable scrolled text box.
        self.progress_window.configure(state="normal")
        self.progress_window.insert(tk.END, scroll_txt)  # Adding text.
        self.progress_window.insert(tk.END, "\n")
        self.progress_window.yview(tk.END)  # Autoscroll
        # Disable scrolled text box.
        self.progress_window.configure(state="disable")
        pass

class How2UseWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master=master
        self.title("使い方")
        self.iconbitmap(self.master.icon_image)  # Works only on Windows OS
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        aida_func=AidaCore()
        self.imgs = [
            Image.open(aida_func.get_abs_path("./imgs/How2Use-1.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-2.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-3.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-4.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-5.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-6.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-7.png")),
            Image.open(aida_func.get_abs_path("./imgs/How2Use-8.png")),
        ]
        self._im_width, self._im_height = self.imgs[0].size
        # ボタン・セパレータ・ページ進みの行の高さが46みたい
        self.geometry(f'{int(self._im_width*0.75)}x{int(self._im_height*0.75)+46}')
        self.minsize(f'{int(self._im_width*0.25)}', f'{int(self._im_height*0.25)+46}')
        self.create_widgets()

    def create_widgets(self):
        self.__imgs_copy=self.image_copy(self.imgs) #縮小してから拡大すると画質が荒くなっていくので元の画像を保持しておく。

        self.__how2_imgs = []
        for i_cp in range(len(self.imgs)):
            self.__how2_imgs.append(ImageTk.PhotoImage(self.imgs[i_cp]))

        self.__img_label = ttk.Label(self, image=self.__how2_imgs[0], anchor='center', background='white')
        self.__img_label.bind('<Configure>', functools.partial(self.resize_image, image_number=0))
        self.__button_back = ttk.Button(self, text="<<", command=self.back, state=tk.DISABLED)
        button_exit = ttk.Button(self, text="閉じる", command=self.destroy)
        self.__button_forward = ttk.Button(self, text=">>", command=lambda: self.forward(2))
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.__status = ttk.Label(self, text="ページ 1 / " + str(len(self.__how2_imgs)), anchor='e')

        self.__img_label.grid(row=0, column=0, columnspan=3, sticky='NSEW')
        self.__button_back.grid(row=1, column=0)
        button_exit.grid(row=1, column=1)
        self.__button_forward.grid(row=1, column=2)
        separator.grid(row=2, column=0, columnspan=3, sticky='EW')
        self.__status.grid(row=3, column=0, columnspan=3, sticky='EW')

    def image_copy(self, imgs):
        """
        pillowモジュールは何か変更を加えると元のデータが上書きされてしまうのでオリジナル画像のコピーを保持してから変更を加える。
        """
        imgs_copy=[]
        for i_cp in range(len(imgs)):
            imgs_copy.append(imgs[i_cp].copy())
        return imgs_copy

    def resize_image(self, event, image_number):

        aspect = self._im_width/float(self._im_height)
        new_height = event.height
        new_width = int(new_height*aspect)
        if new_width > event.width:
            new_width = event.width
            new_height = int(new_width/aspect)
        self.imgs[image_number] = self.__imgs_copy[image_number].resize((new_width, new_height))
        self.__how2_imgs[image_number] = ImageTk.PhotoImage(self.imgs[image_number])
        self.__img_label.config(image=self.__how2_imgs[image_number])
        self.__img_label.image = self.__how2_imgs[image_number] # リサイズ前の画像用のメモリ領域を確保し続けるので不要なメモリ分開放する。

    def forward(self, image_number):

        self.__img_label.grid_forget()
        self.__img_label = ttk.Label(self, image=self.__how2_imgs[image_number-1], anchor='center', background='white')
        self.__img_label.bind('<Configure>', functools.partial(self.resize_image,image_number=image_number-1))
        self.__button_forward = ttk.Button(self, text=">>", command=lambda: self.forward(image_number+1))
        self.__button_back = ttk.Button(self, text="<<", command=lambda: self.back(image_number-1))
        if image_number == len(self.__how2_imgs):
            self.__button_forward = ttk.Button(self, text=">>", state=tk.DISABLED)
        self.__status = ttk.Label(self, text="ページ " + str(image_number) + " / " + str(len(self.__how2_imgs)), anchor='e')

        self.__img_label.grid(row=0, column=0, columnspan=3, sticky='NSEW')
        self.__button_back.grid(row=1, column=0)
        self.__button_forward.grid(row=1, column=2)
        self.__status.grid(row=3, column=0, columnspan=3, sticky='EW')

    def back(self, image_number):

        self.__img_label.grid_forget()
        self.__img_label = ttk.Label(self, image=self.__how2_imgs[image_number-1], anchor='center', background='white')
        self.__img_label.bind('<Configure>', functools.partial(self.resize_image, image_number=image_number-1))
        self.__button_forward = ttk.Button(self, text=">>", command=lambda: self.forward(image_number+1))
        self.__button_back = ttk.Button(self, text="<<", command=lambda: self.back(image_number-1))
        if image_number == 1:
            self.__button_back = ttk.Button(self, text="<<", state=tk.DISABLED)
        self.__status = ttk.Label(self, text="ページ " + str(image_number) + " / " + str(len(self.__how2_imgs)), anchor='e')

        self.__img_label.grid(row=0, column=0, columnspan=3, sticky='NSEW')
        self.__button_back.grid(row=1, column=0)
        self.__button_forward.grid(row=1, column=2)
        self.__status.grid(row=3, column=0, columnspan=3, sticky='EW')

class AboutWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master=master
        self.create_widgets()

    def create_widgets(self):
        self.title("このアプリケーションについて")
        self.iconbitmap(self.master.icon_image) #Works only on Windows OS
        self.resizable(tk.FALSE,tk.FALSE)
        # self.geometry("500x300")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        # self.grid_rowconfigure(0, weight=0)
        # self.grid_rowconfigure(1, weight=0)

        logo_img = Image.open(self.master.icon_image)
        # logo_img = Image.open('./imgs/nuntara.png')
        logo_img = logo_img.resize((100, 100), Image.LANCZOS)
        tk_logo_img = ImageTk.PhotoImage(logo_img)

        icon_label = ttk.Label(self, image=tk_logo_img, anchor='e')
        title_label = ttk.Label(self, text=__appname__, font=("", 50, "italic"), anchor='w')
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        date_label = ttk.Label(self, text="最終更新日: ", anchor='e')
        date_label2 = ttk.Label(self, text=__date__, anchor='w')
        ver_label = ttk.Label(self, text="アプリケーションバージョン: ", anchor='e')
        ver_label2 = ttk.Label(self, text=str(__version__), anchor='w')
        pyver_label = ttk.Label(self, text="Pythonバージョン: ", anchor='e')
        pyver_label2 = ttk.Label(self, text=str(__deprecated__.split(", ")[1]), anchor='w')
        popver_label = ttk.Label(self, text="Popplerバージョン: ", anchor='e')
        popver_label2 = ttk.Label(self, text=str(__deprecated__.split(", ")[2]), anchor='w')
        osver_label = ttk.Label(self, text="動作環境: ", anchor='e')
        osver_label2 = ttk.Label(self, text=str(__deprecated__.split(", ")[0]), anchor='w')
        author_label = ttk.Label(self, text="作者:\n", anchor='e')
        author_label2 = ttk.Label(self, text="\n".join(__author__), anchor='w')
        license_label = ttk.Label(self, text="ライセンス: ", anchor='e')
        license_label2 = ttk.Label(self, text=__license__, anchor='w')
        close_about_button = ttk.Button(self, text="閉じる", command=self.destroy)
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        copyright_label = ttk.Label(self, text=__copyright__)

        icon_label.grid(row=0, column=0, padx=20, pady=10, sticky="NSEW")
        title_label.grid(row=0, column=1, padx=2, sticky="NSEW")
        separator.grid(row=1, column=0, pady=3, columnspan=2, sticky="NSEW")
        date_label.grid(row=2, column=0, pady=2, sticky="NSEW")
        date_label2.grid(row=2, column=1, padx=5, pady=2, sticky="NSEW")
        ver_label.grid(row=3, column=0, pady=2, sticky="NSEW")
        ver_label2.grid(row=3, column=1, padx=5, pady=2, sticky="NSEW")
        pyver_label.grid(row=4, column=0, pady=2, sticky="NSEW")
        pyver_label2.grid(row=4, column=1, padx=5, pady=2, sticky="NSEW")
        popver_label.grid(row=5, column=0, pady=2, sticky="NSEW")
        popver_label2.grid(row=5, column=1, padx=5, pady=2, sticky="NSEW")
        osver_label.grid(row=6, column=0, pady=2, sticky="NSEW")
        osver_label2.grid(row=6, column=1, padx=5, pady=2, sticky="NSEW")
        author_label.grid(row=7, column=0, pady=2, sticky="NSEW")
        author_label2.grid(row=7, column=1, padx=5, pady=2, sticky="NSEW")
        license_label.grid(row=8, column=0, pady=2, sticky="NSEW")
        license_label2.grid(row=8, column=1, padx=5, pady=2, sticky="NSEW")
        close_about_button.grid(row=9, column=0, pady=15, columnspan=2)
        separator.grid(row=10, column=0, columnspan=2, sticky="NSEW")
        copyright_label.grid(row=11, column=0, pady=5, columnspan=2)

class AidaCore:
    def get_abs_path(self, relative_path): # 絶対パスを返す
        bundle_dir = os.path.abspath(os.path.dirname(__file__))
        absolute_path = os.path.join(bundle_dir, relative_path).replace('/', os.sep)
        return absolute_path

    def save_tiff_stack(self, save_path, imgs_list, dpi_value):
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

    def save_pdf_stack(self, save_path, imgs):
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

    def img_comp(self): #run_program()の内容の内、メインとなる部分だけ引っ張り出す。
        pass

    def opened_file_check(self, checking_file):
        # if os.path.isfile(checking_file):
        #     while True:
        #         try:
        #             os.rename(checking_file, checking_file)
        #         except:
        #             response = messagebox.askretrycancel("エラーメッセージ", "保存先へのアクセスが拒否されました。\n"\
        #                 "保存先で同一名のファイルが使用中である可能性があります。\n"\
        #                     "ファイルが開かれていないことを確認ください。")
        #             if response == False:
        #                 self.stop_program()
        #                 break
        #         else: break
        pass

if __name__ == "__main__":
    main()
