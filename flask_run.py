# -*- coding: UTF-8 -*-
import datetime
import logging
import signal
import time

import requests
import yaml
from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import pymysql
import os
from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.utils import secure_filename

from config import Config
from util_methods import cmd, download_directory, rmtree, scan_dir, portscanner, kill_port, upload_model, create_dir, \
    download_dir_from_hdfs
import shutil
import json
from JsonResponse import JsonResponse
import threading
import time
from flask_apscheduler import APScheduler
from hdfs.client import Client

pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app, resources=r'/*')
db = SQLAlchemy(app)

app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
lock = threading.Lock()
service_lock = threading.Lock()
create_version_lock = threading.Lock()
bucket_name = Config.bucket_name
access_key = Config.access_key
secret_key = Config.secret_key
endpoint_url = Config.endpoint_url
git_url = Config.git_url
service_port_dict = {}
service_url_dict = {}
service_process_pid_dict = {}
already_used_ports = []
env_dict = []
service_obj_dict = {}
creating_env_dict = {}

hdfs_client = Client(Config.HDFS_URL)


class Repository(db.Model):
    """
    代码仓库
    """
    __tablename__ = 'repository'
    __bind_key__ = 'gitea'
    id = db.Column(db.Integer, primary_key=True, index=True)
    owner_id = db.Column('owner_id', db.Integer)
    owner_name = db.Column('owner_name', db.String(255))
    lower_name = db.Column('lower_name', db.String(255))
    repo_name = db.Column('name', db.String(255))
    update_time = db.Column('updated_unix', db.Integer)


# class Model(db.Model):
#     """
#     模型
#     """
#     __tablename__ = 'model_versions'
#     __bind_key__ = 'mlflow'
#     name = db.Column('name', db.String(256), primary_key=True)
#     version = db.Column('version', db.Integer, primary_key=True)
#     source = db.Column('source', db.String(255))
#     create_time = db.Column('creation_time', db.Integer)

class Model(db.Model):
    __tablename__ = 'model'
    __bind_key__ = 'mlflow'
    id = db.Column(db.Integer, primary_key=True, index=True)
    model_name = db.Column('name', db.String(255))
    version = db.Column('version', db.Integer)
    model_hdfs_path = db.Column('hdfs_path', db.String(255))
    update_time = db.Column('update_time', db.Integer)


class Task(db.Model):
    """
    任务
    """
    __tablename__ = 'task'
    __bind_key__ = 'mlflow'
    id = db.Column(db.Integer, primary_key=True, index=True)
    value = db.Column('value', db.String(255))


class TaskRelation(db.Model):
    """
    代码仓库和任务的关系
    """
    __tablename__ = 'task_relation'
    __bind_key__ = 'mlflow'
    id = db.Column(db.Integer, primary_key=True, index=True)
    task_id = db.Column(db.Integer)
    repo_id = db.Column(db.Integer)


# class Project(db.Model):
#     __tablename__ = 'project'
#     __bind_key__ = 'mlflow'
#     id = db.Column('id', db.Integer, primary_key=True, index=True)
#     repo_id = db.Column('repo_id', db.Integer)
#     branch_name = db.Column('branch_name', db.String(255))
#
#
# class ProjectRelation(db.Model):
#     __tablename__ = 'project_relation'
#     __bind_key__ = 'mlflow'
#     id = db.Column('id', db.Integer, primary_key=True, index=True)
#     project_id = db.Column('project_id', db.Integer)
#     model_name = db.Column('model_name', db.String(255))
#     model_version = db.Column('model_version', db.Integer)

class Project(db.Model):
    __tablename__ = 'project'
    __bind_key__ = 'mlflow'
    id = db.Column('id', db.Integer, primary_key=True, index=True)
    hdfs_path = db.Column('hdfs_path', db.String(255))
    update_time = db.Column('update_time', db.Integer)
    version = db.Column('version', db.Integer)


class ProjectRelation(db.Model):
    __tablename__ = 'project_relation'
    __bind_key__ = 'mlflow'
    id = db.Column('id', db.Integer, primary_key=True, index=True)
    project_id = db.Column('project_id', db.Integer)
    module_id = db.Column('module_id', db.Integer)


class Module(db.Model):
    __tablename__ = 'module'
    __bind_key__ = 'mlflow'
    id = db.Column('id', db.Integer, primary_key=True, index=True)
    repo_id = db.Column('repo_id', db.Integer)
    branch_name = db.Column('branch_name', db.String(255))
    model_name = db.Column('model_name', db.String(255))
    model_hdfs_path = db.Column('model_hdfs_path', db.String(255))
    model_version = db.Column('model_version', db.Integer)
    model_update_time = db.Column('model_update_time', db.Integer)


#
# @app.errorhandler(Exception)
# def error_handler(e):
#     #     """
#     #     全局异常捕获，也相当于一个视图函数
#     #     """
#     #     print(str(e))
#     return JsonResponse.error(data=str(e)).to_dict()


def get_project_relation_by_pid(project_id):
    try:
        relations = ProjectRelation.query.filter_by(project_id=project_id).all()
    except:
        return None
    res = {'models': [], 'versions': []}
    for relation in relations:
        res['models'].append(relation.model_name)
        res['versions'].append(relation.model_version)
    return res


def get_model_source(name, version):
    source = Model.query.filter_by(name=name, version=int(version)).all()
    if len(source) > 0:
        print(source[0].source)
        return source[0].source
    return None


# @app.route('/query_all_project', methods=['GET'])
# def query_all_project():
#     print('get_all_project')
#     try:
#         projects = Project.query.all()
#     except Exception as e:
#         projects = []
#     res = []
#     index = 0
#     for project in projects:
#         repo = Repository.query.filter_by(id=project.repo_id).all()[0]
#         repo_name = repo.repo_name
#         repo_owner = repo.owner_name
#         update_time = repo.update_time
#         temp = get_project_relation_by_pid(project.id)
#         res.append(
#             {'index': index, 'project_id': project.id, 'repo_owner': repo_owner, 'repo_name': repo_name,
#              'branch_name': project.branch_name, 'model_names': temp['models'],
#              'model_versions': temp['versions'], 'update_time': update_time})
#         index += 1
#         # print(res)
#     return JsonResponse.success(data=res).to_dict()


@app.route('/query_all_project', methods=['GET'])
def query_all_project():
    print('get_all_project')
    try:
        projects = Project.query.all()
    except Exception as e:
        projects = []
    res = []
    module_ids = []
    index = 0
    for project in projects:
        project_relations = ProjectRelation.query.filter_by(project_id=project.id).all()
        for project_relation in project_relations:
            module_ids.append(project_relation.module_id)
        res.append(
            {'index': index, 'project_id': project.id, 'project_hdfs_path': project.hdfs_path,
             'project_version': project.version, 'module_ids': module_ids})
        index += 1
    print(res)
    return JsonResponse.success(data=res).to_dict()


