import concurrent.futures
import functools
import os
import re
import sys
import time

import chardet
import paramiko
import yaml


# ======================================================================================================================


# 返回信息
class ReInfo:
    def __init__(self, status: int = 0, msg: str = "函数正常"):
        self.host = ""
        self.status: int = status
        self.msg: str = msg

    def print_msg(self):
        print(self.host)
        print(self.msg)
        print(self.status)

    def status(self) -> int:
        """

        :return: int
        """
        return self.status

    def get_msg(self) -> str:
        return self.msg

    def set_re_info(self, status: int = 0, msg: str = "函数正常"):
        self.status = status
        self.msg = msg


# docker操作函数
class DockerTool:
    def __init__(self, server: dict):
        # 配置参数
        self.host = server['host'] if 'host' in server else None
        self.port = server['port'] if 'port' in server else 22
        self.username = server['username'] if 'username' in server else os.getlogin()
        self.password = server['password'] if 'password' in server else ""
        self.key_filename = server['key_filename'] if 'key_filename' in server else "~/.ssh/id_rsa"
        self.key_filename = self.key_filename.replace("~", os.path.expanduser("~"))
        self.re_info = ReInfo()
        self.re_info.host = self.host
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

    def connect_server(self) -> int:
        try:
            self.client.connect(hostname=self.host, port=self.port,
                                username=self.username, key_filename=self.key_filename)
        except:
            self.client.connect(hostname=self.host, port=self.port,
                                username=self.username, password=self.password)

        try:
            self.client.get_transport()
            self.re_info.set_re_info(0, "登录成功")
        except:
            self.re_info.set_re_info(1, "登录失败")

        return self.re_info.status

    def ubuntu_install_docker(self) -> int:
        # 更新缓存
        self.client.exec_command("sudo apt update")
        # 选择docker版本
        stdin, stdout, stderr = self.client.exec_command("sudo apt-cache madison docker.io")
        outline = stdout.readlines()[0]
        if not re.match("N:.*", outline):
            version = outline.split()[2]
        else:
            self.re_info.set_re_info(1, "软件包未找到")
            return self.re_info.status

        # 安装docker
        stdin, stdout, stderr = self.client.exec_command(f"sudo apt-get install -y docker.io={version}")
        if stdout.channel.recv_exit_status() == 0:
            self.re_info.set_re_info(0, "安装docker成功")
        else:
            self.re_info.set_re_info(1, "安装docker失败")
        return self.re_info.status

    def start_docker(self) -> int:
        # 检查docker
        stdin, stdout, stderr = self.client.exec_command("sudo systemctl is-active docker")
        if stdout.channel.recv_exit_status() == 0:
            # docker 已经启动
            self.client.exec_command("sudo systemctl daemon-reload")
            stdin, stdout, stderr = self.client.exec_command("sudo systemctl restart docker")
        else:
            stdin, stdout, stderr = self.client.exec_command("sudo systemctl start docker")
        # 检查结果
        self.re_info.set_re_info(stdout.channel.recv_exit_status(), stderr.read().decode())
        return self.re_info.status

    def install_docker(self) -> int:
        """
        多发行版通用安装函数
        未完成
        :return:
        """
        try:
            self.client.get_transport()
        except:
            if self.connect_server() != 0:
                return self.re_info.status

        # 系统检查
        pass

    def install_docker_from_tar(self) -> int:
        """
        未完成
        :return:
        """
        pass

# ====================================================================================================================


def servers_install_docker(server_list: list) -> int:
    # 主机对象列表
    for server in server_list:
        docker_host = DockerTool(server)
        if docker_host.connect_server() != 0:
            docker_host.re_info.print_msg()
            return 1

        if docker_host.ubuntu_install_docker() != 0:
            docker_host.re_info.print_msg()
            return 2
    return 0


def print_config():
    config_file = """
global_key_file: "~/.ssh/id_rsa"
servers:
  - host: "192.168.1.31"
    password: "123456"
    key_filename: "~/.ssh/id_rsa"
    port: 22
    username: "vga"
"""
    print(config_file)


# ====================================================================================================================


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "help":
            print_config()
            sys.exit(0)

    # 查找配置文件
    if not os.path.exists("docker.yaml"):
        print("配置文件未找到")

    # 读取配置文件
    with open("docker.yaml", "rb") as f:
        charset = chardet.detect(f.read(4))['encoding']
    with open("docker.yaml", "r") as f:
        config = yaml.safe_load(f)

    # 安装docker
    new_server_list: list = []
    global_pass = config['global_pass'] if 'global_pass' in config else None
    global_key_file = config['global_key_file'] if 'global_key_file' in config else "~/.ssh/id_rsa"

    # 配置服务器列表
    for server in config['servers']:
        server['password'] = server['password'] if 'password' in server else global_pass
        server['key_filename'] = server['key_filename'] if 'key_filename' in server else global_key_file
        new_server_list.append(server)

    # 安装 dockers
    servers_install_docker(new_server_list)
