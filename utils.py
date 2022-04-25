import os


# Function name: delete
# Function operation: delete the file or the directory that get
# Param path: the socket that is connected to the client
def delete(path):
    # check if the path is directory
    if os.path.isdir(path):
        # over on the directory from the deepest directory to the directory
        for path, dirs, files in os.walk(path, topdown=False):
            # delete all the files
            for file in files:
                os.remove(os.path.join(path, file))
            # delete all the directory
            for dir in dirs:
                os.rmdir(os.path.join(path, dir))
        # delete the directory
        os.rmdir(path)
    else:
        # delete the file
        os.remove(path)


# Function name: getFolder
# Function operation: get from socket directory
# Param sock: the socket that is connected
# Param dir: the path of directory to save their the directory from socket
def getFolder(sock, dir):
    # get type of data
    size = sock.recv(4)
    info = sock.recv(int.from_bytes(size, 'big'))
    while info:
        # if the data is directory
        if info != b'file':
            # get relative path
            size = sock.recv(4)
            info = sock.recv(int.from_bytes(size, 'big'))
            info = info.strip().decode()
            # get absolut path
            path = os.path.join(dir, info)
            # create the directory and get the next type of data
            os.mkdir(path)
            size = sock.recv(4)
            info = sock.recv(int.from_bytes(size, 'big'))
            continue
        # the data type is file
        size = sock.recv(4)
        # get relative path
        info = sock.recv(int.from_bytes(size, 'big'))
        info = info.strip().decode()
        # get absolut path
        path = os.path.join(dir, info)
        # create the file
        f = open(path, 'wb')
        size = sock.recv(4)
        size = int.from_bytes(size, 'big')
        # write the file
        while size > 0:
            info = sock.recv(min(1000000, size))
            f.write(info)
            size -= len(info)
        f.close()
        # get the next type of data
        size = sock.recv(4)
        info = sock.recv(int.from_bytes(size, 'big'))


# Function name: sendFolder
# Function operation: send directory file after file
# Param sock: the socket that is connected
# Param dir: the path of directory to send
def sendFolder(sock, dir):
    # over on all the directories in dir
    for path, dirs, files in os.walk(dir):
        # send all the directory
        for di in dirs:
            # get relative path
            pathD = os.path.join(path, di)
            relPath = os.path.relpath(pathD, dir)
            # send that it is path to directory
            sock.send((3).to_bytes(4, 'big'))
            sock.send(b'dir')
            # send the relative path
            sock.send(len(relPath).to_bytes(4, 'big'))
            sock.send(relPath.encode())
        # send all the files in the directory
        for file in files:
            # get relative path
            fileName = os.path.join(path, file)
            relPath = os.path.relpath(fileName, dir)
            # send that send file
            fileSize = os.path.getsize(fileName)
            sock.send((4).to_bytes(4, 'big'))
            sock.send(b'file')
            # send the relative path
            sock.send(len(relPath).to_bytes(4, 'big'))
            sock.send(relPath.encode())
            # send the file size
            sock.send(fileSize.to_bytes(4, 'big'))
            f = open(fileName, 'rb')
            # Send the file in chunks so large files can be handled.
            while True:
                data = f.read(1_000_000)
                if not data:
                    break
                sock.send(data)
            f.close()
