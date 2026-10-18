# -*- coding: utf-8 -*-
"""python run.py  ->  启动 Web 服务（也可被 gunicorn 以 run:app 引用）"""
from app.web import app, main

if __name__ == "__main__":
    main()
