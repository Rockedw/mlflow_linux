# -*- coding: UTF-8 -*-
import signal
import time

import requests
from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import pymysql
import os
from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from util_methods import cmd, download_directory, rmtree, scan_dir, portscanner, kill_port
import shutil
import json
from JsonResponse import JsonResponse
import threading
import time
from flask_apscheduler import APScheduler

pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app, resources=r'/*')
db = SQLAlchemy(app)

app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
lock = threading.Lock()
service_lock = threading.Lock()
bucket_name = Config.bucket_name
access_key = Config.access_key
secret_key = Config.secret_key
endpoint_url = Config.endpoint_url
git_url = Config.git_url
service_port_dict = {}
service_url_dict = {}
service_process_pid_dict = {}
already_used_ports = []


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


class Model(db.Model):
    """
    模型
    """
    __tablename__ = 'model_versions'
    __bind_key__ = 'mlflow'
    name = db.Column('name', db.String(256), primary_key=True)
    version = db.Column('version', db.Integer, primary_key=True)
    source = db.Column('source', db.String(500))
    create_time = db.Column('creation_time', db.Integer)


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


class Project(db.Model):
    __tablename__ = 'project'
    __bind_key__ = 'mlflow'
    id = db.Column('id', db.Integer, primary_key=True, index=True)
    repo_id = db.Column('repo_id', db.Integer)
    branch_name = db.Column('branch_name', db.String(255))


class ProjectRelation(db.Model):
    __tablename__ = 'project_relation'
    __bind_key__ = 'mlflow'
    id = db.Column('id', db.Integer, primary_key=True, index=True)
    project_id = db.Column('project_id', db.Integer)
    model_name = db.Column('model_name', db.String(500))
    model_version = db.Column('model_version', db.Integer)


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


@app.route('/query_all_project', methods=['GET'])
def query_all_project():
    print('get_all_project')
    try:
        projects = Project.query.all()
    except Exception as e:
        projects = []
    res = []
    index = 0
    for project in projects:
        repo = Repository.query.filter_by(id=project.repo_id).all()[0]
        repo_name = repo.repo_name
        repo_owner = repo.owner_name
        update_time = repo.update_time
        temp = get_project_relation_by_pid(project.id)
        res.append(
            {'index': index, 'project_id': project.id, 'repo_owner': repo_owner, 'repo_name': repo_name,
             'branch_name': project.branch_name, 'model_names': temp['models'],
             'model_versions': temp['versions'], 'update_time': update_time})
        index += 1
        # print(res)
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
    path = './repos/' + owner_name + '/' + repo_name
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
        print(ref)
        remote_branches.append(ref)

    print(remote_branches)
    temp_path = './temp/repos/' + owner_name + '/' + repo_name
    try:
        temp_version = str(len(os.listdir(temp_path)))
    except Exception as e:
        temp_version = '0'

    to_path = temp_path + '/' + temp_version + '/' + repo_name
    shutil.copytree(path, to_path)

    return remote_branches, temp_version


