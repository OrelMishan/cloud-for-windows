import os
import socket
import random
import string
import sys
import utils


# Function name: addEvent
# Function operation: add the event that get from the client
# to the lists of updates to send of all other client with the same id
# Param type: is type of event
# Param src: is the relative path of the event
# Param dst: is optional for move event is the dst location and for create event is the type sile or directory
# Param sub_dict: is the dictionary of all updates list to this id
# Param num_sub :is the sub_num of the client that send the event
def addEvent(type, src, dst, sub_dict, num_sub):
    # create the string that represent eupdate
    event = type + '###' + src
    if dst != '':
        event = event + '###' + dst
    # for every client of this id add the event except the client that send the event
    for key in sub_dict.keys():
        if key == int.from_bytes(num_sub, 'big'):
            continue
        sub_dict[key].append(event)


# Function name: created
# Function operation: create a file or directory when client send created change
# Param numFolder: the name of the folder in the server with the backup of the client directory
# Param client_socket: the socket that is connected to the client
# Param dict: the lists of updates to send of all clients with the same id
def created(numFolder, client_socket, dict):
    # get the sub id of the client
    subid = client_socket.recv(4)
    size = client_socket.recv(4)
    # get the what created file or directory
    type = client_socket.recv(int.from_bytes(size, 'big'))
    name = ''
    kind = 'dir'
    if type == b'directory':
        # get the relative path to the new directory
        size = client_socket.recv(4)
        name = client_socket.recv(int.from_bytes(size, 'big'))
        # get the absolut path
        path = os.path.join(os.getcwd(), str(numFolder))
        # create the directory
        if not os.path.isdir(os.path.join(path, name.decode())):
            os.makedirs(os.path.join(path, name.decode()))
    else:
        kind = 'file'
        # get the relative path to the new directory
        size = client_socket.recv(4)
        name = client_socket.recv(int.from_bytes(size, 'big'))
        # get the absolut path
        path = os.path.join(os.getcwd(), str(numFolder))
        # get the file's size and create him
        file_size = client_socket.recv(4)
        f = open(os.path.join(path, name.decode()), 'wb')
        file_size = int.from_bytes(file_size, 'big')
        while file_size > 0:
            # write the new file
            info = client_socket.recv(min(1000000, file_size))
            f.write(info)
            file_size -= len(info)
        f.close()
    # add the event to the updates lists
    addEvent('created', name.decode(), kind, dict, subid)


# Function name: deleted
# Function operation: delete a file or directory when client send deleted change
# Param numFolder: the name of the folder in the server with the backup of the client directory
# Param client_socket: the socket that is connected to the client
# Param dict: the lists of updates to send of all clients with the same id
def deleted(num_folder, client_socket, dict):
    # get the sub id of the client
    subid = client_socket.recv(4)
    size = client_socket.recv(4)
    # get the relative path to delete
    name = client_socket.recv(int.from_bytes(size, 'big'))
    # get the absolut path
    src_path = os.path.join(os.getcwd(), str(num_folder))
    # send the path to deleted
    utils.delete(os.path.join(src_path, name.decode()))
    # add the event to the updates lists
    addEvent('deleted', name.decode(), '', dict, subid)


# Function name: moved
# Function operation: rename directory when client send moved change
# Param numFolder: the name of the folder in the server with the backup of the client directory
# Param client_socket: the socket that is connected to the client
# Param dict: the lists of updates to send of all clients with the same id
def moved(num_folder, client_socket, dict):
    # get the sub id of the client
    subid = client_socket.recv(4)
    size = client_socket.recv(4)
    # get the relative path to the directory
    src_name = client_socket.recv(int.from_bytes(size, 'big'))
    src_path = os.path.join(os.getcwd(), str(num_folder))
    dst_path = src_path
    # get the absolut path
    src_path = os.path.join(src_path, src_name.decode())
    size = client_socket.recv(4)
    # get the relative path to the new place of the directory
    dst_name = client_socket.recv(int.from_bytes(size, 'big'))
    dst_path = os.path.join(dst_path, dst_name.decode())
    # moved the directory
    if os.path.isdir(src_path):
        os.renames(src_path, dst_path)
    # add the event to the updates lists
    addEvent('moved', src_name.decode(), dst_name.decode(), dict, subid)


# Function name: send_moved
# Function operation: send to client that happened moved in other client with same id
# Param client_socket: the socket that is connected to the client
# Param src: the relative path of the directory
# Param dst: the relative path to the new place of the directory
def send_moved(client_socket, src, dst):
    # send that happened move
    client_socket.send(b'move')
    # send the src relative path
    client_socket.send(len(src).to_bytes(4, 'big'))
    client_socket.send(src.encode())
    # send the dst relative path
    client_socket.send(len(dst).to_bytes(4, 'big'))
    client_socket.send(dst.encode())


