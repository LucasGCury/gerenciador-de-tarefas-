import re
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivy.uix.boxlayout import BoxLayout
import sqlite3


class Database:
    def __init__(self):
        self.connection = sqlite3.connect("task_manager.db")
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
    
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                email TEXT NOT NULL UNIQUE,
                                password TEXT NOT NULL)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT NOT NULL,
                                description TEXT,
                                priority TEXT,
                                due_date TEXT,
                                category TEXT,
                                user_id INTEGER,
                                FOREIGN KEY(user_id) REFERENCES users(id))''')
        self.connection.commit()

    def register_user(self, email, password):
        try:
            self.cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, email, password):
        self.cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        return self.cursor.fetchone()

    def add_task(self, title, description, priority, due_date, category, user_id):
        self.cursor.execute('INSERT INTO tasks (title, description, priority, due_date, category, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                            (title, description, priority, due_date, category, user_id))
        self.connection.commit()

    def get_tasks(self, user_id):
        self.cursor.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()

    def delete_task(self, task_id):
        self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.connection.commit()

class TaskManagerApp(MDApp):
    db = None
    dialog = None
    current_user_id = None

    def build(self):
        self.db = Database()
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        screen_manager = ScreenManager()
        screen_manager.add_widget(LoginScreen(name="login"))
        screen_manager.add_widget(RegisterScreen(name="register"))
        screen_manager.add_widget(TaskScreen(name="tasks"))
        return screen_manager

    def is_valid_email(self, email):

        pattern = r'^[\w\.-]+@(?:gmail|hotmail|outlook|yahoo)\.com$'
        return re.match(pattern, email) is not None

    def register(self, email, password, confirm_password):
        if not self.is_valid_email(email):
            self.show_alert_dialog("Erro", "Insira um e-mail válido, como @gmail.com ou @hotmail.com.")
        elif password != confirm_password:
            self.show_alert_dialog("Erro", "As senhas não coincidem.")
        elif self.db.register_user(email, password):
            self.show_alert_dialog("Sucesso", "Usuário registrado com sucesso!")
            self.root.current = 'login'
        else:
            self.show_alert_dialog("Erro", "Este email já está registrado.")

    def login(self, email, password):
        user = self.db.login_user(email, password)
        if user:
            self.current_user_id = user[0]
            self.root.current = 'tasks'
            self.load_tasks()
        else:
            self.show_alert_dialog("Erro", "Login inválido")

    def load_tasks(self):
        tasks = self.db.get_tasks(self.current_user_id)
        task_list = self.root.get_screen("tasks").ids.task_list
        task_list.clear_widgets()
        for task in tasks:
            task_btn = MDRaisedButton(
                text=f"[{task[3]}] {task[1]} - {task[2]}",
                on_release=lambda x, task_id=task[0]: self.show_manage_task_dialog(task_id, task[1], task[2])
            )
            task_list.add_widget(task_btn)

    def show_manage_task_dialog(self, task_id, title, description):
        self.dialog = MDDialog(
            title="Gerenciar Tarefa",
            type="custom",
            content_cls=BoxLayout(
                orientation="vertical",
                spacing="12dp",
                padding="10dp",
                size_hint_y=None,
                height="180dp",
                children=[
                    MDTextField(
                        text=title,
                        hint_text="Título da Tarefa"
                    ),
                    MDTextField(
                        text=description,
                        hint_text="Descrição da Tarefa"
                    ),
                ]
            ),
            buttons=[
                MDRaisedButton(
                    text="DELETAR",
                    on_release=lambda x: self.delete_task(task_id)
                ),
                MDRaisedButton(
                    text="SALVAR",
                    on_release=lambda x: self.update_task(
                        task_id,
                        self.dialog.content_cls.children[1].text,
                        self.dialog.content_cls.children[0].text
                    )
                ),
            ],
        )
        self.dialog.open()

    def update_task(self, task_id, title, description):
        if title.strip():
            self.db.cursor.execute(
                'UPDATE tasks SET title = ?, description = ? WHERE id = ?',
                (title, description, task_id)
            )
            self.db.connection.commit()
            self.load_tasks()
            self.dialog.dismiss()
        else:
            self.show_alert_dialog("Erro", "O título da tarefa não pode estar vazio.")

    def show_add_task_dialog(self):
        self.dialog = MDDialog(
            title="Nova Tarefa",
            type="custom",
            content_cls=BoxLayout(
                orientation="vertical",
                spacing="12dp",
                padding="10dp",
                size_hint_y=None,
                height="180dp",
                children=[
                    MDTextField(
                        hint_text="Título da Tarefa",
                        multiline=False
                    ),
                    MDTextField(
                        hint_text="Descrição da Tarefa",
                        multiline=True
                    ),
                ]
            ),
            buttons=[
                MDRaisedButton(
                    text="CANCELAR",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="ADICIONAR",
                    on_release=lambda x: self.add_task(
                        self.dialog.content_cls.children[1].text,
                        self.dialog.content_cls.children[0].text
                    )
                ),
            ],
        )
        self.dialog.open()

    def add_task(self, title, description):
        if title.strip():
            self.db.add_task(title, description, "Média", None, "Pessoal", self.current_user_id)
            self.load_tasks()
            self.dialog.dismiss()
        else:
            self.show_alert_dialog("Erro", "O título da tarefa não pode estar vazio.")

    def delete_task(self, task_id):
        self.db.delete_task(task_id)
        self.load_tasks()

    def show_alert_dialog(self, title, text):
        dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDRaisedButton(text="OK", on_release=lambda x: dialog.dismiss())]
            )
        dialog.open()

class LoginScreen(Screen):
    pass

class RegisterScreen(Screen):
    pass

class TaskScreen(Screen):
    pass

kv = '''
<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 10

        MDTextField:
            id: email
            hint_text: "Email"
            icon_right: "email"
            required: True

        MDTextField:
            id: password
            hint_text: "Senha"
            icon_right: "lock"
            password: True
            required: True

        MDRaisedButton:
            text: "Login"
            on_release: app.login(email.text, password.text)

        MDRaisedButton:
            text: "Registrar-se"
            on_release: app.root.current = 'register'

<RegisterScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 10

        MDTextField:
            id: email
            hint_text: "Email"
            icon_right: "email"
            required: True

        MDTextField:
            id: password
            hint_text: "Senha"
            icon_right: "lock"
            password: True
            required: True

        MDTextField:
            id: confirm_password
            hint_text: "Confirme a Senha"
            icon_right: "lock"
            password: True
            required: True

        MDRaisedButton:
            text: "Registrar"
            on_release: app.register(email.text, password.text, confirm_password.text)

        MDRaisedButton:
            text: "Voltar ao Login"
            on_release: app.root.current = 'login'

<TaskScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10

        MDLabel:
            text: "Suas Tarefas"
            halign: "center"
            font_style: "H5"

        ScrollView:
            MDList:
                id: task_list

        MDRaisedButton:
            text: "Adicionar Nova Tarefa"
            pos_hint: {"center_x": 0.5}
            on_release: app.show_add_task_dialog()

        MDRaisedButton:
            text: "Voltar ao Login"
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "login"
'''

Builder.load_string(kv)

if __name__ == "__main__":
    TaskManagerApp().run()
