import threading
from socket import *

lock = threading.Lock()  # 确保 多个线程在共享资源的时候不会出现脏数据
openNum = 0  # 端口开放数量统计
threads = []  # 线程池


def portscanner(host, ports):
    for port in ports:
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.connect((host, port))
            s.close()
        except:
            print(f"{port} open")
            return port


# def main(ip, ports=range(8082,8083)):  # 设置 端口缺省值0-65535
#     setdefaulttimeout(1)
#     for port in ports:
#         t = threading.Thread(target=portscanner, args=(ip, port))
#         threads.append(t)
#         t.start()
#     for t in threads:
#         t.join()
#     print(f"PortScan is Finish ，OpenNum is {openNum}")


if __name__ == '__main__':
    ip = '127.0.0.1'
    # main(ip,[22,101,8080,8000])          # 输入端口扫描
    # main(ip)

    portscanner(ip,ports=range(43000,65535))