@app.route('/query_all_owner')
def query_all_owner():
    repos = Repository.query.all()
    owners = []
    for repo in repos:
        if repo.owner_name not in owners:
            owners.append(repo.owner_name)
    return JsonResponse.success(data=owners).to_dict()


@app.route('/query_repo_by_owner', methods=['POST'])
def query_repo_by_owner():
    data = request.json
    owner = data.get('owner_name')
    repos = Repository.query.filter_by(owner_name=owner).all()
    res = []
    for repo in repos:
        # 转为日期格式
        update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(repo.update_time / 1000))
        res.append(
            {'id': repo.id, 'owner_name': repo.owner_name, 'repo_name': repo.repo_name, 'lower_name': repo.lower_name,
             'update_time': repo.update_time})
    return JsonResponse.success(data=res).to_dict()


@app.route('/query_all_task', methods=['GET'])
def query_all_task():
    """
    获取所有的任务
    :return:
    """
    print('query all task')
    try:
        tasks = Task.query.all()
    except Exception as e:
        tasks = []
    res = []
    for task in tasks:
        res.append({'id': task.id, 'value': task.value})
    return JsonResponse.success(data=res).to_dict()


@app.route('/query_repo_by_task_id', methods=['POST'])
def query_repo_by_task_id():
    """
    使用任务id查血对应的代码仓库
    :return:
    """
    task_id = request.json.get('task_id')
    res = []
    task_relations = TaskRelation.query.filter_by(task_id=task_id).all()
    for task_relation in task_relations:
        temp = Repository.query.filter_by(id=task_relation.repo_id).all()
        if len(temp) > 0:
            res.append({'id': temp[0].id, 'owner_name': temp[0].owner_name, 'repo_name': temp[0].repo_name})
    print(res)
    return JsonResponse.success(data=res).to_dict()


@app.route('/query_project_by_task_id', methods=['POST'])
def query_project_by_task_id():
    task_id = request.json.get('task_id')
    projects = []
    task_id = request.json.get('task_id')
    res = []
    task_relations = TaskRelation.query.filter_by(task_id=task_id).all()
    for task_relation in task_relations:
        temp = db.session.query(Project).join(Repository).filter(Project.repo_id == Repository.id).filter(
            Repository.id == task_relation.repo_id).all()
        projects.append(temp)

    for project in projects:
        repo = Repository.query.filter_by(id=project.repo_id).all()[0]
        repo_name = repo.repo_name
        repo_owner = repo.repo_owner
        temp = get_project_relation_by_pid(project.id)
        res.append(
            {'project_id': project.id, 'repo_owner': repo_owner, 'repo_name': repo_name,
             'branch_name': project.branch_name, 'model_names': temp['models'],
             'model_versions': temp['versions']})
    return res


def query_branches_by_repo_name_and_owner(owner_name, repo_name, update_time):
    """
    使用 仓库拥有者名字、仓库名称、仓库的更新时间查血该仓库的所有分支
    :param owner_name:
    :param repo_name:
    :param update_time:
    :return:
    """
    repo_url = git_url + owner_name + '/' + repo_name + '.git'
    print(repo_url)
    path = '/tmp/repos/real/' + owner_name + '/' + repo_name
    repo = None
    time = path + '/' + str(update_time) + '.time'
    if os.path.exists(path):
        if not os.path.exists(time):
            rmtree(path)
            repo = Repo.clone_from(url=repo_url, to_path=path)
            with open(time, 'a') as f:
                f.write('something')
            f.close()
        else:
            repo = Repo(path)
    else:
        repo = Repo.clone_from(url=repo_url, to_path=path)
        with open(time, 'a') as f:
            f.write('something')
        f.close()
    remote_branches = []
    for ref in repo.git.branch('-r').split('\n'):
        remote_branches.append(ref)
    print(remote_branches)
    temp_path = '/tmp/repos/temp/' + owner_name + '/' + repo_name
    create_version_lock.acquire(blocking=True, timeout=-1)
    try:
        temp_version = str(len(os.listdir(temp_path)))
    except Exception as e:
        print(e)
        temp_version = '0'

    to_path = temp_path + '/' + temp_version + '/' + repo_name
    shutil.copytree(path, to_path)
    create_version_lock.release()

    return remote_branches, temp_version, to_path


@app.route('/query_all_repo')
def query_all_repo():
    """
    查血所有代码仓库
    :return:
    """
    repos = Repository.query.all()
    res = []
    for repo in repos:
        # 时间戳转换成日期
        update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(repo.update_time / 1000))
        res.append(
            {'id': repo.id, 'owner_name': repo.owner_name, 'repo_name': repo.repo_name, 'lower_name': repo.lower_name,
             'update_time': update_time})
    return JsonResponse.success(data=res).to_dict()


@app.route('/query_branches_by_owner_and_name', methods=['POST'])
def query_branches_by_owner_and_name():
    """
    查询代码仓库的所有分支
    :return:
    """
    print('query_branches_by_owner_and_name excute')
    # return os.getcwd()
    data = request.json
    repo_name = data.get('repo_name')
    owner_name = data.get('owner_name')
    update_time = data.get('update_time')
    branches, temp_version, _ = query_branches_by_repo_name_and_owner(owner_name=owner_name,
                                                                      repo_name=repo_name,
                                                                      update_time=update_time
                                                                      )
    print('branches : ' + str(branches))
    print('temp_version : ' + temp_version)
    if len(branches) > 0:
        return JsonResponse.success(data={'branches': branches, 'temp_version': temp_version}).to_dict()
    else:
        return JsonResponse.error().to_dict()


@app.route('/query_file_by_owner_and_name_and_branch', methods=['POST'])
def query_file_by_owner_and_name_and_branch():
    """
    查血代码仓库特定分支下的所有文件
    :return:
    """
    data_json = request.json
    owner_name = data_json.get('owner_name')
    repo_name = data_json.get('repo_name')
    branch_name = data_json.get('branch_name')
    temp_version = data_json.get('temp_version')
    print('abcded' + str(len(temp_version)))
    if len(temp_version) > 0:
        path = '/tmp/repos/' + owner_name + '/' + repo_name + '/' + temp_version + '/' + repo_name
    else:
        path = '/tmp/repos/' + owner_name + '/' + repo_name
    if branch_name is not None:
        if not os.path.exists(path):
            return JsonResponse.error(data='There is no git directory').to_dict()
        cwd = os.getcwd()
        command = 'cd ' + cwd + ' && ' + 'cd ' + path + ' && ' + 'git checkout ' + branch_name
        print(command)
        cmd(command)
    files = scan_dir(path)
    # rmtree(path)
    return JsonResponse.success(data=[files]).to_dict()


