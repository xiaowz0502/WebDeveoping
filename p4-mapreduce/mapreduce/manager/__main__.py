"""MapReduce framework Manager node."""
import tempfile
import logging
import json
import time
import threading
import socket
from collections import deque
import pathlib
import shutil
import click

# import mapreduce.utils

# Configure logging
LOGGER = logging.getLogger(__name__)


class Manager:
    """Represent a MapReduce framework Manager node."""

    def __init__(self, host, port):
        """Construct a Manager instance and start listening for messages."""
        self.mdic = {
            "shutdown": False,
            "host_port": (host, port),
            "job_finished": True,
            "workers": [],
            "job_id_tracker": 0,
        }
        self.tasks = deque()
        self.readyworkers = deque()
        self.jobs = deque()
        self.threadtcp = threading.Thread(target=self.tcp_server)
        self.threadudp = threading.Thread(target=self.udp_server)
        self.threadjob = threading.Thread(target=self.job_handler)
        self.threadtcp.start()
        self.threadudp.start()
        self.threadjob.start()

        time.sleep(0.1)

        self.threadtcp.join()
        self.threadudp.join()
        self.threadjob.join()

    def job_handler(self):
        """Handle jobs."""
        while not self.mdic["shutdown"]:
            if len(self.jobs) != 0:
                job = self.jobs.popleft()
                self.mdic["job_finished"] = False
                out_path = pathlib.Path(job["output_directory"])
                LOGGER.warning("out_path: %s", out_path)
                if out_path.is_dir():
                    LOGGER.warning("Output directory already exists, deleting")
                    shutil.rmtree(out_path)
                    # LOGGER.info("Output directory already exists, deleting")
                out_path.mkdir(parents=True, exist_ok=True)
                jobid = job["job_id"]
                prefix = f"mapreduce-shared-job{jobid:05d}-"
                with tempfile.TemporaryDirectory(prefix=prefix) as tmpdir:
                    in_path = pathlib.Path(job["input_directory"])
                    filenamelist = sorted(
                        f for f in in_path.iterdir() if f.is_file())
                    # LOGGER.info("filenamelist: %s", filenamelist)
                    self.handle_mapping(job, filenamelist, tmpdir)
                    self.wait_jobfinish()
                    time.sleep(1)
                    self.handle_reduce(job, tmpdir, out_path)
                    self.wait_jobfinish()
                    time.sleep(2)
            time.sleep(1)
            self.mdic["job_finished"] = True

    def wait_jobfinish(self):
        """Wait for job to finish."""
        while len(self.tasks) != 0:
            if self.mdic["shutdown"]:
                return
            self.dead_checker()
            time.sleep(0.1)

    def handle_mapping(self, job, filenamelist, tmpdir):
        """Handle mapping."""
        list_dict = []
        for i in range(0, job["num_mappers"]):
            list_dict.append([])
        for i, file in enumerate(filenamelist):
            list_dict[i % job["num_mappers"]].append(str(file))
        # LOGGER.info("%s", listDict)
        for i in range(0, job["num_mappers"]):
            while len(self.readyworkers) == 0:
                # LOGGER.warning("no worker available, waiting")
                if self.mdic["shutdown"]:
                    return
                time.sleep(1)
            avail = self.readyworkers.popleft()
            # LOGGER.info("Worker %s is popped", i)
            pexec = pathlib.Path(job["mapper_executable"])
            # if job["mapper_executable"][0] != "/":
            #     pexec = job["output_directory"]
            # pexec.relative_to()
            dic = {
                "message_type": "new_map_task",
                "task_id": i,
                "input_paths": list_dict[i],
                "executable": str(pexec),
                "output_directory": tmpdir,
                "num_partitions": job["num_reducers"],
                "worker_host": self.mdic["workers"][avail]["host"],
                "worker_port": self.mdic["workers"][avail]["port"],
            }
            self.tasks.append([i, self.mdic["workers"][avail]["id"]])
            self.mdic["workers"][avail]["task"] = dic
            # LOGGER.info("%s", dic)
            self.mdic["workers"][avail]["status"] = "busy"
            try:
                with socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM) as socktmp:
                    socktmp.connect(
                        (
                            (
                                self.mdic["workers"][avail]["host"],
                                self.mdic["workers"][avail]["port"],
                            )
                        )
                    )
                    message = json.dumps(dic)
                    socktmp.sendall(message.encode("utf-8"))
            except ConnectionRefusedError:
                self.mdic["workers"][avail]["status"] = "dead"

    def handle_reduce(self, job, tmpdir, out_path):
        """Handle reduce."""
        reducelist = []
        # LOGGER.info("Reduce works start")
        # LOGGER.info("%s", job["num_reducers"])
        for i in range(0, job["num_reducers"]):
            reducelist.append([])
        # LOGGER.info("reducelist: %s", reducelist)
        # LOGGER.info("tmpdir: %s", tmpdir)
        temp_path = pathlib.Path(tmpdir)
        # LOGGER.warning("tempPath: %s", tempPath)
        filelist = sorted(f for f in temp_path.iterdir() if f.is_file())
        # LOGGER.info("filelist: %s", filelist)
        for i in range(0, job["num_reducers"]):
            for file in filelist:
                checkname = f"part{i:05d}"
                if file.name.find(checkname) != -1:
                    # LOGGER.warning("filename: %s", filelist[j].name)
                    reducelist[i].append(str(file))
        # LOGGER.info("reduce list: %s", reducelist)
        for i in range(0, job["num_reducers"]):
            while len(self.readyworkers) == 0:
                if self.mdic["shutdown"]:
                    return
                time.sleep(0.1)
            avail = self.readyworkers.popleft()
            # LOGGER.info("Worker %s is popped", i)
            pexec = pathlib.Path(job["reducer_executable"])
            # LOGGER.warning("reducer_executable before absolute(): %s", pexec)
            pexec = pexec.absolute()
            # LOGGER.warning("reducer_executable: %s", pexec)
            dic = {
                "message_type": "new_reduce_task",
                "task_id": i,
                "input_paths": reducelist[i],
                "executable": str(pexec),
                "output_directory": str(out_path),
                "worker_host": self.mdic["workers"][avail]["host"],
                "worker_port": self.mdic["workers"][avail]["port"],
            }
            # LOGGER.info("%s", dic)
            self.tasks.append([i, self.mdic["workers"][avail]["id"]])
            self.mdic["workers"][avail]["task"] = dic
            self.mdic["workers"][avail]["status"] = "busy"
            try:
                with socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM) as socktmp:
                    socktmp.connect(
                        (
                            (
                                self.mdic["workers"][avail]["host"],
                                self.mdic["workers"][avail]["port"],
                            )
                        )
                    )
                    message = json.dumps(dic)
                    socktmp.sendall(message.encode("utf-8"))
            except ConnectionRefusedError:
                self.mdic["workers"][avail]["status"] = "dead"

    def dead_checker(self):
        """Check dead workers."""
        # # LOGGER.warning("enter deadchecker")
        # # LOGGER.warning("self.tasks: %s", self.tasks)
        taskslength = len(self.tasks)
        for i in range(taskslength):
            if self.mdic["workers"][self.tasks[i][1]]["status"] != "busy":
                # # LOGGER.warning("readyworker: %s", self.readyworkers)
                while len(self.readyworkers) == 0:
                    # # LOGGER.warning("no worker available, waiting")
                    if self.mdic["shutdown"]:
                        return
                    time.sleep(0.1)
                # # LOGGER.warning("worker available, pop")
                ava = self.readyworkers.popleft()
                # # LOGGER.warning("worker available %s", self.workers[avail])

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

                    send_dic = self.mdic["workers"][self.tasks[i][1]]["task"]

                    send_dic["worker_host"] = self.mdic["workers"][ava]["host"]
                    send_dic["worker_port"] = self.mdic["workers"][ava]["port"]
                    self.mdic["workers"][ava]["status"] = "busy"
                    self.mdic["workers"][ava]["task"] = send_dic
                    self.mdic["workers"][self.tasks[i][1]]["task"] = None
                    # # LOGGER.info("ready to append")
                    list_temp = [
                        self.tasks[i][0],
                        self.mdic["workers"][ava]["id"]
                        ]
                    # # LOGGER.warning("append task: %s", list_temp)
                    self.tasks.append(list_temp)
                    # # LOGGER.warning("success")
                    self.tasks.remove(self.tasks[i])
                    # # LOGGER.warning("task worker id: %s", self.tasks[i][1])
                    try:
                        sock.connect(
                            (
                                self.mdic["workers"][ava]["host"],
                                self.mdic["workers"][ava]["port"],
                            )
                        )
                        # # LOGGER.info("connect finished")
                        sock.sendall(json.dumps(send_dic).encode("utf-8"))
                    # # LOGGER.info("sendall finished")
                    except ConnectionRefusedError:
                        self.mdic["workers"][ava]["status"] = "dead"

    def udp_server(self):
        """Test UDP Socket Server."""
        # Create an INET, DGRAM socket, this is UDP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

            # Bind the UDP socket to the server
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(self.mdic["host_port"])
            sock.settimeout(1)

            # Receive incoming UDP messages
            while not self.mdic["shutdown"]:
                if len(self.mdic["workers"]) != 0:
                    try:
                        message_bytes = sock.recv(4096)
                    except socket.timeout:
                        continue
                    message_str = message_bytes.decode("utf-8")
                    message_dict = json.loads(message_str)
                    for worker in self.mdic["workers"]:
                        curtime = time.time()
                        # LOGGER.warning("curtime: %s", curtime)
                        if (
                            worker["host"] == message_dict["worker_host"]
                            and worker["port"] == message_dict["worker_port"]
                        ):
                            worker["worker_last_heartbeat"] = curtime
                        if curtime - worker["worker_last_heartbeat"] > 10:
                            # LOGGER.warning("start changing status")
                            worker["status"] = "dead"
                            # LOGGER.info("status changing success")
                time.sleep(0.1)

    def tcp_server(self):
        """Test TCP Socket Server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Bind the socket to the server
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("localhost", self.mdic["host_port"][1]))
            sock.listen()
            # LOGGER.info("TCP Server listening on")
            # Socket accept() will block for a maximum of 1 second.  If you
            # omit this, it blocks indefinitely, waiting for a connection.
            sock.settimeout(1)
            while not self.mdic["shutdown"]:
                try:
                    clientsocket, address = sock.accept()
                except socket.timeout:
                    continue
                clientsocket.settimeout(1)
                with clientsocket:
                    message_chunks = []
                    while True:
                        try:
                            data = clientsocket.recv(4096)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        message_chunks.append(data)

                # Decode list-of-byte-strings to UTF8 and parse JSON data
                message_str = (b"".join(message_chunks)).decode("utf-8")

                try:
                    mes_dict = json.loads(message_str)
                except json.JSONDecodeError:
                    continue
                if mes_dict["message_type"] == "shutdown":
                    self.shutdown_workers(address)

                    self.mdic["shutdown"] = True
                elif mes_dict["message_type"] == "register":
                    self.do_register(address, mes_dict)
                elif mes_dict["message_type"] == "new_manager_job":
                    # LOGGER.info("New manager")
                    job = {
                        "input_directory": mes_dict["input_directory"],
                        "output_directory": mes_dict["output_directory"],
                        "mapper_executable": mes_dict["mapper_executable"],
                        "reducer_executable": mes_dict["reducer_executable"],
                        "num_mappers": mes_dict["num_mappers"],
                        "num_reducers": mes_dict["num_reducers"],
                        "job_id": self.mdic["job_id_tracker"],
                    }
                    self.jobs.append(job)
                    # LOGGER.info("New job %s", self.mdic["job_id_tracker"])
                    self.mdic["job_id_tracker"] += 1
                elif mes_dict["message_type"] == "finished":
                    for i in range(0, len(self.mdic["workers"])):
                        if (
                            self.mdic["workers"][i]["host"]
                            == mes_dict["worker_host"]
                            and self.mdic["workers"][i]["port"]
                            == mes_dict["worker_port"]
                        ):
                            self.mdic["workers"][i]["status"] = "ready"
                            self.mdic["workers"][i]["task"] = None
                            self.tasks.remove([mes_dict["task_id"], i])
                            self.readyworkers.append(i)
                            break

    def do_register(self, address, mes_dict):
        """Do register."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            hasdead = False
            index = None
            for worker in self.mdic["workers"]:
                if (
                    worker["host"] == address[0]
                    and worker["port"] == mes_dict["worker_port"]
                ):
                    hasdead = True
                    index = worker["id"]
                    break

            if hasdead:
                self.mdic["workers"][index]["status"] = "ready"
                self.readyworkers.append(self.mdic["workers"][index]["id"])
                # if self.mdic["workers"][index]["task"] is not None:
                #     self.mdic["workers"][index]["task"] = None
            else:
                worker = {
                    "host": mes_dict["worker_host"],
                    "port": mes_dict["worker_port"],
                    "worker_last_heartbeat": time.time(),
                    "status": "ready",
                    "task": None,
                    "id": len(self.mdic["workers"]),
                }
                self.mdic["workers"].append(worker)
                worker_id = len(self.mdic["workers"]) - 1
                self.readyworkers.append(worker_id)

                try:
                    sock.connect((address[0], mes_dict["worker_port"]))
                    message = json.dumps(
                        {
                            "message_type": "register_ack",
                            "worker_host": mes_dict["worker_host"],
                            "worker_port": mes_dict["worker_port"],
                        }
                    )
                    sock.sendall(message.encode("utf-8"))
                except ConnectionRefusedError:
                    for worker in self.mdic["workers"]:
                        if (
                            worker["host"] == address[0]
                            and worker["port"] == mes_dict["worker_port"]
                        ):
                            worker["status"] = "dead"

    def shutdown_workers(self, address):
        """Shut down all workers."""
        # LOGGER.warning("enter shutdown workers before for loop")
        for port in self.mdic["workers"]:
            # LOGGER.warning("enter shutdown workers")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if port["status"] != "dead":
                    # LOGGER.warning("port: %s", port)
                    try:
                        sock.connect((address[0], port["port"]))
                        message = json.dumps(
                            {
                                "message_type": "shutdown",
                            }
                        )
                        sock.sendall(message.encode("utf-8"))
                    except ConnectionRefusedError:
                        continue
                    # LOGGER.info("DDEEBBUUGG:  shutdown to %s", message)


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=6000)
@click.option("--logfile", "logfile", default=None)
@click.option("--loglevel", "loglevel", default="info")
@click.option("--shared_dir", "shared_dir", default=None)
def main(host, port, logfile, loglevel, shared_dir):
    """Run Manager."""
    tempfile.tempdir = shared_dir
    if logfile:
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(
        f"Manager:{port} [%(levelname)s] %(message)s"
        )
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(loglevel.upper())
    Manager(host, port)


if __name__ == "__main__":
    main()