@app.route('/query_all_repo')
def query_all_repo():
    """
    查血所有代码仓库
    :return:
    """
    repos = Repository.query.all()
    res = []
    for repo in repos:
        res.append(
            {'id': repo.id, 'owner_name': repo.owner_name, 'repo_name': repo.repo_name, 'lower_name': repo.lower_name,
             'update_time': repo.update_time})
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
    branches, temp_version = query_branches_by_repo_name_and_owner(owner_name=owner_name,
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
        path = './temp/repos/' + owner_name + '/' + repo_name + '/' + temp_version + '/' + repo_name
    else:
        path = './repos/' + owner_name + '/' + repo_name
    if branch_name is not None:
        if not os.path.exists(path):
            return JsonResponse.error(msg='There is no git directory').to_dict()
        cwd = os.getcwd()
        command = 'cd ' + cwd + ' && ' + 'cd ' + path + ' && ' + 'git checkout ' + branch_name
        print(command)
        cmd(command)
    files = scan_dir(path)
    # rmtree(path)
    return JsonResponse.success(data=[files]).to_dict()


@app.route('/query_all_model', methods=['GET'])
def query_all_model():
    """
    查询所有模型
    :return:
    """
    model_list = Model.query.all()
    models = {}
    for model in model_list:
        if model.name not in models:
            models[model.name] = [
                {'model_version': model.version, 'model_source': model.source, 'create_time': model.create_time}]
        else:
            models[model.name].append(
                {'model_version': model.version, 'model_source': model.source, 'create_time': model.create_time})
    return JsonResponse.success(data=models).to_dict()


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
    path = './temp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
    if not os.path.exists(path):
        return JsonResponse.error(msg='There is no git directory').to_dict()
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
    version = './temp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
    path = version + '/' + repo_name
    # print('path : ' + path)
    if not os.path.exists(path):
        print('nothing')
        return JsonResponse.error(msg='There is no git directory').to_dict()
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


@app.route('/load_model', methods=['POST'])
def load_model():
    data = request.json
    owner_name = data.get('repo_owner')
    repo_name = data.get('repo_name')
    branch_name = data.get('branch_name')
    update_time = data.get('update_time')
    model_names: list = data.get('model_names')
    model_versions: list = data.get('model_versions')
    print(data)
    key = repo_name + '/' + branch_name
    for i in range(0, len(model_names)):
        key = key + '/' + model_names[i] + '/' + str(model_versions[i])
    service_lock.acquire(blocking=True, timeout=60.0)
    if key in service_url_dict and key in service_port_dict:
        service_port_dict[key][1] = int(time.time())
        service_lock.release()
        return JsonResponse.success(data=service_url_dict[key]).to_dict()
    service_lock.release()
    branches, temp_version = query_branches_by_repo_name_and_owner(owner_name=owner_name,
                                                                   repo_name=repo_name,
                                                                   update_time=update_time
                                                                   )
    print('branches:' + str(branches))
    version = './temp/repos/' + owner_name + '/' + repo_name + '/' + temp_version
    if not os.path.exists(version):
        return JsonResponse.error(data='没有对应的代码仓库').to_dict()
    cwd = os.getcwd()
    command = 'cd ' + cwd + ' && ' + 'cd ' + version + '/' + repo_name + ' && ' + 'git checkout ' + branch_name
    cmd(command)
    config_json = {}
    model_local_paths = []
    port = portscanner(already_used_ports=already_used_ports, lock=lock)
    path = version + '/' + repo_name
    for i in range(0, len(model_names)):
        local_path = download_directory(download_path=get_model_source(model_names[i], version=model_versions[i]))
        model_local_paths.append(local_path)
        config_json[model_names[i]] = local_path
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
    pid = cmd(command)
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
        service_lock.acquire()
        service_url = f.readline()
        service_url_dict[key] = service_url
        service_process_pid_dict[key] = pid
        service_port_dict[key] = [port, int(time.time())]
        service_lock.release()
    f.close()
    return JsonResponse.success(data=service_url).to_dict()


@app.route('/create_project', methods=['POST'])
def create_project():
    data = request.json
    owner_name = data.get('owner_name')
    repo_name = data.get('repo_name')
    branch_name = data.get('branch_name')
    model_list = data.get('model_list')
    repo = Repository.query.filter_by(owner_name=owner_name, repo_name=repo_name).first()
    repo_id = repo.id
    project = Project(repo_id=repo_id, branch_name=branch_name)
    db.session.add(project)
    db.session.flush()
    project_id = project.id
    for model in model_list:
        project_relation = ProjectRelation(project_id=project_id, model_name=model[0], model_version=int(model[1]))
        db.session.add(project_relation)
    try:
        db.session.commit()
        return JsonResponse.success(data='success').to_dict()
    except Exception as e:
        print(e)
        db.session.rollback()
        return JsonResponse.error().to_dict()


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


@app.route('/test', methods=['POST'])
def test():
    print('---------------------------------------------')
    print(request.json)
    print('---------------------------------------------')
    return JsonResponse.success(request.json).to_dict()


@app.route('/test2', methods=['GET'])
def test2():
    print('---------------------------------------------')
    print('---------------------------------------------')
    return JsonResponse.success(str(service_process_pid_dict) + str(service_url_dict)).to_dict()


@app.route('/request_service', methods=['POST'])
def request_service():
    post_data = request.json
    service_url = post_data.get('service_url')

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


@scheduler.task('interval', id='auto_close_service', seconds=600)
def auto_close_service():
    service_lock.acquire()
    current_time = int(time.time())
    for k, v in service_port_dict.items():
        t = v[1]
        port = v[0]
        if current_time - t >= 600:
            try:
                kill_port(port)
            finally:
                del service_port_dict[k]
                del service_url_dict[k]
                del service_process_pid_dict[k]
                already_used_ports.remove(v[0])
    service_lock.release()
    print("定时清理服务")


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
