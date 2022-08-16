from tkinter import ttk, Tk, Entry, Label, Text, HORIZONTAL, RIGHT, Y
import threading
import client


class Gui:
    def __init__(self):
        self.window = Tk()
        self.window.title("chat")
        self.window.geometry("600x600")
        self.window.configure(bg="lightgray")
        self.msg_label = Text(self.window)
        self.msg_label.place(x=20, y=55, width=550, height=400)
        self.msg_label.config(state="disabled")
        #inputs
        self.name_text = Entry(self.window)
        self.name_text.place(x=100, y=10)
        self.message = Entry(self.window)
        self.message.place(x=150, y=480, width=300, height=19)
        self.dest_send = Entry(self.window)
        self.dest_send.place(x=20, y=480)
        self.file_name = Entry(self.window)
        self.file_name.place(x=20, y=530)
        #Button
        ttk.Button(self.window, text="login", width=7, command=self.login).place(x=2, y=4)
        ttk.Button(self.window, text="show online", width=15, command=self.get_users).place(x=350, y=10)
        ttk.Button(self.window, text="show server files", width=15, command=self.get_files).place(x=2, y=30)
        ttk.Button(self.window, text="send", width=10, command=self.send).place(x=460, y=480)
        ttk.Button(self.window, text="Download", width=10, command=self.download).place(x=380, y=525)
        ttk.Button(self.window, text="stop Download", width=15, command=self.stop_download).place(x=460, y=525)
        self.name = ""
        self.mes = ""
        self.size_file = ""
        # name button
        self.name_button = Label(self.window, text="name:", bg="lightgray")
        self.name_button.place(x=60, y=10)
        self.name_button.config(font=("Ariel", 8))
        self.dest_button = Label(self.window, text="To(blank to all)", bg="lightgray")
        self.dest_button.place(x=20, y=460)
        self.dest_button.config(font=("Ariel", 8))
        self.message_button = Label(self.window, text="message", bg="lightgray")
        self.message_button.place(x=150, y=460)
        self.message_button.config(font=("Ariel", 8))
        self.file_name_button = Label(self.window, text="server file name", bg="lightgray")
        self.file_name_button.place(x=20, y=510)
        self.file_name_button.config(font=("Ariel", 8))
        # scrollbar
        self.scrollbar = ttk.Scrollbar(self.window)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.scrollbar.configure(command=self.msg_label.yview)
        # Percent
        self.my_prog = ttk.Progressbar(self.window, orient=HORIZONTAL, length=150, mode='determinate')
        self.my_prog.place(x=20, y=560)
        self.my_pres = Label(self.window, text="")
        self.my_pres.place(x=80, y=563)
        self.my_pres.config(text=self.my_prog['value'], font=("Ariel", 6), bg='white')

        self.stop_thread = True
        self.thread = threading.Thread(target=self.recv)
        self.window.mainloop()

    # connect
    def login(self):
        self.name = self.name_text.get()
        ack = client.connect(self.name)
        print(ack)
        if ack == "<connected>":
            self.stop_thread = False
            self.thread.start()
            ttk.Button(self.window, text="logout", width=7, command=self.logout).place(x=2, y=4)
            self.mes = self.name + " connected"
            self.print(self.mes)
        else:
            ttk.Button(self.window, text="login", width=7, command=self.login).place(x=2, y=4)
            self.mes = ack
            self.mes += "\n"
            self.mes += "try another name"
            self.print(self.mes)
            print(ack)

    # disconnect
    def logout(self):
        client.process_request("disconnect")
        self.stop_thread = True
        self.window.destroy()

    # get list of online users
    @staticmethod
    def get_users():
        client.process_request("getusers")

    def handle_user_list(self, mes_recv):
        size = mes_recv.find("<", 1)
        size_of_user = int(mes_recv[size + 1])
        mes_recv = mes_recv[size + 3:len(mes_recv)]
        users = []
        for _ in range(size_of_user):
            start = mes_recv.find("<", 0)
            end = mes_recv.find(">", 1)
            users.append(mes_recv[start + 1:end])
            mes_recv = mes_recv[end + 1:len(mes_recv)]
        self.mes = f"--online list--\n{', '.join(users)}\n--end list--"

    # Messages received from the server
    def recv(self):
        while not self.stop_thread:
            if len(client.message_recv) != 0:
                mes_recv = client.message_recv.pop(0)
                if mes_recv.startswith("<users_lst>"):
                    self.handle_user_list(mes_recv)
                elif mes_recv.startswith("<msg_lst>"):
                    mes_recv = mes_recv[13:len(mes_recv)]
                    size = mes_recv.find("<", 0)
                    send_name = mes_recv[0:size - 1]
                    size1 = mes_recv.find(">", size + 1)
                    mes_recv = mes_recv[size + 1:size1]
                    self.mes = send_name + ":" + mes_recv
                elif mes_recv.startswith("<file_lst>"):
                    mes_recv = mes_recv[10:len(mes_recv)]
                    name_file = ""
                    file_list = []
                    while name_file != "end":
                        start = mes_recv.find("<", 0)
                        end = mes_recv.find(">", 1)
                        name_file = mes_recv[start + 1:end]
                        file_list.append(name_file)
                        mes_recv = mes_recv[end + 1:len(mes_recv)]
                    self.mes = f"--file list--\n{', '.join(file_list[:-1])}"
                elif mes_recv.startswith("client"):
                    self.mes = mes_recv
                elif mes_recv == "done writing file":
                    self.mes = "press procces to continue"
                    self.my_prog['value'] = 50
                    self.my_pres.config(text=self.my_prog['value'], font=("Ariel", 6), bg='white')
                    ttk.Button(self.window, text="process", width=10, command=self.continue_download).place(x=380, y=525)
                elif mes_recv.startswith("User"):
                    self.mes = mes_recv
                    self.my_prog['value'] = 100
                    self.my_pres.config(text=self.my_prog['value'], font=("Ariel", 6), bg='white')
                elif mes_recv.startswith("<size>"):
                    self.mes = "Downloads"
                    index = mes_recv.find(">", len(mes_recv) - 6)
                    mes_recv = mes_recv[0:index]
                    index = mes_recv.find("<", len(mes_recv) - 6)
                    self.size_file = mes_recv[index + 1:len(mes_recv)]
                elif mes_recv.startswith("Couldn't find user"):
                    self.mes=mes_recv
                elif mes_recv.startswith("<File>"):
                    self.mes=mes_recv
                if self.mes != "":
                    self.print(self.mes)

    # send message
    def send(self):
        dest_name = self.dest_send.get()
        message = self.message.get()
        self.print(self.name + ":" + message)
        if dest_name != "":
            mes = "send" + " " + dest_name + " " + " " + message + " "
        else:
            mes = "sendall" + " " + message + " "
        client.process_request(mes)

    def continue_download(self):
        file_name = self.file_name.get()
        client.process_request("continue" + " " + file_name)
        ttk.Button(self.window, text="download", width=10, command=self.download).place(x=380, y=525)

    # Prints on screen
    def print(self, mes):
        self.msg_label.config(state='normal')
        self.msg_label.insert('end', mes)
        self.msg_label.yview('end')
        self.msg_label.insert('end', "\n")
        self.msg_label.config(state='disable')

    # List of files on the server
    @staticmethod
    def get_files():
        client.process_request("getfilelist")

    # Download file
    def download(self):
        self.my_prog['value'] = 0
        self.my_pres.config(text=self.my_prog['value'], font=("Ariel", 6), bg='white')
        file_name = self.file_name.get()
        client.process_request("download" + " " + file_name)

    # Stop downloading the file
    def stop_download(self):
        client.process_request("stop " + self.size_file)
        ttk.Button(self.window, text="download", width=10, command=self.download).place(x=380, y=525)
        self.print("Download stopped")



if __name__ == '__main__':
    i = Gui()