# Function name: send_created
# Function operation: send to client that happened created in other client with same id
# Param client_socket: the socket that is connected to the client
# Param path: the relative path of the directory ofr file that created
# Param type: if need to create file or directory
# Param num_folder: the num folder with the backup on the server
def send_created(client_socket, path, type, num_folder):
    # send that happened created
    client_socket.send(b'crea')
    # send if created file or directory
    client_socket.send(len(type).to_bytes(4, 'big'))
    client_socket.send(type.encode())
    # send the relative path of the file or the directory
    client_socket.send(len(path).to_bytes(4, 'big'))
    client_socket.send(path.encode())
    file = os.path.join(os.getcwd(), str(num_folder))
    file = os.path.join(file, path)
    # send the file size
    client_socket.send(os.path.getsize(file).to_bytes(4, 'big'))
    if type == 'file':
        # send the file
        with open(file) as f:
            while True:
                data = f.read(1_000_000)
                if not data:
                    break
                client_socket.send(data)
            f.close()


# Function name: send_deleted
# Function operation: send to client that happened deleted in other client with same id
# Param client_socket: the socket that is connected to the client
# Param path: the relative path of the directory ofr file that created
def send_deleted(client_socket, path):
    # send that heppened deleted
    client_socket.send(b'dele')
    # send the relative path to the file or directory to delete
    client_socket.send(len(path).to_bytes(4, 'big'))
    client_socket.send(path.encode())


# Function name: send_update
# Function operation: send to client all the updates that happened in other clients with the same id
# Param num_folder: the num folder with the backup on the server
# Param client_socket: the socket that is connected to the client
# Param events: the list of the updates to send
def send_update(num_folder, client_socket, events):
    # send the num of updates that happened
    client_socket.send(len(events).to_bytes(4, 'big'))
    for event in events:
        update = event.split('###')
        # send the update
        if update[0] == 'moved':
            send_moved(client_socket, update[1], update[2])
        elif update[0] == 'deleted':
            send_deleted(client_socket, update[1])
        else:
            send_created(client_socket, update[1], update[2], num_folder)
    # clear the list of updates of the client
    events.clear()


# Function name: main
if __name__ == '__main__':
    # get Tcp socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # get num port
    server.bind(('', int(sys.argv[1])))
    server.listen(5)
    # initialize data structures
    id_list = {}
    id_to_num = {}
    num_client = 0
    while True:
        # connect to client
        client_socket, client_address = server.accept()
        # get from client type of operation
        data = client_socket.recv(3)
        # new client with exist id
        if data == b'old':
            # get the id
            data = client_socket.recv(128)
            numFolder = id_to_num[data.decode()]
            # send sub id
            id_list[data.decode()][len(id_list[data.decode()]) + 1] = []
            client_socket.send((len(id_list[data.decode()])).to_bytes(4, 'big'))
            # send the backup
            utils.sendFolder(client_socket, os.path.join(os.getcwd(), str(numFolder)))
        # new client
        elif data == b'new':
            # rand new id
            id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
            id_list[id] = {}
            id_to_num[id] = num_client
            num_client += 1
            id_list[id][1] = []
            # send id and sub id
            client_socket.send(id.encode())
            print(id)
            client_socket.send((1).to_bytes(4, 'big'))
            dirName = os.path.join(os.getcwd(), str(id_to_num[id]))
            os.mkdir(dirName)
            utils.getFolder(client_socket,dirName)
        # the client send update
        elif data == b'upd':
            # get client id
            data = client_socket.recv(128)
            numFolder = id_to_num[data.decode()]
            # get type of update
            size = client_socket.recv(4)
            upd_type = client_socket.recv(int.from_bytes(size, 'big'))
            # get the update
            if upd_type == b'created':
                created(numFolder, client_socket, id_list[data.decode()])
            elif upd_type == b'renamed':
                moved(numFolder, client_socket, id_list[data.decode()])
            elif upd_type == b'deleted':
                deleted(numFolder, client_socket, id_list[data.decode()])
        # the client ask for updates
        elif data == b'get':
            # get client id
            data = client_socket.recv(128)
            numFolder = id_to_num[data.decode()]
            # get client sub id
            subid = client_socket.recv(4)
            # send all the updates
            send_update(numFolder, client_socket, id_list[data.decode()][int.from_bytes(subid, 'big')])
        client_socket.close()