# class Model(db.Model):
#     __tablename__ = 'model'
#     __bind_key__ = 'mlflow'
#     id = db.Column(db.Integer, primary_key=True, index=True)
#     model_name = db.Column('model_name', db.String(255))
#     version = db.Column('version', db.Integer)
#     model_hdfs_path = db.Column('model_hdfs_path', db.String(255))
#     update_time = db.Column('update_time', db.Integer)
@app.route('/query_all_model', methods=['GET'])
def query_all_model():
    """
    查询所有模型
    :return:
    """
    # model_list = Model.query.all()
    # models = {}
    # for model in model_list:
    #     if model.model_name not in models:
    #         models[model.model_name] = [
    #             {'version': model.version, 'hdfs_path': model.model_hdfs_path, 'update_time': model.update_time}]
    #     else:
    #         models[model.model_name].append(
    #             {'version': model.version, 'hdfs_path': model.model_hdfs_path, 'update_time': model.update_time})
    # return JsonResponse.success(data=models).to_dict()
    models = Model.query.all()
    res = []
    for model in models:
        # 时间戳转换成日期
        update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(model.update_time / 1000))
        res.append(
            {'id': model.id, 'model_name': model.model_name, 'version': model.version,
             'model_hdfs_path': model.model_hdfs_path, 'update_time': update_time})
    return JsonResponse.success(data=res).to_dict()


@app.route('/download_model_by_name_and_version', methods=['POST'])
def download_model_by_name_and_version():
    """
    通过模型名称和版本号下载对应模型到服务器
    :return:
    """
    model_name = request.json.get('model_name')
    model_version = request.json.get('model_version')
    model = Model.query.filter_by(name=model_name, version=model_version).all()
    if len(model) <= 0:
        return JsonResponse.error().to_dict()
    model_source: str = model[0].source
    path = model_source.split('//' + bucket_name + '/')[1] + '/model'
    download_directory(download_path=path)

    return str(os.path.exists(path))


@app.route('/change_branch_by_branch_name', methods=['POST'])
def change_branch_by_name():
    """
    通过分支名称更改代码仓库的分支
    :return:
    """
    data = request.json
    owner_name = data.get('owner_name')
    repo_name = data.get('repo_name')
    branch_name = data.get('branch_name')
    temp_version = data.get('temp_version')
    path = '/tmp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
    if not os.path.exists(path):
        return JsonResponse.error(data='There is no git directory').to_dict()
    cwd = os.getcwd()
    command = 'cd ' + cwd + ' && ' + 'cd ' + path + ' && ' + 'git checkout ' + branch_name
    print(command)
    cmd(command)
    return JsonResponse.success(data=os.getcwd()).to_dict()


@app.route('/run_mlflow_project', methods=['POST'])
def run_mlflow_project():
    """
    运行mlflow项目
    :return:
    """
    print('run run run run run run run')
    data = request.json
    owner_name = data.get('owner_name')
    repo_name = data.get('repo_name')
    branch_name = data.get('branch_name')
    update_time = data.get('update_time')
    temp_version = data.get('temp_version')
    input_text = data.get('input_text')
    model_names: list = data.get('model_names')
    s3_models: list = data.get('s3_models')

    repo_url = git_url + owner_name + '/' + repo_name + '.git'
    version = '/tmp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
    path = version + '/' + repo_name
    # print('path : ' + path)
    if not os.path.exists(path):
        print('nothing')
        return JsonResponse.error(data='There is no git directory').to_dict()
    cwd = os.getcwd()
    if not os.path.exists(path + '/.git'):
        print(path + '/.git 不存在')
    config_json = {}
    model_local_paths = []
    param = ''
    for i in range(0, len(model_names)):
        local_path = download_directory(download_path=get_model_source(s3_models[i][0], version=s3_models[i][1]))
        model_local_paths.append(local_path)
        config_json[model_names[i]] = local_path
    input_text = data.get('input_text')

    with open(path + '/mlflow_model_config.json', 'w') as f:
        f.write(json.dumps(config_json))
    f.close()
    command = 'cd ' + cwd + ' && ' + \
              'cd ' + path + ' && ' + \
              'rm -rf .git &&' + \
              'cd ' + cwd + ' && ' + \
              'mlflow run ' + path + ' -P config=./mlflow_model_config.json -P input=' + input_text + ' --env-manager=local'
    # command = 'mlflow run ' + repo_url + ' --version ' + branch_name
    print(command)
    cmd(command)
    with open(path + '/' + 'mlflow_output') as f:
        res = f.readlines()
    # rmtree(version)

    return JsonResponse.success(data=res).to_dict()


@app.route('/run_module2', methods=['POST'])
def run_module2():
    data = request.json
    owner_name = data.get('repo_owner')
    repo_name = data.get('repo_name')
    branch_name = data.get('branch_name')
    update_time = data.get('repo_update_time')
    model_name: str = data.get('model_name')
    model_version: int = data.get('model_version')

    print(data)
    key = repo_name + '/' + branch_name
    key = key + '/' + model_name + '/' + str(model_version)
    print('获取service_lock')
    service_lock.acquire(blocking=True, timeout=60.0)
    if key in service_url_dict and key in service_port_dict:
        service_port_dict[key][1] = int(time.time())
        service_lock.release()
        print('释放service_lock')
        return JsonResponse.success(data=service_url_dict[key]).to_dict()
    service_lock.release()
    print('释放service_lock')
    branches, temp_version, path = query_branches_by_repo_name_and_owner(owner_name=owner_name,
                                                                         repo_name=repo_name,
                                                                         update_time=update_time
                                                                         )
    print('branches:' + str(branches))
    version = '/tmp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
    if not os.path.exists(version):
        return JsonResponse.error(data='没有对应的代码仓库').to_dict()
    cwd = os.getcwd()
    command = 'cd ' + path + ' && ' + 'git checkout ' + branch_name
    cmd(command)
    config_json = {}
    model_local_paths = []
    port = portscanner(already_used_ports=already_used_ports, lock=lock)
    local_path = download_directory(download_path=get_model_source(model_name, version=model_version))
    model_local_paths.append(local_path)
    config_json[model_name] = local_path
    config_json['port'] = port
    with open(path + '/mlflow_model_config.json', 'w') as f:
        f.write(json.dumps(config_json))
    f.close()
    command = 'cd ' + cwd + ' && ' + \
              'cd ' + path + ' && ' + \
              'rm -rf .git &&' + \
              'cd ' + cwd + ' && ' + \
              'mlflow run ' + path + ' -P config=mlflow_model_config.json --env-manager=local'
    # command = 'mlflow run ' + repo_url + ' --version ' + branch_name
    print(command)
    subp = cmd(command)
    # cmd(command)
    service_url = ''
    cnt = 0
    while cnt <= 30:
        print(cnt)
        cnt += 1
        if os.path.exists(path + '/' + 'mlflow_output'):
            break
        else:
            time.sleep(5)
    with open(path + '/' + 'mlflow_output') as f:
        print('获取service_lock')
        service_lock.acquire()
        try:
            service_url = f.readline()
            service_url_dict[key] = service_url
            service_process_pid_dict[key] = subp.pid
            service_port_dict[key] = [port, int(time.time())]
        finally:
            service_lock.release()
            print('释放service_lock')
    f.close()
    return JsonResponse.success(data=service_url).to_dict()


