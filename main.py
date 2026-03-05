import serial
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from datetime import datetime
import os
from pathlib import Path


class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Сканер данных")
        self.root.iconbitmap("title.ico")
        self.root.geometry("1200x750")
        self.root.configure(bg='#f0f0f0')
        self.root.resizable(False, False)

        # Загрузка настроек
        self.load_settings()

        # Инициализация переменных
        self.serial_port = None
        self.reading = False
        self.current_image = None

        # Счётчик и отслеживание сканирований
        self.scan_count = 0
        self.scanned_barcodes = set()
        self.counter_color = 'green'

        # Создание интерфейса
        self.create_widgets()

        # Запуск чтения COM-порта
        self.start_serial_reading()

        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        """Загрузка настроек из JSON файла"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                self.settings = json.load(f)

            self.com_settings = self.settings['com_port']
            self.products = self.settings['products']
            self.logging_settings = self.settings['logging']

            if self.logging_settings['enabled']:
                log_dir = os.path.dirname(self.logging_settings['file'])
                if log_dir:
                    Path(log_dir).mkdir(parents=True, exist_ok=True)

        except FileNotFoundError:
            messagebox.showerror("Ошибка", "Файл settings.json не найден!")
            self.root.quit()
        except json.JSONDecodeError:
            messagebox.showerror("Ошибка", "Ошибка в формате settings.json!")
            self.root.quit()

    def create_widgets(self):
        """Создание элементов интерфейса"""

        # Заголовок
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=70)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="📦 Сканер штрих-кодов",
            font=('Arial', 20, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)

        # Основной контейнер
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Верхняя часть: изображение + счётчик + логи
        top_frame = tk.Frame(main_frame, bg='#f0f0f0')
        top_frame.pack(fill='both', expand=True, pady=(0, 15))

        # Фрейм для изображения (слева)
        image_frame = tk.LabelFrame(
            top_frame,
            text="Изображение продукта",
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        image_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        self.image_label = tk.Label(image_frame, bg='white', text="Ожидание сканирования...")
        self.image_label.pack(expand=True)

        # Фрейм для счётчика (центр)
        counter_frame = tk.LabelFrame(
            top_frame,
            text="Счётчик сканирований",
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10,
            width=250
        )
        counter_frame.pack(side='left', fill='y', padx=(0, 10))
        counter_frame.pack_propagate(False)

        # Большой счётчик
        self.counter_var = tk.StringVar()
        self.counter_var.set("0")

        self.counter_label = tk.Label(
            counter_frame,
            textvariable=self.counter_var,
            font=('Arial', 72, 'bold'),
            bg='#27ae60',
            fg='white',
            width=4,
            relief='sunken',
            bd=3
        )
        self.counter_label.pack(pady=20, fill='x')

        # Индикатор статуса счётчика
        self.counter_status_var = tk.StringVar()
        self.counter_status_var.set("Готов к сканированию")

        self.counter_status_label = tk.Label(
            counter_frame,
            textvariable=self.counter_status_var,
            font=('Arial', 10),
            bg='white',
            fg='#7f8c8d'
        )
        self.counter_status_label.pack(pady=10)

        # Кнопка сброса счётчика
        reset_btn = tk.Button(
            counter_frame,
            text="🔄 Сброс",
            command=self.reset_counter,
            font=('Arial', 11, 'bold'),
            bg='#3498db',
            fg='white',
            activebackground='#2980b9',
            activeforeground='white',
            relief='raised',
            bd=3,
            padx=20,
            pady=8
        )
        reset_btn.pack(pady=10)

        # Фрейм для логов (справа)
        log_frame = tk.LabelFrame(
            top_frame,
            text="📋 История сканирований",
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        log_frame.pack(side='right', fill='both', expand=True)

        # Текстовое поле для логов
        self.log_text = tk.Text(
            log_frame,
            font=('Consolas', 9),
            bg='#f8f9fa',
            fg='#2c3e50',
            wrap='word',
            state='disabled',
            relief='sunken',
            bd=2
        )
        self.log_text.pack(fill='both', expand=True)

        # Scrollbar для логов
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        log_scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        # Кнопка очистки логов
        clear_log_btn = tk.Button(
            log_frame,
            text="🗑️ Очистить логи",
            command=self.clear_logs,
            font=('Arial', 9),
            bg='#95a5a6',
            fg='white',
            activebackground='#7f8c8d',
            activeforeground='white',
            relief='raised',
            bd=2,
            padx=10,
            pady=5
        )
        clear_log_btn.pack(pady=(10, 0), fill='x')

        # Фрейм для информации о продукте
        info_frame = tk.LabelFrame(
            main_frame,
            text="Информация о продукте",
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        info_frame.pack(fill='x', pady=(0, 15))

        # Код продукта
        code_frame = tk.Frame(info_frame, bg='white')
        code_frame.pack(fill='x', pady=5)

        tk.Label(
            code_frame,
            text="Код:",
            font=('Arial', 10, 'bold'),
            bg='white',
            width=10,
            anchor='w'
        ).pack(side='left')

        self.code_var = tk.StringVar()
        self.code_var.set("Не отсканировано")
        tk.Label(
            code_frame,
            textvariable=self.code_var,
            font=('Arial', 10),
            bg='white',
            fg='#2980b9'
        ).pack(side='left')

        # Название продукта
        name_frame = tk.Frame(info_frame, bg='white')
        name_frame.pack(fill='x', pady=5)

        tk.Label(
            name_frame,
            text="Название:",
            font=('Arial', 10, 'bold'),
            bg='white',
            width=10,
            anchor='w'
        ).pack(side='left')

        self.name_var = tk.StringVar()
        self.name_var.set("-")
        self.name_label = tk.Label(
            name_frame,
            textvariable=self.name_var,
            font=('Arial', 10),
            bg='white',
            wraplength=500,
            justify='left'
        )
        self.name_label.pack(side='left', fill='x', expand=True)

        # Время сканирования
        time_frame = tk.Frame(info_frame, bg='white')
        time_frame.pack(fill='x', pady=5)

        tk.Label(
            time_frame,
            text="Время:",
            font=('Arial', 10, 'bold'),
            bg='white',
            width=10,
            anchor='w'
        ).pack(side='left')

        self.time_var = tk.StringVar()
        self.time_var.set("-")
        tk.Label(
            time_frame,
            textvariable=self.time_var,
            font=('Arial', 10),
            bg='white'
        ).pack(side='left')

        # Статус
        status_frame = tk.Frame(main_frame, bg='#ecf0f1', relief='sunken', bd=2)
        status_frame.pack(fill='x', pady=(0, 10))

        self.status_var = tk.StringVar()
        self.status_var.set("🔄 Подключение к COM-порту...")
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=('Arial', 9),
            bg='#ecf0f1',
            fg='#7f8c8d',
            pady=8
        )
        self.status_label.pack()

        # Кнопки управления
        buttons_frame = tk.Frame(main_frame, bg='#f0f0f0')
        buttons_frame.pack(fill='x', pady=10)

        # Кнопка выхода
        exit_btn = tk.Button(
            buttons_frame,
            text="❌ Выход",
            command=self.on_closing,
            font=('Arial', 11, 'bold'),
            bg='#e74c3c',
            fg='white',
            activebackground='#c0392b',
            activeforeground='white',
            relief='raised',
            bd=3,
            padx=30,
            pady=8
        )
        exit_btn.pack(side='right', padx=10)

    def start_serial_reading(self):
        """Запуск потока для чтения COM-порта"""
        try:
            self.serial_port = serial.Serial(
                port=self.com_settings['port'],
                baudrate=self.com_settings['baudrate'],
                timeout=self.com_settings['timeout']
            )
            self.status_var.set(f"✅ Порт {self.com_settings['port']} открыт. Ожидание данных...")
            self.status_label.config(fg='#27ae60')

            self.reading = True
            self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.serial_thread.start()

        except serial.SerialException as e:
            self.status_var.set(f"❌ Ошибка порта: {str(e)}")
            self.status_label.config(fg='#e74c3c')
            messagebox.showerror("Ошибка COM-порта", f"Не удалось открыть порт:\n{str(e)}")

    def read_serial(self):
        """Чтение данных из COM-порта в фоновом потоке"""
        while self.reading:
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    gtin = data[2:16] if len(data) >= 16 else data
                    if data:
                        self.root.after(0, lambda d=data, g=gtin: self.process_scan(d, g))
            except Exception as e:
                if self.reading:
                    self.root.after(0, lambda: self.status_var.set(f"❌ Ошибка чтения: {str(e)}"))

    def process_scan(self, barcode: str, gtin: str):
        """Обработка отсканированного штрих-кода"""
        timestamp = datetime.now()
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Обновление информации о продукте
        self.code_var.set(barcode)

        # Получение названия продукта
        product_name = "Неизвестный продукт"
        if gtin in self.products:
            product_name = self.products[gtin]['name']

        if gtin in self.products:
            product = self.products[gtin]
            self.name_var.set(product['name'])
            self.time_var.set(time_str)

            # Загрузка и отображение изображения
            self.load_product_image(product['image'])

            # Проверка на дубликат
            if barcode in self.scanned_barcodes:
                # Дубликат - синий цвет, счётчик не увеличивается
                self.update_counter_color(is_duplicate=True)
                self.status_var.set(f"🔵 Дубликат: {product['name']}")
                self.status_label.config(fg='#3498db')
                # Добавление в логи
                self.add_log_entry(time_str, barcode, product_name, is_duplicate=True)
            else:
                # Новый код - увеличиваем счётчик, чередуем цвета
                self.scanned_barcodes.add(barcode)
                self.update_counter_color(is_duplicate=False)
                self.status_var.set(f"✅ Отсканировано: {product['name']}")
                self.status_label.config(fg='#27ae60')
                # Добавление в логи
                self.add_log_entry(time_str, barcode, product_name, is_duplicate=False)
        else:
            self.name_var.set("❌ Продукт не найден в базе")
            self.time_var.set(time_str)
            self.clear_image()
            self.status_var.set(f"⚠️ Неизвестный код: {barcode}")
            self.status_label.config(fg='#e67e22')
            # Добавление в логи
            self.add_log_entry(time_str, barcode, "❌ Не найден в базе", is_duplicate=False)

        # Логирование в файл
        self.log_scan(barcode, timestamp)

    def add_log_entry(self, time_str, barcode, product_name, is_duplicate=False):
        """Добавление записи в панель логов"""
        # Включаем редактирование
        self.log_text.config(state='normal')

        # Формирование строки лога
        if is_duplicate:
            log_line = f"🔵 [{time_str}] {barcode} — {product_name}\n"
        else:
            log_line = f"✅ [{time_str}] {barcode} — {product_name}\n"

        # Добавление в конец
        self.log_text.insert('end', log_line)

        # Прокрутка вниз
        self.log_text.see('end')

        # Отключаем редактирование
        self.log_text.config(state='disabled')

    def clear_logs(self):
        """Очистка панели логов"""
        if messagebox.askyesno("Очистка логов", "Очистить историю сканирований в панели?"):
            self.log_text.config(state='normal')
            self.log_text.delete('1.0', 'end')
            self.log_text.config(state='disabled')
            self.status_var.set("🗑️ Логи очищены")

    def update_counter_color(self, is_duplicate=False):
        """Обновление цвета и значения счётчика"""
        if is_duplicate:
            # Дубликат - синий цвет, счётчик не меняется
            self.counter_label.config(bg='#3498db')
            self.counter_status_var.set("Дубликат кода")
        else:
            # Новый код - увеличиваем счётчик и чередуем цвета
            self.scan_count += 1
            self.counter_var.set(str(self.scan_count))

            # Чередование цветов: зелёный -> жёлтый -> зелёный...
            if self.counter_color == 'green':
                self.counter_label.config(bg='#e3db15')  # Жёлтый
                self.counter_color = 'yellow'
                self.counter_status_var.set("Новый код")
            else:
                self.counter_label.config(bg='#27ae60')  # Зелёный
                self.counter_color = 'green'
                self.counter_status_var.set("Новый код")

    def reset_counter(self):
        """Сброс счётчика"""
        if messagebox.askyesno("Сброс счётчика", "Сбросить счётчик и очистить историю сканирований?"):
            self.scan_count = 0
            self.scanned_barcodes.clear()
            self.counter_var.set("0")
            self.counter_color = 'green'
            self.counter_label.config(bg='#27ae60')
            self.counter_status_var.set("Счётчик сброшен")
            self.status_var.set("🔄 Счётчик сброшен. Готов к новым сканированиям...")
            self.status_label.config(fg='#27ae60')

            # Также очищаем панель логов
            self.clear_logs()

    def load_product_image(self, image_path):
        """Загрузка и отображение изображения продукта"""
        try:
            if os.path.exists(image_path):
                img = Image.open(image_path)
                img = img.resize((300, 300), Image.Resampling.LANCZOS)
                self.current_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.current_image, text="")
            else:
                self.clear_image()
                self.status_var.set("⚠️ Изображение не найдено")
        except Exception as e:
            self.clear_image()
            self.status_var.set(f"❌ Ошибка загрузки изображения: {str(e)}")

    def clear_image(self):
        """Очистка области изображения"""
        self.image_label.config(image='', text="Изображение отсутствует")
        self.current_image = None

    def log_scan(self, barcode, timestamp):
        """Логирование сканирования в файл"""
        if not self.logging_settings['enabled']:
            return

        try:
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'barcode': barcode,
                'product_name': self.products.get(barcode, {}).get('name', 'Unknown'),
                'is_duplicate': barcode in self.scanned_barcodes,
                'scan_count': self.scan_count
            }

            log_file = self.logging_settings['file']
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        except Exception as e:
            print(f"Ошибка логирования: {e}")

    def on_closing(self):
        """Обработка закрытия приложения"""
        if messagebox.askokcancel("Выход", "Закрыть приложение?"):
            self.reading = False
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.root.destroy()

def main():
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
