# -*- coding: utf-8 -*-
"""`python3.12 -m baron` — запуск сервера памяти Baron Munchausen.

Ровно то же, что `python3.12 -m mnemos`, только под новым именем и без
предупреждения о переименовании.
"""

from mnemos.__main__ import main

if __name__ == "__main__":
    main(prog="baron")