# @app.route('/load_model', methods=['POST'])
# def load_model():
#     data = request.json
#     owner_name = data.get('repo_owner')
#     repo_name = data.get('repo_name')
#     branch_name = data.get('branch_name')
#     update_time = data.get('update_time')
#     model_names: list = data.get('model_names')
#     model_versions: list = data.get('model_versions')
#     print(data)
#     key = repo_name + '/' + branch_name
#     for i in range(0, len(model_names)):
#         key = key + '/' + model_names[i] + '/' + str(model_versions[i])
#     service_lock.acquire(blocking=True, timeout=60.0)
#     if key in service_url_dict and key in service_port_dict:
#         service_port_dict[key][1] = int(time.time())
#         service_lock.release()
#         return JsonResponse.success(data=service_url_dict[key]).to_dict()
#     service_lock.release()
#     branches, temp_version = query_branches_by_repo_name_and_owner(owner_name=owner_name,
#                                                                    repo_name=repo_name,
#                                                                    update_time=update_time
#                                                                    )
#     print('branches:' + str(branches))
#     version = './tmp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
#     if not os.path.exists(version):
#         return JsonResponse.error(data='没有对应的代码仓库').to_dict()
#     cwd = os.getcwd()
#     command = 'cd ' + cwd + ' && ' + 'cd ' + version + '/' + repo_name + ' && ' + 'git checkout ' + branch_name
#     cmd(command)
#     config_json = {}
#     model_local_paths = []
#     port = portscanner(already_used_ports=already_used_ports, lock=lock)
#     path = version + '/' + repo_name
#     for i in range(0, len(model_names)):
#         local_path = download_directory(download_path=get_model_source(model_names[i], version=model_versions[i]))
#         model_local_paths.append(local_path)
#         config_json[model_names[i]] = local_path
#         config_json['port'] = port
#     with open(path + '/mlflow_model_config.json', 'w') as f:
#         f.write(json.dumps(config_json))
#     f.close()
#     command = 'cd ' + cwd + ' && ' + \
#               'cd ' + path + ' && ' + \
#               'rm -rf .git &&' + \
#               'cd ' + cwd + ' && ' + \
#               'mlflow run ' + path + ' -P config=mlflow_model_config.json --env-manager=local'
#     # command = 'mlflow run ' + repo_url + ' --version ' + branch_name
#     print(command)
#     pid = cmd(command)
#     # cmd(command)
#     service_url = ''
#     cnt = 0
#     while cnt <= 30:
#         print(cnt)
#         cnt += 1
#         if os.path.exists(path + '/' + 'mlflow_output'):
#             break
#         else:
#             time.sleep(5)
#     with open(path + '/' + 'mlflow_output') as f:
#         service_lock.acquire()
#         try:
#             service_url = f.readline()
#             service_url_dict[key] = service_url
#             service_process_pid_dict[key] = pid
#             service_port_dict[key] = [port, int(time.time())]
#         finally:
#             service_lock.release()
#     f.close()
#     return JsonResponse.success(data=service_url).to_dict()


# @app.route('/create_project', methods=['POST'])
# def create_project():
#     data = request.json
#     owner_name = data.get('owner_name')
#     repo_name = data.get('repo_name')
#     branch_name = data.get('branch_name')
#     model_list = data.get('model_list')
#     repo = Repository.query.filter_by(owner_name=owner_name, repo_name=repo_name).first()
#     repo_id = repo.id
#     project = Project(repo_id=repo_id, branch_name=branch_name)
#     db.session.add(project)
#     db.session.flush()
#     project_id = project.id
#     for model in model_list:
#         project_relation = ProjectRelation(project_id=project_id, model_name=model[0], model_version=int(model[1]))
#         db.session.add(project_relation)
#     try:
#         db.session.commit()
#         if project_id not in env_dict:
#             env_dict.append(project_id)
#         return JsonResponse.success(data='success').to_dict()
#     except Exception as e:
#         print(e)
#         db.session.rollback()
#         return JsonResponse.error().to_dict()

