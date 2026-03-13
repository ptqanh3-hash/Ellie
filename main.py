from app.database import DatabaseManager
from app.ui.main_window import TaskMNGApp


def main():
    app = TaskMNGApp(DatabaseManager())
    app.mainloop()


if __name__ == "__main__":
    main()

