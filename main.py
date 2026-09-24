from tkinter import *
import tkinter as tk
import ttkbootstrap as ttk
import time
from pathlib import Path




# fonctions
def update_time():
    current_time = time.strftime('%Y-%m-%d  %H:%M:%S')
    time_label.config(text=current_time)
    time_label.after(1000, update_time)

def Start():
        # Create a new Frame inside the LabelFrame
        new_window_frame = ttk.Frame(lframe, bootstyle="info")
        new_window_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Add a label to the new frame
        label = ttk.Label(new_window_frame, text="Ceci est une nouvelle fenetre", font=("Helvetica", 14))
        label.pack(pady=10)

        # Add a close button to the new frame
        close_button = ttk.Button(new_window_frame, text="fermer",  command=new_window_frame.destroy)
        close_button.pack(pady=5)

#fenetre configuration
fen = ttk.Window(themename="darkly")
fen.title("KKB - GestCom")
fen.geometry("1200x650")
icon_path = Path(__file__).resolve().parent / 'src' / 'images' / 'logo_kkbgestcom (1).ico'
if icon_path.is_file():
    try:
        fen.iconbitmap(str(icon_path))
    except tk.TclError:
        pass
# frame
main_frame = ttk.LabelFrame(fen, width=100, height=50, borderwidth=50, relief=tk.GROOVE ,text="menu")
main_frame.pack(side=LEFT,padx=10)
top_frame = ttk.LabelFrame(fen, width=10, height=120, borderwidth=50, relief=tk.GROOVE ,text="top")
top_frame.pack(side= TOP, fill=X, padx=10)

#label
lab1 = ttk.Label(text="wellcome")
lab1.place(x=50,y=20)
lab2 = ttk.Label(text="Bienvenue")
lab2.place(x=50,y=40) 
lab3 = ttk.Label(top_frame,text="KKB")
lab3.pack(side=LEFT)
lab4 = ttk.Label(top_frame,text="GesTcom")
lab4.pack(side=LEFT)
#toggle button
lab_tog = ttk.Label(top_frame,text="Dark")
lab_tog.pack(side=RIGHT)
tog = ttk.Checkbutton(top_frame,bootstyle ="round-toggle")
tog.pack(side=RIGHT)
time_label = Label(top_frame, font=('Helvetica', 24))
time_label.pack(side=BOTTOM)

update_time()


#label frame
# label_frame = ttk.Labelframe(main_frame, text="Frame Title", bootstyle="info", padding=10, height=10, width=10)
# label_frame.pack(padx=300,pady=100, expand=True,fill=BOTH)
# label_frame.grid(sticky=SE)

#icon button
but1 = ttk.Button(main_frame,bootstyle = "Dark", text="Valider Vente", width=20)
but1.grid(column=0 , row=0,pady=5)
but2 = ttk.Button(main_frame,bootstyle = "Dark", text="Enregistrer Index", width=20)
but2.grid(column=0 , row=1,pady=5)
but3 = ttk.Button(main_frame,bootstyle = "Dark", text="Les Articles", width=20)
but3.grid(column=0 , row=2 ,pady=5)
but4 = ttk.Button(main_frame,bootstyle = "Dark", text="Solde Transaction", width=20)
but4.grid(column=0 , row=3 ,pady=5)
but5 = ttk.Button(main_frame,bootstyle = "Dark", text="statistique ", width=20)
but5.grid(column=0 , row=4 ,pady=5)
but5 = ttk.Button(main_frame,bootstyle = "Dark", text="configuration ", width=20)
but5.grid(column=0 , row=5 ,pady=5)

#logo
#date
#time
#fenetre de travail
# Create a LabelFrame to hold the internal "windows"
lframe = ttk.LabelFrame(fen, text="Espace de travail", bootstyle="primary")
lframe.pack(fill=BOTH, expand=True, padx=10, pady=10)

# Create a button that "opens" a new internal window
open_window_button = ttk.Button(
    fen, 
    text="start", 
    command=Start
)
open_window_button.pack(pady=10)






fen.mainloop()

