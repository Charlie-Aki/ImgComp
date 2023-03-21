#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinterdnd2 as tkdnd
from PIL import ImageTk, Image, ImageDraw,\
     ImageFont, ImageSequence, ImageChops
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

# Popplerのパスを通す
poppler_path = os.path.join(os.getcwd(), "poppler-23.01.0", "bin")
os.environ["PATH"] += os.pathsep + poppler_path

def main():
    app=Application()
    app.mainloop()

def do_nothing():
    pass

class Application(tkdnd.TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        global aida_func
        aida_func=AidaCore(self.progress_window_frame, self.main_frame)
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
        self.progress_window_frame=ProgressWindowFrame(master=self)
        self.main_frame=MainFrame(master=self, ctrl_frame=self.progress_window_frame)
        self.menubar=Menubar(master=self, ctrl_frame=self.main_frame)

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
        file_menu.add_command(label="旧図ファイル選択", command=self.ctrl_frame.old_entry_dialogue)
        file_menu.add_command(label="改訂図ファイル選択", command=self.ctrl_frame.new_entry_dialogue)
        file_menu.add_command(label="出力先フォルダ選択", command=self.ctrl_frame.outdir_entry_dialogue)
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
        thread_flag = threading.Event() # 中断ボタン監視フラグ(set()=true;継続, clear()=false;中断)
        self.create_widgets(thread_flag)

    # def specify_style(self):
    #     s=ttk.Style()
    #     s.theme_use('vista')
    #     s.configure('main_frame.theme', background='red')
    #     return s

    def create_widgets(self, thread_flag):
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
        self.run_button = ttk.Button(self, text="実行", command=self.run_program(thread_flag=thread_flag))
        self.stop_button = ttk.Button(self, text="中断", command=self.stop_program(thread_flag=thread_flag))
        self.stop_button.state(["disabled"]) #Disable the button.
        old_dialogue_button.grid(row=0, column=3)
        new_dialogue_button.grid(row=1, column=3)
        outdir_dialogue_button.grid(row=2, column=3)
        old_clear_button.grid(row=0, column=4)
        new_clear_button.grid(row=1, column=4)
        outdir_clear_button.grid(row=2, column=4)
        self.run_button.grid(row=4, column=1)
        self.stop_button.grid(row=4, column=2)

        # Create Check Button
        self.outext1 = tk.StringVar()
        self.outext2 = tk.StringVar()
        self.outext1.set(self.settings["outext1"])
        self.outext2.set(self.settings["outext2"])
        check_tiff = ttk.Checkbutton(self, text="tiff", variable=self.outext1, onvalue="tiff_on", offvalue="tiff_off")
        check_pdf = ttk.Checkbutton(self, text="pdf", variable=self.outext2, onvalue="pdf_on", offvalue="pdf_off")
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
        setting_data = {
            "output_dir": self.self.outdir_entry.get(),
            "outext1": self.outext1.get(),
            "outext2": self.outext2.get()
        }
        with open(setting_file_path, "w") as _file:
            json.dump(setting_data, _file)

    def run_program(self, thread_flag):
        try:
            self.record_settings(self.settings)
            self.run_button.state(["disabled"])  # Disable run button.
            self.stop_button.state(["!disabled"])  # Enable stop button.
            self.ctrl_frame.text_message_init()
            # self.file_menu.entryconfig("実行", state="disabled")  # Disable run menu.
            # self.file_menu.entryconfig("中断", state="normal")  # Enable stop menu.

            ######################
            #ファイル名読み込み
            ######################
            fname1 = tuple(self.old_entry.get().split(','))
            fname2 = tuple(self.new_entry.get().split(','))
            output_dir = self.outdir_entry.get()

            ######################
            #読み込んだファイル・フォルダのエラーチェック
            ######################
            file_exts = aida_func.detect_exts(fname1, fname2)
            #エントリーボックスが空
            if fname1 == ('',) or fname2 == ('',) or len(output_dir) == 0:
                self.regular_error("ファイルか保存先が指定されていません。")
                return
            #読み込みファイル数エラー
            elif len(fname1) != len(fname2):
                self.regular_error("比較対象のファイル数が異なります。")
                return
            #非対応拡張子エラー(tiffかPDFファイル以外を選択した場合)
            elif not file_exts[0].endswith(".tif") and not file_exts[0].endswith(".tiff")\
                and not file_exts[0].endswith(".pdf"):
                self.regular_error("tiff形式かpdf形式のファイルを選択してください。")
                return
            #拡張子混在エラー(.tiffと.tifの混在はOKにしてる)
            elif len(set(file_exts)) != 1 and file_exts[0][0:4] != file_exts[1][0:4]:
                self.regular_error("異なる形式の拡張子が混在しています。\n"\
                    "同じ形式のファイルを選択してください。")
                return
            #tiffもpdfもどちらもチェックボックスがOFFの時
            elif self.outext1.get() == "tiff_off" and self.outext2.get() == "pdf_off":
                self.regular_error("出力形式が選択されていません。\n"\
                    "tiffまたはpdfまたは両方のチェックボックスにチェックを入れてください。")
                return
            #出力先フォルダが存在しない
            elif os.path.isdir(output_dir) == False:
                self.regular_error("選択された出力先フォルダは存在しません。")
                return
            #存在しないファイルが含まれる
            elif self.isanyfile(fname1) == False or self.isanyfile(fname2) == False:
                self.regular_error("選択されたファイルに存在しないファイルが含まれています。")
                return

            thread_main = threading.Thread(target=self.img_comp_flow(thread_flag=thread_flag, fname1=fname1, fname2=fname2, output_dir=output_dir))
            thread_flag.set()
            thread_main.start()

        except:
            import traceback
            with open(os.path.join(output_dir, "ERR_DETECT_IMGCOMP.txt"), "w") as error_output:
                traceback.print_exc(file=error_output)
            self.regular_error("予期せぬエラーが発生しました。\nプログラムを終了します。")
            self.master.quit()

    def isanyfile(self, file_paths):
        #一度でもFalseになったらFalseを返す
        for name in file_paths:
            if os.path.isfile(name) == False:
                return False
        #一回もFalseにならなければTrueを返す
        return True

    def img_comp_flow(self, thread_flag, fname1, fname2, output_dir):
        """
        画像の画素差分出力を流す。コアとなる処理はAidaCoreクラスから呼び出し。
        """
        file_exts = aida_func.detect_exts(self.fname1, self.fname2)

        ######################
        #比較⇒変換⇒出力
        ######################
        for j in range(len(fname1)):
            if thread_flag.is_set() == True:
                scroll_txt = "ファイルの読み込み中..."
                self.ctrl_frame.text_message(scroll_txt)

                #画像バイナリデータの読み込み
                drw1, drw2, num_frames, dpi_value = aida_func.read_binary_image(
                    fname1[j], fname2[j])

                #pdf2image上限エラー
                if file_exts[0].endswith(".pdf") and num_frames > 100:
                    self.regular_error(
                        "PDFファイルは100ページまでしか読み込めません。")
                    return

                #配列の初期化
                drw_out_4dim_pages = []
                if thread_flag.is_set() == True:
                    #画像比較
                    for page in range(0, num_frames):
                        scroll_txt = str(j+1)+"/"+str(len(fname1))+"ファイルの" +\
                            str(page+1)+"/"+str(num_frames)+"ページ目を処理中..."
                        self.ctrl_frame.text_message(scroll_txt)

                        #画像のグレースケール化＋出力用変数(drw_out)の準備
                        if drw1[page].size != drw2[page].size:
                            self.regular_error("同じサイズの画像を選択してください")
                            return

                        #新旧青/赤色付け
                        drw_out = aida_func.create_masked_image(
                            drw1[page], drw2[page])
                        #左上文字入れ
                        drw_out = aida_func.insert_text(
                            drw_out, fname1[j], fname2[j])
                        #配列内にまとめる
                        drw_out_4dim_pages.append(drw_out)

                    if thread_flag.is_set() == True:
                        #出力先に保存
                        scroll_txt = "出力先にファイルを保存しています..."
                        self.ctrl_frame.text_message(scroll_txt)
                        tiff_name = os.path.join(output_dir, "Output_"
                                                      + os.path.splitext(os.path.basename(fname2[j]))[0] + ".tif")
                        # 保存先で同一名ファイルが開かれていないかチェックする
                        self.opened_file_check(tiff_name)
                        if thread_flag.is_set() == True:
                            aida_func.save_tiff_stack(
                                tiff_name, drw_out_4dim_pages, dpi_value)
                        #pdfにチェックがあればPDFに変換する
                        if self.outext2.get() == "pdf_on":
                            save_path = os.path.join(output_dir, "Output_"
                                                          + os.path.splitext(os.path.basename(fname2[j]))[0] + ".pdf")
                            # 保存先で同一名ファイルが開かれていないかチェックする
                            self.opened_file_check(save_path)
                            if thread_flag.is_set() == True:
                                aida_func.save_pdf_stack(
                                    save_path, tiff_name)

                        if self.outext1.get() == "tiff_off":
                            # 保存先で同一名ファイルが開かれていないかチェックする
                            self.opened_file_check(tiff_name)
                            os.remove(tiff_name)

                        if thread_flag.is_set() == True:
                            scroll_txt = "保存しました。\n"
                            self.ctrl_frame.text_message(scroll_txt)

        if thread_flag.is_set() == True:
            response = messagebox.askquestion(
                "確認", "処理が完了しました。\n出力フォルダを開きますか？")
            if response == "yes":
                subprocess.Popen(["explorer", output_dir])
            scroll_txt = "\n正常に処理を完了しました。\n"
            self.ctrl_frame.text_message(scroll_txt)
        else:
            response = messagebox.askquestion(
                "確認", "処理が中断されました。\n出力フォルダを開きますか？")
            if response == "yes":
                subprocess.Popen(["explorer", output_dir])
            scroll_txt = "\n途中で処理を中断しました。\n"
            self.ctrl_frame.text_message(scroll_txt)

        self.run_button.state(["!disabled"])  # Enable run button.
        self.stop_button.state(["disabled"])  # Disable stop button.
        # self.file_menu.entryconfig("実行", state="normal")  # Enable run menu.
        # # Disable stop menu.
        # self.file_menu.entryconfig("中断", state="disabled")

        scroll_txt = "続けて実行する場合は再度ファイルと出力先を選択し、「実行」をクリックしてください。"
        self.ctrl_frame.text_message(scroll_txt)

    def stop_program(self, thread_flag):
        thread_flag.clear()
        self.stop_button.state(["disabled"])  # Disable stop button.
        # Disable stop menu.
        # self.file_menu.entryconfig("中断", state="disabled")
        scroll_txt = "処理を中断しています..."
        self.ctrl_frame.text_message(scroll_txt)

    def opened_file_check(self, checking_file):
        """
        ファイルが読み取り専用になっていないか調べる。
        """
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

    def regular_error(self, str_msg):
        """
        エラーメッセージの定型
        """
        messagebox.showerror("エラーメッセージ", str_msg)
        self.run_button.state(["!disabled"])  # Enable run button.
        self.stop_button.state(["disabled"])  # Disable stop button.
        # self.file_menu.entryconfig("実行", state="normal")  # Enable run menu.
        # # Disable stop menu.
        # self.file_menu.entryconfig("中断", state="disabled")
        scroll_txt = "ファイルと出力先を選択し、「実行」をクリックしてください。"
        self.ctrl_frame.text_message(scroll_txt)

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

        # Set ScrolledText for Progress Window Frame
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
        """
        スクロールボックスの中を空にする。
        """
        # Enable scrolled text box.
        self.progress_window.configure(state="normal")
        self.progress_window.delete(1.0, tk.END)  # Clear text box.
        # Disable scrolled text box.
        self.progress_window.configure(state="disable")

    def text_message(self, scroll_txt):
        """
        スクロールボックスにテキストを追加する。
        """
        # Enable scrolled text box.
        self.progress_window.configure(state="normal")
        self.progress_window.insert(tk.END, scroll_txt)  # Adding text.
        self.progress_window.insert(tk.END, "\n")
        self.progress_window.yview(tk.END)  # Auto scroll
        # Disable scrolled text box.
        self.progress_window.configure(state="disable")

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
    def get_abs_path(self, relative_path):
        """
        絶対パスを返す
        """
        bundle_dir = os.path.abspath(os.path.dirname(__file__))
        absolute_path = os.path.join(bundle_dir, relative_path).replace('/', os.sep)
        return absolute_path

    def detect_exts(self, fname1, fname2):
        file_exts = [str.lower(os.path.splitext(ext)[1]) for ext in fname1+fname2]
        return file_exts

    def read_binary_image(self, fname1, fname2):
        file_exts=self.detect_exts(fname1, fname2)
        if file_exts[0].endswith(".tif") or file_exts[0].endswith(".tiff"):
            drw1 = Image.open(fname1)
            drw2 = Image.open(fname2)
            itr1 = ImageSequence.Iterator(drw1)
            itr2 = ImageSequence.Iterator(drw2)
            num_frames = drw1.n_frames
            dpi_value = drw1.info['dpi']
            return itr1, itr2, num_frames, dpi_value
        elif file_exts[0].endswith(".pdf"):
            drw1 = pdf2image.convert_from_path(fname1, dpi=300)
            drw2 = pdf2image.convert_from_path(fname2, dpi=300)
            num_frames = len(drw1)
            dpi_value = (300, 300)
            return drw1, drw2, num_frames, dpi_value

    def create_masked_image(self, drw1, drw2):
        #グレースケールに変換、出力用のベース作成
        drw1_gray = drw1.convert("L")
        drw2_gray = drw2.convert("L")
        drw_out = drw2_gray.convert("RGB")

        #差分を色塗りするためのマスクの作成
        mask_red = ImageChops.subtract(drw1_gray, drw2_gray)
        mask_blue = ImageChops.subtract(drw2_gray, drw1_gray)

        #マスクを使用して差分箇所に色塗り
        drw_out.paste(Image.new("RGB", drw_out.size, "red"), mask=mask_red)
        drw_out.paste(Image.new("RGB", drw_out.size, "blue"), mask=mask_blue)

        return drw_out

    def insert_text(self, drw_out, fname1, fname2):
        #出力画像データに、「前データ => 後データ」のテキスト挿入 #Works only on Windows OS. Mac OS requires full path.
        fnt = ImageFont.truetype(
            "C:\Windows\Fonts\msgothic.ttc", int(drw_out.size[1]/60))
        drw_text = ImageDraw.Draw(drw_out)
        txt = os.path.splitext(os.path.basename(fname1))[0]+' => '\
            + os.path.splitext(os.path.basename(fname2))[0]
        drw_text.text((50, 50), txt, fill="red", font=fnt)
        txt = os.path.splitext(os.path.basename(fname1))[0]+' => '
        drw_text.text((50, 50), txt, fill="black", font=fnt)
        txt = os.path.splitext(os.path.basename(fname1))[0]
        drw_text.text((50, 50), txt, fill="blue", font=fnt)

        return drw_out

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
        tiff_stack = Image.open(imgs)

        for i in range(tiff_stack.n_frames):
            tiff_stack.seek(i)
            tiff_stack.save(return_data, 'TIFF')
            images.append(return_data.getvalue())

        with open(save_path, 'wb') as tmp:
            tmp.write(img2pdf.convert(images))
            tmp.close()

        tiff_stack.close()


if __name__ == "__main__":
    main()
