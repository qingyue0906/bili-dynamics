import threading
import time
import webbrowser
from __a_preview_app import app

def open_browser():
    # 等待服务器启动
    time.sleep(1)
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    # 在子线程中打开浏览器
    threading.Thread(target=open_browser).start()
    # 在主线程中启动Flask应用
    app.run(debug=True)