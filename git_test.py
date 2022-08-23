import os
import subprocess
from git import Repo
import shutil

import stat


def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


def cmd(command):
    subp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    subp.wait(60)
    if subp.poll() == 0:
        print(subp.communicate()[1])
    else:
        print("失败")


def get_branches(git_url, owner_name, repo_name):
    repo_url = git_url + '/' + owner_name + '/' + repo_name + '.git'
    print(repo_url)
    to_path = repo_name
    repo = None
    if os.path.exists(to_path):
        # repo = Repo(to_path)
        # remote = repo.remote()
        # remote.fetch()
        # 删除本地文件
        # rmtree(to_path)
        pass
    else:
        repo = Repo.clone_from(url=repo_url, to_path=to_path)
    remote_branches = []
    for ref in repo.git.branch('-r').split('\n'):
        print(ref)
        remote_branches.append(ref)
    print(remote_branches)
    cwd = os.getcwd()
    os.chdir(repo_name)
    cmd('git checkout ' + remote_branches[2])
    os.chdir(cwd)


get_branches(git_url='http://39.105.6.98:43101', owner_name='Rock', repo_name='test_repository')
