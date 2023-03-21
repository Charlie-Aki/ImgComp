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
        self.title(__appname__+"Ver."+__version__)
        aida_func=AidaCore()
        self.iconbitmap(aida_func.get_abs_path('./imgs/ImgComp_256x256.ico').replace('/', os.sep)) # Windows用アイコン設定
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
        self.menubar=Menubar(master=self)
        self.main_frame=MainFrame(master=self)
        self.progress_window_frame=ProgressWindowFrame(master=self)
        # self.how2use_window=How2UseWindow(master=self)
        # self.about_window=AboutWindow(master=self)

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
        self.settings=master.settings
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
        old_entry = ttk.Entry(self, width=30)
        old_entry.grid(row=0, column=1, columnspan=2, sticky='EW')
        new_entry = ttk.Entry(self, width=30)
        new_entry.grid(row=1, column=1, columnspan=2, sticky='EW')
        outdir_entry = ttk.Entry(self, width=30)
        outdir_entry.insert(0, self.settings["output_dir"])
        outdir_entry.grid(row=2, column=1, columnspan=2, sticky='EW')

        old_entry.drop_target_register(tkdnd.DND_FILES)
        old_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_files, focus_entry=old_entry))
        new_entry.drop_target_register(tkdnd.DND_FILES)
        new_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_files, focus_entry=new_entry))
        outdir_entry.drop_target_register(tkdnd.DND_FILES)
        outdir_entry.dnd_bind('<<Drop>>', functools.partial(self.drop_folder, focus_entry=outdir_entry))

        # Create Buttons for Main Frame
        old_dialogue_button = ttk.Button(self, text="参照", command=do_nothing)
        new_dialogue_button = ttk.Button(self, text="参照", command=do_nothing)
        outdir_dialogue_button = ttk.Button(self, text="参照", command=do_nothing)
        old_clear_button = ttk.Button(self, text="クリア", command=do_nothing)
        new_clear_button = ttk.Button(self, text="クリア", command=do_nothing)
        outdir_clear_button = ttk.Button(self, text="クリア", command=do_nothing)
        run_button = ttk.Button(self, text="実行", command=do_nothing)
        stop_button = ttk.Button(self, text="中断", command=do_nothing)
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
        check_tiff = ttk.Checkbutton(self, text="tiff", variable=outext1, onvalue="tiff_on", offvalue="tiff_off", command=lambda: print(outext1.get()))
        check_pdf = ttk.Checkbutton(self, text="pdf", variable=outext2, onvalue="pdf_on", offvalue="pdf_off", command=lambda: print(outext2.get()))
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


class ProgressWindowFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
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
        Progress_Window = tk.Text(self, wrap=tk.NONE, fg="white", bg="black")
        Progress_Window.grid(row=0, column=0, sticky='NSEW')
        scrollbar_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.Progress_Window.yview)
        scrollbar_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.Progress_Window.xview)
        Progress_Window['yscrollcommand'] = scrollbar_y.set
        Progress_Window['xscrollcommand'] = scrollbar_x.set
        scrollbar_y.grid(row=0, column=1, sticky='NS')
        scrollbar_x.grid(row=1, column=0, sticky='EW')
        Progress_Window.insert(tk.END, "ファイルと出力先を選択し、「実行」をクリックしてください。")
        Progress_Window.configure(state="disable")

class How2UseWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

class AboutWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

class AidaCore:
    def get_abs_path(self, relative_path): # 絶対パスを返す
        bundle_dir = os.path.abspath(os.path.dirname(__file__))
        absolute_path = os.path.join(bundle_dir, relative_path)
        return absolute_path

    def save_tiff_stack(self, save_path, imgs_list, dpi_value):
        pass

    def save_pdf_stack(self, save_path, imgs):
        pass

    def img_comp(self):
        pass


if __name__ == "__main__":
    main()
