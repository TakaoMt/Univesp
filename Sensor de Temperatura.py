import tkinter as tk
from tkinter import ttk, messagebox
import wmi
import os
from time import sleep
from twilio.rest import Client
import threading

class TemperatureMonitorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Monitor de Temperatura")

        self.temperature_values = {}
        self.temperature_limit = self.load_temperature_limit()
        self.phone_number = self.load_phone_number()
        self.check_interval = self.load_check_interval()

        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(padx=10, pady=10)

        self.configure_label = ttk.Label(self.main_frame, text="Insira o limite de temperatura:")
        self.configure_label.grid(row=0, column=0, padx=10, pady=5)

        self.temperature_entry = ttk.Entry(self.main_frame)
        self.temperature_entry.grid(row=0, column=1, padx=10, pady=5)

        self.configure_button = ttk.Button(self.main_frame, text="Configurar", command=self.configure_temperature_limit)
        self.configure_button.grid(row=0, column=2, padx=10, pady=5)

        self.temperature_limit_label = ttk.Label(self.main_frame, text=f"Temperatura Limite: {self.temperature_limit} °C")
        self.temperature_limit_label.grid(row=0, column=3, padx=10, pady=5)

        self.phone_number_label = ttk.Label(self.main_frame, text="Insira o número de telefone:")
        self.phone_number_label.grid(row=1, column=0, padx=10, pady=5)

        self.phone_number_entry = ttk.Entry(self.main_frame)
        self.phone_number_entry.grid(row=1, column=1, padx=10, pady=5)

        self.interval_label = ttk.Label(self.main_frame, text="Intervalo de verificação (s):")
        self.interval_label.grid(row=2, column=0, padx=10, pady=5)

        self.interval_entry = ttk.Entry(self.main_frame)
        self.interval_entry.grid(row=2, column=1, padx=10, pady=5)

        self.start_button = ttk.Button(self.main_frame, text="Iniciar Monitoramento", command=self.start_monitoring)
        self.start_button.grid(row=3, column=0, columnspan=4, padx=10, pady=5)

        self.error_displayed = False
        self.monitoring = False

    def load_temperature_limit(self):
        if os.path.exists("temperature_limit.txt"):
            with open("temperature_limit.txt", "r") as file:
                temperature_limit = file.readline().strip()
                try:
                    temperature_limit = float(temperature_limit)
                    return temperature_limit
                except ValueError:
                    return None
        return None

    def load_phone_number(self):
        if os.path.exists("phone_number.txt"):
            with open("phone_number.txt", "r") as file:
                phone_number = file.readline().strip()
                return phone_number
        return None

    def load_check_interval(self):
        if os.path.exists("check_interval.txt"):
            with open("check_interval.txt", "r") as file:
                check_interval = file.readline().strip()
                try:
                    check_interval = float(check_interval)
                    return check_interval
                except ValueError:
                    return None
        return None

    def save_temperature_limit(self, temperature_limit):
        with open("temperature_limit.txt", "w") as file:
            file.write(str(temperature_limit))

    def save_phone_number(self, phone_number):
        with open("phone_number.txt", "w") as file:
            file.write(phone_number)

    def save_check_interval(self, check_interval):
        with open("check_interval.txt", "w") as file:
            file.write(str(check_interval))

    def get_temperature_sensors(self):
        try:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            temperature_sensors = {}
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature':
                    temperature_sensors[sensor.Name] = sensor.Value
            return temperature_sensors
        except Exception as e:
            print(f"Erro ao recuperar sensores de temperatura: {e}")
            return None

    def send_whatsapp_message(self, message):
        account_sid = 'your_account_sid'
        auth_token = 'your_auth_token'
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=message,
            from_='whatsapp:+14155238886',  # Número do Twilio WhatsApp
            to=f'whatsapp:{self.phone_number}'
        )
        print("Mensagem enviada:", message.sid)

    def update_temperature(self):
        temperature_sensors = self.get_temperature_sensors()
        if temperature_sensors is not None:
            for sensor_name, sensor_value in temperature_sensors.items():
                if sensor_name not in self.temperature_values:
                    self.temperature_values[sensor_name] = []
                if len(self.temperature_values[sensor_name]) >= 3:
                    self.temperature_values[sensor_name].pop(0)  # Remove a leitura mais antiga
                self.temperature_values[sensor_name].append(sensor_value)
            self.display_temperature_values()
            self.check_temperature_limit()
        else:
            self.show_error_message("Falha ao recuperar sensores de temperatura.")

    def display_temperature_values(self):
        for widget in self.main_frame.winfo_children():
            if widget not in [self.configure_label, self.temperature_entry, self.configure_button,
                              self.phone_number_label, self.phone_number_entry, self.interval_label,
                              self.interval_entry, self.start_button, self.temperature_limit_label]:
                widget.destroy()

        if self.temperature_values:
            for index, (sensor_name, temp_readings) in enumerate(self.temperature_values.items()):
                box_frame = ttk.Frame(self.main_frame, borderwidth=2, relief="groove")
                box_frame.grid(row=index + 4, column=0, padx=10, pady=10, sticky="nsew", columnspan=4)

                label = ttk.Label(box_frame, text=f"Sensor: {sensor_name}", font=("Arial", 12, "bold"))
                label.grid(row=0, column=0, padx=10, pady=5, columnspan=3)

                for row, temp_reading in enumerate(temp_readings, start=1):
                    color = "black"
                    if self.temperature_limit is not None:
                        color = "red" if temp_reading > self.temperature_limit else "green"
                    label = ttk.Label(box_frame, text=f"Leitura {row}: {temp_reading} °C", foreground=color)
                    label.grid(row=row, column=0, padx=10, pady=5, sticky="w", columnspan=3)

    def check_temperature_limit(self):
        for sensor_name, temp_readings in self.temperature_values.items():
            last_reading = temp_readings[-1]
            if self.temperature_limit is not None and last_reading > self.temperature_limit:
                message = f"A temperatura do sensor {sensor_name} ultrapassou o limite de {self.temperature_limit} °C."
                self.send_whatsapp_message(message)

    def configure_temperature_limit(self):
        try:
            temperature_limit = float(self.temperature_entry.get())
            if temperature_limit >= 0:
                self.temperature_limit = temperature_limit
                self.save_temperature_limit(temperature_limit)
                self.temperature_limit_label.config(text=f"Temperatura Limite: {temperature_limit} °C")
                messagebox.showinfo("Sucesso", f"Limite de temperatura definido para {temperature_limit} °C.")
            else:
                messagebox.showerror("Erro", "Por favor, insira um valor positivo para o limite de temperatura.")
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um número válido para o limite de temperatura.")

    def start_monitoring(self):
        if self.monitoring:
            messagebox.showwarning("Aviso", "O monitoramento já está em execução.")
            return
        try:
            check_interval = float(self.interval_entry.get())
            phone_number = self.phone_number_entry.get()
            if check_interval > 0 and phone_number:
                self.check_interval = check_interval
                self.phone_number = phone_number
                self.save_check_interval(check_interval)
                self.save_phone_number(phone_number)
                messagebox.showinfo("Sucesso", f"Intervalo de verificação definido para {check_interval} segundos.")
                self.monitoring = True
                self.monitor_thread = threading.Thread(target=self.continuously_monitor_temperature)
                self.monitor_thread.start()
            else:
                messagebox.showerror("Erro", "Por favor, insira valores positivos para o intervalo de verificação e o número de telefone.")
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um número válido para o intervalo de verificação.")

    def continuously_monitor_temperature(self):
        while self.monitoring:
            self.update_temperature()
            sleep(self.check_interval)

    def show_error_message(self, message):
        if not self.error_displayed:
            messagebox.showerror("Erro", message)
            self.error_displayed = True

def main():
    root = tk.Tk()
    app = TemperatureMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
