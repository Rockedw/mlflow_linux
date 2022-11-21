# # import os
# # import threading
# # import time
# # from socket import *
# #
# # lock = threading.Lock()  # 确保 多个线程在共享资源的时候不会出现脏数据
# # openNum = 0  # 端口开放数量统计
# # threads = []  # 线程池
# #
# #
# # def portscanner(host, ports):
# #     for port in ports:
# #         try:
# #             s = socket(AF_INET, SOCK_STREAM)
# #             s.connect((host, port))
# #             s.close()
# #         except:
# #             print(f"{port} open")
# #             return port
# #
# #
# # # def main(ip, ports=range(8082,8083)):  # 设置 端口缺省值0-65535
# # #     setdefaulttimeout(1)
# # #     for port in ports:
# # #         t = threading.Thread(target=portscanner, args=(ip, port))
# # #         threads.append(t)
# # #         t.start()
# # #     for t in threads:
# # #         t.join()
# # #     print(f"PortScan is Finish ，OpenNum is {openNum}")
# #
# #
# # if __name__ == '__main__':
# #     # ip = '127.0.0.1'
# #     # # main(ip,[22,101,8080,8000])          # 输入端口扫描
# #     # # main(ip)
# #     #
# #     # portscanner(ip,ports=range(43000,65535))
# #     cnt = 0
# #     while cnt <= 30:
# #         print(cnt)
# #         cnt += 1
# #         if os.path.exists('/' + 'mlflow_output'):
# #             break
# #         else:
# #             time.sleep(5)
#
# import json
#
# import requests
# from flask import Flask, request
#
# from JsonResponse import JsonResponse
#
# app = Flask(__name__)
#
#
# @app.route('/test', methods=['GET'])
# def test():
#     service_url = 'http://8.130.105.10:59081/predict'
#     data = {'service_url': 'http://127.0.0.1:40000/predict', 'data': '输入一些啥'}
#     response = requests.post(url=service_url, json=json.dumps(data))
#     print(response.text)
#     res = response.text
#     return JsonResponse.success(data=str(res)).to_dict()
#
#
# @app.route('/test2', methods=['GET'])
# def test2():
#     service_url = 'http://8.130.105.10:59083/predict'
#     res = requests.get(url=service_url)
#     return str(res.text)
#
#
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8099)
#
# # project_config = {'modules':{'module1':{'git_path':'gitpath1','model_hdfs_path':'model-hdfs-path1','branch':'branch1'},'module2':{'git_path':'gitpath2','model_hdfs_path':'model-hdfs-path2','branch':'branch2'}}}
# # # 将project_config写入yaml文件
# # import yaml
# # with open('project_config.yaml', 'w') as f:
# #     yaml.dump(project_config, f)
# # # 读取yaml文件
# # with open('project_config.yaml', 'r') as f:
# #     project_config = yaml.load(f, Loader=yaml.FullLoader)
# #     print(project_config)
import json

import requests

from JsonResponse import JsonResponse

service_url = 'http://8.130.105.10:59081/predict'
res = requests.post(url=service_url, json=json.dumps({'data': '哈哈'}))
print(JsonResponse.success(data=res.text).to_dict())
