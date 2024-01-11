"""MapReduce framework Worker node."""
import os
import logging
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import pathlib
import hashlib
import heapq
import contextlib
import click

# Configure logging
LOGGER = logging.getLogger(__name__)


class Worker:
    """A class representing a Worker node in a MapReduce cluster."""

    def __init__(self, host, port, manager_host, manager_port):
        """Construct a Worker instance and start listening for messages."""
        self.host = host
        self.port = port
        self.shutdown = False
        self.heart_beat = False
        self.manager = (manager_host, manager_port)
        # self.manager_host = manager_host
        # self.manager_port = manager_port
        self.threadtcp = threading.Thread(target=self.tcpthread)
        self.threadudp = threading.Thread(target=self.udpthread)

        self.threadtcp.start()
        self.threadudp.start()

        self.threadtcp.join()
        self.threadudp.join()

        LOGGER.info(
            "Starting worker host=%s port=%s pwd=%s",
            host,
            port,
            os.getcwd(),
        )
        LOGGER.info(
            "manager_host=%s manager_port=%s",
            manager_host,
            manager_port,
        )

    def send_register(self):
        """Do docstring."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Bind the socket to the server
            # sock.connect((self.manager_host, self.manager_port))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # sock.bind((self.host, self.port))
            sock.connect(self.manager)
            message = json.dumps(
                {
                    "message_type": "register",
                    "worker_host": self.host,
                    "worker_port": self.port,
                }
            )
            sock.sendall(message.encode("utf-8"))

    def tcpthread(self):
        """Do docstring."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Bind the socket to the server
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen()
            self.send_register()
            # Socket accept() will block for a maximum of 1 second.  If you
            # omit this, it blocks indefinitely, waiting for a connection.
            sock.settimeout(1)
            while not self.shutdown:
                try:
                    client, address = sock.accept()
                    # LOGGER.info("debug")
                except socket.timeout:
                    continue
                LOGGER.info("error: %s", address[0])
                client.settimeout(1)

                with client:
                    message_chunks = []
                    while True:
                        try:
                            data_helper = client.recv(4096)

                        except socket.timeout:
                            continue
                        if not data_helper:
                            break
                        message_chunks.append(data_helper)

                # Decode list-of-byte-strings to UTF8 and parse JSON data
                message_bytes = b"".join(message_chunks)
                message_str = message_bytes.decode("utf-8")

                try:
                    message_dict = json.loads(message_str)
                except json.JSONDecodeError:
                    continue
                if message_dict["message_type"] == "shutdown":
                    self.shutdown = True
                elif message_dict["message_type"] == "register_ack":
                    self.heart_beat = True
                elif message_dict["message_type"] == "new_map_task":
                    self.map_task(message_dict)
                elif message_dict["message_type"] == "new_reduce_task":
                    # LOGGER.info("enter reduce task")
                    self.reduce_task(message_dict)
                # time.sleep(1)

    def reduce_task(self, message_dict):
        # LOGGER.info("enter reduce function")
        """Do docstring."""
        input_files = message_dict["input_paths"]
        task_id = message_dict["task_id"]

        prefix = f"mapreduce-local-task{task_id:05d}-"

        with tempfile.TemporaryDirectory(prefix=prefix) as tmpdir:
            file_name = f"part-{task_id:05d}"
            with tempfile.NamedTemporaryFile(
                    delete=False, prefix=tmpdir) as temp_file:
                temp_file.name = file_name
                with contextlib.ExitStack() as stack:
                    files = [
                        stack.enter_context(open(fname, encoding="utf-8"))
                        for fname in input_files
                    ]
                    executable = message_dict["executable"]
                    instream = heapq.merge(*files)

                    outfile = pathlib.Path(temp_file.name)
                    with open(outfile, "a", encoding="utf-8") as outopen:
                        # outopen = open(outfile, "a")
                        # LOGGER.warning("list: %s", outfile)
                        # LOGGER.info("Enter following subprocess")
                        self.helper_four(
                            executable,
                            outopen,
                            instream,
                            temp_file,
                            message_dict
                        )
            self.send_finished(task_id)

    def helper_four(
            self, executable, outopen, instream, temp_file, message_dict
            ):
        """Do docstring."""
        with subprocess.Popen(
            [executable],
            text=True,
            stdin=subprocess.PIPE,
            stdout=outopen,
        ) as reduce_process:
            # Pipe input to reduce_process
            # LOGGER.warning("in for loop")
            for line in instream:
                # LOGGER.info("Here")
                reduce_process.stdin.write(line)
                # LOGGER.debug("line: %s", line)
            fpath = pathlib.Path(temp_file.name)
            shutil.move(
                fpath, message_dict["output_directory"]
                )

    def map_task(self, message_dict):
        """Do docstring."""
        taskid = message_dict["task_id"]
        input_files = message_dict["input_paths"]
        # LOGGER.info("succeffuly enter map_task")
        prefix = f"mapreduce-local-task{taskid:05d}-"
        # prefix = os.path.join(message_dict["output_directory"], prefix)
        LOGGER.warning("map path Prefix: %s", prefix)
        with tempfile.TemporaryDirectory(prefix=prefix) as tmpdir:
            templist = []
            file_num = message_dict["num_partitions"]
            # LOGGER.info("entered map task temporary directory")
            LOGGER.info("make some files")
            for i in range(file_num):
                file_name = f"maptask{taskid:05d}-part{i:05d}"
                with tempfile.NamedTemporaryFile(
                        delete=False, prefix=tmpdir) as temp:
                    temp.name = file_name
                    templist.append(temp)
                # LOGGER.info("file_name: %s", file_name)
            LOGGER.info("files have been created")
            # try:
            self.helper_two(input_files, message_dict, templist)
            # sort
            # LOGGER.info("sorting...")
            self.helper_one(templist, message_dict)
            self.send_finished(taskid)

    def helper_two(self, input_files, message_dict, templist):
        """Do docstring."""
        with contextlib.ExitStack() as stack:
            files = [
                stack.enter_context(open(fname, encoding="utf-8"))
                for fname in input_files
            ]
            for file in files:
                executable = message_dict["executable"]
                input_path = file.name
                with open(input_path, encoding="utf-8") as infile:
                    with subprocess.Popen(
                        [executable],
                        stdin=infile,
                        stdout=subprocess.PIPE,
                        text=True,
                    ) as map_process:
                        with contextlib.ExitStack() as stack:
                            temp_files = [
                                stack.enter_context(
                                    open(fname.name, "a", encoding="utf-8")
                                )
                                for fname in templist
                            ]
                            for line in map_process.stdout:
                                # Add line to correct partition output file
                                self.helper_three(
                                    line, message_dict,
                                    temp_files
                                    )
            LOGGER.info("files have been created")

    def helper_three(self, line, message_dict, temp_files):
        """Do docstring."""
        key = line.split("\t")[0]
        value = line.split("\t")[1]
        # LOGGER.warning("linelist: %s", line.split("\t"))
        # LOGGER.info("key: %s", key)
        # LOGGER.info("value: %s", value)
        hexdigest = hashlib.md5(key.encode("utf-8")).hexdigest()
        keyhash = int(hexdigest, base=16)
        partition = keyhash % message_dict["num_partitions"]
        # with open((temp_files[partition]).name, "a") as f:
        temp_files[partition].write(f"{key}\t{value}")

    def helper_one(self, templist, message_dict):
        """Do docstring."""
        for file in templist:
            with open(file.name, encoding="utf-8") as infile:
                # infile = open(file.name, encoding="utf-8")
                # LOGGER.info("opened file name: %s", file.name)
                words = []
                file_line = infile.readline()
                while file_line:
                    # LOGGER.info("opened fileline: %s", file_line)
                    words.append(file_line)
                    file_line = infile.readline()
                # LOGGER.info("words: %s", words)
            words.sort()
            # LOGGER.info("sorted words: %s", words)
            with open(file.name, "w", encoding="utf-8") as f_file:
                f_file.write("")
            with open(file.name, "a", encoding="utf-8") as f_file:
                # LOGGER.info("opened file")
                for line in words:
                    # LOGGER.info("line: %s", line)
                    f_file.write(line)
                # LOGGER.info("written line")
                # LOGGER.info("%s", file)
                # LOGGER.info("written file: %s", file.name)
                fpath = pathlib.Path(file.name)
                shutil.move(fpath, message_dict["output_directory"])
            # LOGGER.warning("moved file: %s", file.name)

    def send_finished(self, taskid):
        """Do docstring."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # LOGGER.info("sending finished")
            sock.connect(self.manager)
            message = json.dumps(
                {
                    "message_type": "finished",
                    "task_id": taskid,
                    "worker_host": self.host,
                    "worker_port": self.port,
                }
            )
            sock.sendall(message.encode("utf-8"))

    def udpthread(self):
        """Do docstring."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.connect(self.manager)
            while not self.shutdown:
                if self.heart_beat:
                    LOGGER.warning("Sending heart beat")
                    message = json.dumps(
                        {
                            "message_type": "heartbeat",
                            "worker_host": self.host,
                            "worker_port": self.port,
                        }
                    )
                    sock.sendall(message.encode("utf-8"))
                time.sleep(2)


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=6001)
@click.option("--manager-host", "manager_host", default="localhost")
@click.option("--manager-port", "manager_port", default=6000)
@click.option("--logfile", "logfile", default=None)
@click.option("--loglevel", "loglevel", default="info")
def main(host, port, manager_host, manager_port, logfile, loglevel):
    """Run Worker."""
    if logfile:
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(f"Worker:{port} [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(loglevel.upper())
    Worker(host, port, manager_host, manager_port)


if __name__ == "__main__":
    main()