@app.route('/create_project', methods=['POST'])
def create_project():
    data = request.json
    hdfs_path = data.get('project_hdfs_path')
    print('hdfs_path:' + hdfs_path)
    if len(hdfs_path) <= 0 or not hdfs_client.status(hdfs_path=hdfs_path)['type'] == 'DIRECTORY':
        return JsonResponse.error(data='hdfs路径不存在').to_dict()
    update_time: int = hdfs_client.status(hdfs_path=hdfs_path)['modificationTime']
    saved_path = '/tmp/projects/' + hdfs_path.split('/')[-1] + '/' + str(update_time)
    print('saved_path:' + saved_path)
    if not os.path.exists(saved_path):
        download_dir_from_hdfs(client=hdfs_client, hdfs_path=hdfs_path, local_path=saved_path)
    if os.path.exists(saved_path + '/.git'):
        rmtree(saved_path + '/.git')
    with open(saved_path + '/config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    f.close()
    modules: dict = config['modules']
    print('modules:' + str(modules))
    module_id_list = []
    for module in modules.values():
        git_path = module['git_path']
        branch = module['branch']
        model_hdfs_path = module['model_hdfs_path']
        model_update_time = hdfs_client.status(hdfs_path=model_hdfs_path)['modificationTime']
        repo_name = git_path.split('/')[-1]
        repo_owner = git_path.split('/')[-2]
        repo = Repository.query.filter_by(owner_name=repo_owner, repo_name=repo_name).first()
        if repo is None:
            return JsonResponse.error(data='仓库不存在').to_dict()
        repo_id = repo.id
        version = create_update_model(model_hdfs_path=model_hdfs_path, update_time=model_update_time)
        if version == -1:
            return JsonResponse.error(data='模型不存在').to_dict()
        module_id = create_module(repo_id=repo_id, branch_name=branch, model_hdfs_path=model_hdfs_path,
                                  model_update_time=model_update_time, model_version=version)
        if module_id == -1:
            return JsonResponse.error(data='module创建失败').to_dict()
        else:
            module_id_list.append(module_id)
    project = Project.query.filter_by(hdfs_path=hdfs_path).order_by(Project.version.desc()).first()
    db.session.flush()
    if project is None:
        temp_project = Project(hdfs_path=hdfs_path, update_time=update_time, version=1)
        db.session.add(temp_project)
    else:
        project_version = project.version + 1
        temp_project = Project(hdfs_path=hdfs_path, update_time=update_time, version=project_version)
        db.session.add(temp_project)
    db.session.flush()
    for module_id in module_id_list:
        project_relation = ProjectRelation(project_id=temp_project.id, module_id=module_id)
        db.session.add(project_relation)
        db.session.flush()
    try:
        db.session.commit()
        return JsonResponse.success(data='success').to_dict()
    except Exception as e:
        print(e)
        db.session.rollback()
        return JsonResponse.error(e).to_dict()


def create_env(module_id):
    try:
        creating_env_dict[module_id] = True
        module = Module.query.filter_by(id=module_id).first()
        if module is None:
            return JsonResponse.error(data='module不存在').to_dict()
        repo_id = module.repo_id
        repo = Repository.query.filter_by(id=repo_id).first()
        if repo is None:
            return JsonResponse.error(data='repo不存在').to_dict()
        repo_owner = repo.owner_name
        repo_name = repo.repo_name
        repo_update_time = repo.update_time
        branch_name = module.branch_name
        repo_url = git_url + repo_owner + '/' + repo_name + '.git'
        print(repo_url)
        saved_path = '/tmp/repos/create_env/' + repo_owner + '/' + repo_name + '/' + branch_name + '/' + str(
            repo_update_time)
        if os.path.exists(saved_path):
            if os.path.exists(saved_path + '/success'):
                return JsonResponse.success(data='success').to_dict()
            else:
                rmtree(saved_path)
        repo = Repo.clone_from(url=repo_url, to_path=saved_path)
        repo.git.checkout(branch_name)
        if os.path.exists(saved_path + '/.git'):
            rmtree(saved_path + '/.git')
        if not os.path.exists(saved_path + '/MLproject'):
            return JsonResponse.error(data='MLproject不存在').to_dict()
        with open(saved_path + '/MLproject') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        f.close()
        conda_env = config['conda_env']
        if conda_env is None:
            return JsonResponse.error(data='conda.yaml不存在').to_dict()
        os.remove(saved_path + '/MLproject')
        with open(saved_path + '/write_hello_world.py', 'w') as f:
            f.write('with open("success.txt", "w") as f:\n')
            f.write('    f.write("hello world")\n')
            f.write('    f.close()')
        f.close()
        # 写yaml文件
        with open(saved_path + '/MLproject', 'w') as f:
            f.write('name: hello_world\n')
            f.write('conda_env: ' + conda_env + '\n')
            f.write('entry_points:\n')
            f.write('  main:\n')
            f.write('    command: "python write_hello_world.py"\n')
        f.close()
        subp = cmd('cd ' + saved_path + ' && mlflow run .')
        subp.wait()
        # 输出子进程信息
        print(subp.stdout.read())
        print(subp.stderr.read())
        if os.path.exists(saved_path + '/success.txt'):
            return JsonResponse.success(data='success').to_dict()
        else:
            return JsonResponse.error(data='创建环境失败,请检查conda文件').to_dict()
    except Exception as e:
        print(e)
        return JsonResponse.error(data=e).to_dict()
    finally:
        del creating_env_dict[module_id]


@app.route('/create_env_by_module_id', methods=['POST'])
def create_env_by_module_id():
    data = request.json
    module_id = data.get('module_id')
    return create_env(module_id)


# @app.route('/create_module_env_by_id')
# def create_module_env_by_id():
#     data = request.json
#     module_id = data.get('module_id')
#     module = Module.query.filter_by(id=module_id).first()
#     if module is None:
#         return JsonResponse.error(data='没有对应的module').to_dict()
#     repo_id = module.repo_id
#     repo = Repository.query.filter_by(id=repo_id).first()
#     if repo is None:
#         return JsonResponse.error(data='没有对应的repo').to_dict()
#     repo_name = repo.name
#     repo_owner = repo.owner
#     branch_name = module.branch_name
#     model_hdfs_path = module.model_hdfs_path
#     model_update_time = module.model_update_time
#     model_version = module.model_version
#     model_name = model_hdfs_path.split('/')[-1]
#     return create_env(module_id)


def create_update_model(model_hdfs_path: str, update_time):
    print('create_update_model')
    model_name = model_hdfs_path.split('/')[-1]
    saved_model_path = '/tmp/models/' + model_name + '/' + str(update_time)
    model = Model.query.filter_by(model_hdfs_path=model_hdfs_path).order_by(Model.version.desc()).first()
    if model is not None:
        next_version = model.version + 1
    else:
        next_version = 1
    model2 = Model.query.filter_by(model_hdfs_path=model_hdfs_path, update_time=update_time).first()
    # 文件夹不存在或者文件夹为空
    if not os.path.exists(saved_model_path) or len(os.listdir(saved_model_path)) == 0:
        os.makedirs(saved_model_path)
        print('下载模型')
        try:
            download_dir_from_hdfs(client=hdfs_client, hdfs_path=model_hdfs_path, local_path=saved_model_path)
        except Exception as e:
            print(e)
            print('下载失败')
    if model2 is None:
        db.session.add(Model(model_name=model_name, model_hdfs_path=model_hdfs_path, version=next_version,
                             update_time=update_time))
    else:
        print('该模型已存在')
        return model2.version
    db.session.flush()
    try:
        db.session.commit()
        return next_version
    except:
        db.session.rollback()
        return -1


def create_module(repo_id, branch_name, model_hdfs_path, model_update_time, model_version):
    print('create_module')
    module = Module.query.filter_by(repo_id=repo_id, branch_name=branch_name,
                                    model_hdfs_path=model_hdfs_path,
                                    model_update_time=model_update_time,
                                    model_version=model_version).first()

    if module is not None:
        return module.id
    model = Model.query.filter_by(model_hdfs_path=model_hdfs_path, update_time=model_update_time).first()

    module2 = Module(repo_id=repo_id, branch_name=branch_name, model_name=model.model_name,
                     model_hdfs_path=model_hdfs_path,
                     model_update_time=model_update_time, model_version=model_version)
    db.session.add(module2)

    # db.session.add(
    #     Module(repo_id=repo_id, branch_name=branch_name, model_name=model.model_name, model_hdfs_path=model_hdfs_path,
    #            model_update_time=model_update_time, model_version=model_version))
    db.session.flush()
    try:
        db.session.commit()
        return module2.id
    except Exception as e:
        db.session.rollback()
        print(e)
        return -1


@app.route('/create_module', methods=['POST'])
def create_module2():
    data = request.json
    config_hdfs_path = data.get('config_hdfs_path')
    print('config_hdfs_path is ' + config_hdfs_path)
    try:
        hdfs_client.status(hdfs_path=config_hdfs_path, strict=False)['modificationTime']
    except Exception as e:
        print(e)
        return JsonResponse.error(data='没有对应的配置文件').to_dict()
    try:
        local_file_path = '/tmp/module/config/' + config_hdfs_path
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        create_dir(local_file_path)
        print('local_path is ' + local_file_path)
        hdfs_client.download(hdfs_path=config_hdfs_path, local_path=local_file_path)
        # 读取yaml文件中的hdfs_path和git_path
        with open(local_file_path, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        f.close()
        model_hdfs_path = config['model_hdfs_path']
        print('model_hdfs_path is ' + model_hdfs_path)
        git_path = config['git_path']
        print('git_path is ' + git_path)
        branch_name = config['branch']
        print('branch_name is ' + branch_name)
        # 从git_path中获取repo_name和branch_name
        repo_name = git_path.split('/')[-1]
        print('repo_name is ' + repo_name)
        owner_name = git_path.split('/')[-2]
        print('owner_name is ' + owner_name)
        try:
            update_time = hdfs_client.status(hdfs_path=model_hdfs_path, strict=False)['modificationTime']
            version = create_update_model(model_hdfs_path=model_hdfs_path, update_time=update_time)
            repo = Repository.query.filter_by(repo_name=repo_name, owner_name=owner_name).first()
            if repo is None:
                return JsonResponse.error(data='没有对应的代码仓库').to_dict()
            repo_id = repo.id
            if version != -1:
                module_id = create_module(repo_id=repo_id, branch_name=branch_name, model_hdfs_path=model_hdfs_path,
                                          model_update_time=update_time, model_version=version)
                if module_id != -1:
                    threading.Thread(target=create_env, args=(module_id,)).start()
                    return JsonResponse.success(data='创建成功，并且在初始化对应的conda环境').to_dict()
                else:
                    return JsonResponse.error(data='创建模块失败').to_dict()
            else:
                return JsonResponse.error(data='创建模型失败').to_dict()
        except Exception as e:
            print(e)
            return JsonResponse.error(data='创建module失败').to_dict()
    except Exception as e:
        print(e)
        return JsonResponse.error(data='创建module失败').to_dict()


@app.route('/query_all_module', methods=['GET'])
def query_all_module():
    modules = Module.query.all()
    res = []
    index = 0
    for module in modules:
        repo = Repository.query.filter_by(id=module.repo_id).first()
        res.append(
            {'index': index,
             'id': module.id, 'repo_id': module.repo_id,
             'repo_name': repo.repo_name,
             'owner_name': repo.owner_name,
             'branch_name': module.branch_name,
             'repo_update_time': repo.update_time,
             'model_name': module.model_name,
             'model_hdfs_path': module.model_hdfs_path,
             # 时间戳转换为时间
             'model_update_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(module.model_update_time / 1000)),
             'model_version': module.model_version})
        index += 1
    return JsonResponse.success(data=res).to_dict()


@app.route('/delete_module_by_id', methods=['POST'])
def delete_module_by_id():
    data = request.json
    module_id = data.get('module_id')
    module = Module.query.filter_by(id=module_id).first()
    if module is None:
        return JsonResponse.error(data='没有对应的module').to_dict()
    db.session.delete(module)
    db.session.flush()
    try:
        db.session.commit()
        return JsonResponse.success(data='删除module成功').to_dict()
    except:
        db.session.rollback()
        return JsonResponse.error(data='删除module失败').to_dict()


def load_model(repo_id, branch_name, model_hdfs_path, model_update_time):
    model = Model.query.filter_by(model_hdfs_path=model_hdfs_path, update_time=model_update_time).first()
    if model is None:
        print('没有model')
        return '', 'error'
    saved_model_path = '/tmp/models/' + model.model_name + '/' + str(model.update_time)
    if not os.path.exists(saved_model_path):
        download_dir_from_hdfs(client=hdfs_client, hdfs_path=model.model_hdfs_path, local_path=saved_model_path)

    repo = Repository.query.filter_by(id=repo_id).first()
    if repo is None:
        print('没有对应的代码仓库')
        return '', 'error'
    repo_name = repo.repo_name
    owner_name = repo.owner_name
    repo_update_time = repo.update_time
    key = repo_name + '/' + branch_name + '/' + model.model_name + '/' + str(model.version)
    service_lock.acquire(blocking=True, timeout=60.0)
    if key in service_url_dict and key in service_port_dict:
        service_port_dict[key][1] = int(time.time())
        service_lock.release()
        return service_url_dict[key], 'success'
    service_lock.release()

    branches, temp_version, repo_path = query_branches_by_repo_name_and_owner(owner_name=owner_name,
                                                                              repo_name=repo_name,
                                                                              update_time=repo_update_time
                                                                              )
    print('branches:' + str(branches))
    # version = '/tmp/repos/' + owner_name + '/' + repo_name + '/temp/' + temp_version
    version = repo_path
    if not os.path.exists(version):
        print('没有本地代码仓库')
        return '', 'error'
    cwd = os.getcwd()
    command = 'cd ' + repo_path + ' && ' + 'git checkout ' + branch_name
    cmd(command)
    config_json = {}
    model_local_paths = []
    port = portscanner(already_used_ports=already_used_ports, lock=lock)

    model_local_paths.append(saved_model_path)
    config_json['model_path'] = saved_model_path
    config_json['port'] = port
    with open(version + '/mlflow_model_config.json', 'w') as f:
        f.write(json.dumps(config_json))
    f.close()
    command = 'cd ' + cwd + ' && ' + \
              'cd ' + version + ' && ' + \
              'rm -rf .git &&' + \
              'cd ' + cwd + ' && ' + \
              'mlflow run ' + version + ' -P config=mlflow_model_config.json'
    # command = 'mlflow run ' + repo_url + ' --version ' + branch_name
    print(command)
    subp = cmd(command)
    # cmd(command)
    service_url = ''
    cnt = 0
    while cnt <= 10:
        if subp.poll() is not None:
            return '', subp.stderr.read()
        print(cnt)
        cnt += 1
        if os.path.exists(version + '/' + 'mlflow_output'):
            break
        else:
            time.sleep(5)
    try:
        with open(version + '/' + 'mlflow_output') as f:
            service_lock.acquire()
            try:
                service_url = f.readline()
                service_url_dict[key] = service_url
                service_process_pid_dict[key] = subp.pid
                service_port_dict[key] = [port, int(time.time())]
                service_obj_dict[key] = subp
            finally:
                service_lock.release()
        f.close()
        return service_url, 'success'
    except Exception as e:
        print(e)
        return '', 'error'


# @app.route('/run_module', methods=['POST'])
# def run_module():
#     data = request.json
#     module_id = data.get('module_id')
#     module = Module.query.filter_by(id=module_id).first()
#     if module is None:
#         return JsonResponse.error(data='没有对应的module').to_dict()
#     repo_id = module.repo_id
#     branch_name = module.branch_name
#     model_hdfs_path = module.model_hdfs_path
#     model_update_time = module.model_update_time
#     model_version = module.model_version
#     model = Model.query.filter_by(model_hdfs_path=model_hdfs_path, update_time=model_update_time,
#                                   version=model_version).first()
#     if model is None:
#         return JsonResponse.error(data='没有对应的model').to_dict()
#     saved_model_path = '/tmp/models/' + model.model_name + '/' + str(model.update_time)
#     if not os.path.exists(saved_model_path):
#         download_dir_from_hdfs(client=hdfs_client, hdfs_path=model.model_hdfs_path, local_path=saved_model_path)
#
#     repo = Repository.query.filter_by(id=repo_id).first()
#     if repo is None:
#         return JsonResponse.error(data='没有对应的代码仓库').to_dict()
#     repo_name = repo.repo_name
#     owner_name = repo.owner_name
#     repo_update_time = repo.update_time
#     key = repo_name + '/' + branch_name + '/' + model.model_name + '/' + str(model.version)
#     service_lock.acquire(blocking=True, timeout=60.0)
#     if key in service_url_dict and key in service_port_dict:
#         service_port_dict[key][1] = int(time.time())
#         service_lock.release()
#         return JsonResponse.success(data=service_url_dict[key]).to_dict()
#     service_lock.release()
#
#     branches, temp_version = query_branches_by_repo_name_and_owner(owner_name=owner_name,
#                                                                    repo_name=repo_name,
#                                                                    update_time=repo_update_time
#                                                                    )
#     print('branches:' + str(branches))
#     version = './tmp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
#     if not os.path.exists(version):
#         return JsonResponse.error(data='没有对应的代码仓库').to_dict()
#     cwd = os.getcwd()
#     command = 'cd ' + cwd + ' && ' + 'cd ' + version + '/' + repo_name + ' && ' + 'git checkout ' + branch_name
#     cmd(command)
#     config_json = {}
#     model_local_paths = []
#     port = portscanner(already_used_ports=already_used_ports, lock=lock)
#     path = version + '/' + repo_name
#
#     model_local_paths.append(saved_model_path)
#     config_json['model_path'] = saved_model_path + '/' + model.model_name
#     config_json['port'] = port
#     with open(path + '/mlflow_model_config.json', 'w') as f:
#         f.write(json.dumps(config_json))
#     f.close()
#     command = 'cd ' + cwd + ' && ' + \
#               'cd ' + path + ' && ' + \
#               'rm -rf .git &&' + \
#               'cd ' + cwd + ' && ' + \
#               'mlflow run ' + path + ' -P config=mlflow_model_config.json --env-manager=local'
#     # command = 'mlflow run ' + repo_url + ' --version ' + branch_name
#     print(command)
#     pid = cmd(command)
#     # cmd(command)
#     service_url = ''
#     cnt = 0
#     while cnt <= 30:
#         print(cnt)
#         cnt += 1
#         if os.path.exists(path + '/' + 'mlflow_output'):
#             break
#         else:
#             time.sleep(5)
#     with open(path + '/' + 'mlflow_output') as f:
#         service_lock.acquire()
#         try:
#             service_url = f.readline()
#             service_url_dict[key] = service_url
#             service_process_pid_dict[key] = pid
#             service_port_dict[key] = [port, int(time.time())]
#         finally:
#             service_lock.release()
#     f.close()
#     return JsonResponse.success(data=service_url).to_dict()


@app.route('/run_module', methods=['POST'])
def run_module():
    data = request.json
    module_id = data.get('module_id')
    if module_id in creating_env_dict:
        return JsonResponse.error(data='正在创建环境，请稍后').to_dict()
    result = run_module_by_id(module_id)
    return result


def run_module_by_id(module_id):
    module = Module.query.filter_by(id=module_id).first()
    if module is None:
        return JsonResponse.error(data='没有对应的module').to_dict()
    repo_id = module.repo_id
    branch_name = module.branch_name
    model_hdfs_path = module.model_hdfs_path
    model_update_time = module.model_update_time
    repo = Repository.query.filter_by(id=repo_id).first()
    saved_path = '/tmp/repos/create_env/' + repo.owner_name + '/' + repo.repo_name + '/' + branch_name + '/' + str(
        repo.update_time)
    if not os.path.exists(saved_path) or not os.path.exists(saved_path + '/success.txt'):
        # 启动线程
        t = threading.Thread(target=create_env, args=(module_id,))
        t.start()
        return JsonResponse.error(data='环境尚未创建，即将开始创建环境').to_dict()
    service_url, msg = load_model(repo_id=repo_id, branch_name=branch_name, model_hdfs_path=model_hdfs_path,
                                  model_update_time=model_update_time)
    if not service_url == '':
        return JsonResponse.success(data=service_url).to_dict()
    return JsonResponse.error(data=msg).to_dict()


@app.route('/run_project_by_id', methods=['POST'])
def run_project():
    data = request.json
    project_id = data.get('project_id')
    project = Project.query.filter_by(id=project_id).first()
    project_hdfs_path = project.hdfs_path
    if project is None:
        return JsonResponse.error(data='没有对应的project').to_dict()
    update_time = project.update_time
    local_saved_path = '/tmp/projects/' + str(project_id) + '/' + str(update_time)
    if not os.path.exists(local_saved_path) and not project_hdfs_path == hdfs_client.status(project_hdfs_path)[
        'modificationTime']:
        return JsonResponse.error(data='本地没有对应的project').to_dict()
    if not os.path.exists(local_saved_path):
        os.mkdir(local_saved_path)
    hdfs_client.download(project_hdfs_path, local_saved_path, overwrite=True)
    project_relations = ProjectRelation.query.filter_by(project_id=project_id).all()
    for project_relation in project_relations:
        module_id = project_relation.module_id
        run_module_by_id(module_id)
    return JsonResponse.success(data='success').to_dict()


@app.route('/query_module_by_project_id', methods=['POST'])
def get_module_by_project_id():
    data = request.json
    project_id = data.get('project_id')
    project = Project.query.filter_by(id=project_id).first()
    if project is None:
        return JsonResponse.error(data='没有对应的project').to_dict()
    project_relations = ProjectRelation.query.filter_by(project_id=project_id).all()
    modules = []
    for project_relation in project_relations:
        module_id = project_relation.module_id
        module = Module.query.filter_by(id=module_id).first()
        modules.append({'id': module.id, 'name': module.name})
    return JsonResponse.success(data=modules).to_dict()


# @app.route('/create_project', methods=['POST'])
# def create_project():
#     data = request.json
#     config_hdfs_path = data.get('config_hdfs_path')
#     try:
#         hdfs_client.download(hdfs_path=config_hdfs_path, local_path='./tmp/project/config/' + config_hdfs_path)


@app.route('/delete_project_by_project_id', methods=['POST'])
def delete_project_by_project_id():
    data = request.json
    project_id = data.get('project_id')
    db.session.query(Project).filter(Project.id == project_id).delete()
    db.session.query(ProjectRelation).filter(ProjectRelation.project_id == project_id).delete()
    try:
        db.session.commit()
        return JsonResponse.success(data='success').to_dict()
    except Exception as e:
        print(e)
        db.session.rollback()
        return JsonResponse.error(data='error').to_dict()


# @app.route(/get_all_hdfs_model', methods=['GET'])
# def get_all_hdfs_model():
#     model_list = []
#     models = hdfs_client.list(hdfs_path='/user/wangyan/models', status=False)
#     for model in models:
#         return


@app.route('/test', methods=['POST'])
def test():
    print('---------------------------------------------')
    print(request.json)
    print('---------------------------------------------')
    return JsonResponse.success(request.json).to_dict()


@app.route('/test2', methods=['GET'])
def test2():
    print('test2 is running')
    config_hdfs_path = '/user/wangyan/config/module_config.yaml'
    print('config_hdfs_path is ' + config_hdfs_path)
    try:
        hdfs_client.status(hdfs_path=config_hdfs_path, strict=False)['modificationTime']
    except Exception as e:
        print(e)
        return JsonResponse.error(data='没有对应的配置文件').to_dict()
    try:
        local_file_path = '/tmp/module/config/' + config_hdfs_path
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        create_dir(local_file_path)
        print('local_path is ' + local_file_path)
        hdfs_client.download(hdfs_path=config_hdfs_path, local_path=local_file_path)
        # 读取yaml文件中的hdfs_path和git_path
        with open(local_file_path, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        f.close()
        model_hdfs_path = config['model_hdfs_path']
        print('model_hdfs_path is ' + model_hdfs_path)
        git_path = config['git_path']
        print('git_path is ' + git_path)
        branch_name = config['branch']
        print('branch_name is ' + branch_name)
        # 从git_path中获取repo_name和branch_name
        repo_name = git_path.split('/')[-1]
        print('repo_name is ' + repo_name)
        owner_name = git_path.split('/')[-2]
        print('owner_name is ' + owner_name)
        try:
            update_time = hdfs_client.status(hdfs_path=model_hdfs_path, strict=False)['modificationTime']
            version = create_update_model(model_hdfs_path=model_hdfs_path, update_time=update_time)
            repo = Repository.query.filter_by(repo_name=repo_name, owner_name=owner_name).first()
            if repo is None:
                return JsonResponse.error(data='没有对应的代码仓库').to_dict()
            repo_id = repo.id
            if version != -1:
                if not create_module(repo_id=repo_id, branch_name=branch_name, model_hdfs_path=model_hdfs_path,
                                     model_update_time=update_time, model_version=version) == -1:
                    return JsonResponse.success(data='创建module成功').to_dict()
                else:
                    return JsonResponse.error(data='创建module失败').to_dict()
            else:
                return JsonResponse.error(data='创建模型失败').to_dict()
        except Exception as e:
            print(e)
            return JsonResponse.error(data='创建module失败').to_dict()
    except Exception as e:
        print(e)
        return JsonResponse.error(data='创建module失败').to_dict()


@app.route('/request_service', methods=['POST'])
def request_service():
    post_data = request.json
    print('post_data is ' + str(post_data))
    service_url = post_data.get('service_url')
    print('service_url is ' + service_url)

    res = requests.post(url=service_url, json=json.dumps(post_data))
    return JsonResponse.success(data=res.text).to_dict()


@app.route('/close_service', methods=['POST'])
def close_service():
    key = request.json('service_key')
    try:
        pid = service_process_pid_dict[key]
        port = service_port_dict[key][0]
        os.kill(pid, signal.SIGKILL)
        kill_port(port)
        already_used_ports.remove(port)
    finally:
        del service_process_pid_dict[key]
        del service_url_dict[key]
        del service_port_dict[key]
    return key + '已经关闭'


@scheduler.task('interval', id='auto_close_service', seconds=600, max_instances=100)
def auto_close_service():
    service_lock.acquire()
    current_time = int(time.time())
    for k in service_port_dict.keys():
        t = service_port_dict[k][1]
        port = service_port_dict[k][0]
        if current_time - t >= 600:
            try:
                kill_port(port)
            finally:
                del service_port_dict[k]
                del service_url_dict[k]
                del service_process_pid_dict[k]
                del service_obj_dict[k]
                already_used_ports.remove(port)
    service_lock.release()
    print("定时清理服务")


@app.route('/delete_model', methods=['POST'])
def delete_model():
    data = request.json
    model_name = data.get('model_name')
    model_version = data.get('model_version')
    try:
        db.session.query(Model).filter(Model.model_name == model_name and Model.version == model_version).delete()
        return JsonResponse.success().to_dict()
    except Exception as e:
        print(e)
        return JsonResponse.error().to_dict()


@app.route('/delete_module', methods=['POST'])
def delete_module():
    data = request.json
    module_id = data.get('module_id')
    try:
        db.session.query(Module).filter(Module.id == module_id).delete()
        return JsonResponse.success(data='successful').to_dict()
    except Exception as e:
        print(e)
        return JsonResponse.error(data='failed').to_dict()


@app.route('/upload_model', methods=['POST'])
def upload_model():
    if request.method == 'POST':
        print(request.form)
        file_list = request.files.getlist('file_list')
        model_name = request.form.get('model_name')
        upload_time = time.time()
        save_dir = './upload/' + str(upload_time) + '/'
        # print(file_list.filename)
        for file in file_list:
            if not os.path.exists(save_dir + file.filename):
                os.makedirs(save_dir + file.filename)
            else:
                continue
            os.rmdir(save_dir + file.filename)
            print(type(file))
            print(file.filename)
            print()
            file.save(save_dir + file.filename)
        upload_model(model_path=save_dir,
                     model_name=model_name)
        rmtree(save_dir)
        return JsonResponse.success().to_dict()

        # model_name = request.json.get('model_name')
        # print(model_name)
        # files = request.files.getlist("file_list")
        # for file in files:
        #     print(file.filename)
        #     file.save('./upload/'+secure_filename(file.filename))
        # return 'file uploaded successfully'


if __name__ == '__main__':
    # p1 = pickle.dumps(app)
    # print('================================')
    # print(p1)
    app.run(host='0.0.0.0', port=8081, debug=False)
    # project = Project(repo_id=1, branch_name='master')
    # print(db.session.add(project))
    # db.session.flush()
    # print(db.session.commit())
    # print(project.id)
    # get_model_source('mini_model', 1)
    # print(download_directory('s3://models/0/48213a12f43f448ea97a11f2f67ec0e0/artifacts'))
