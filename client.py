import os
import socket
import sys
import utils
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

myId = b''
mySubId = b''
updates = []


# function name: is_upt
# function operation: check if event origin is from previous update
# Param event: the event to check
def is_upt(event):
    event_str = event.event_type + event.src_path
    global updates
    # iterate through list of latest events and check if exists, if yes, remove from list and skip
    for str in updates:
        if event_str == str:
            updates.remove(event_str)
            return True
    # if got here, return false
    return False


# function name: on_created
# function operation: take action upon creation event
# Param event: the event to check
def on_created(event):
    # ask for updates
    receive_update()
    # check if event came from previous update, if yes, skip
    if is_upt(event):
        return
    # get socket and connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((sys.argv[1], int(sys.argv[2])))
    # send server to await update
    sock.send(b'upd')
    # send server current id
    sock.send(myId)
    # send server to await for creation
    sock.send(len('created').to_bytes(4, 'big'))
    sock.send('created'.encode())
    # send server sub id
    sock.send(mySubId)
    # get relative path
    updated_path = os.path.relpath(event.src_path, sys.argv[3])
    # if event is a directory, send as directory
    if event.is_directory:
        sock.send(len('directory').to_bytes(4, 'big'))
        sock.send('directory'.encode())
        sock.send(len(updated_path).to_bytes(4, 'big'))
        sock.send(updated_path.encode())
    # else, must be a file, send as file
    else:
        sock.send(len('file').to_bytes(4, 'big'))
        sock.send('file'.encode())
        sock.send(len(updated_path).to_bytes(4, 'big'))
        sock.send(updated_path.encode())
        # get the file size, and report to server, and send
        file_size = os.path.getsize(event.src_path)
        sock.send(file_size.to_bytes(4, 'big'))
        f = open(event.src_path, 'rb')
        # Send the file in chunks so large files can be handled.
        while True:
            data = f.read(1_000_000)
            if not data:
                break
            sock.send(data)
            # done
        f.close()


# function name: on_deleted
# function operation: take action upon deletion event
# Param event: the event to check
def on_deleted(event):
    # ask for updates
    receive_update()
    # check if event came from previous update, if yes, skip
    if is_upt(event):
        return
    # get socket and connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((sys.argv[1], int(sys.argv[2])))
    # send server to await update
    sock.send(b'upd')
    # send server current id
    sock.send(myId)
    # send server to await deletion
    sock.send(len('deleted').to_bytes(4, 'big'))
    sock.send('deleted'.encode())
    sock.send(mySubId)
    # get relative path, and send
    updated_path = os.path.relpath(event.src_path, sys.argv[3])
    sock.send(len(updated_path).to_bytes(4, 'big'))
    sock.send(updated_path.encode())


# function name: on_modified
# function operation: take action upon modification event
# Param event: the event to check
def on_modified(event):
    # if event is a file, send to create function
    if not event.is_directory:
        on_created(event)
    # else, if directory does not exist, send to delete function
    elif not os.path.isdir(event.src_path):
        on_deleted(event)
    # if got here, ignore


# function name: on_moved
# function operation: take action upon moved event
# Param event: the event to check
def on_moved(event):
    # ask for updates
    receive_update()
    # check if event came from previous update, if yes, skip
    if is_upt(event):
        return
    # check if event is a directory
    if event.is_directory:
        # get socket and connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((sys.argv[1], int(sys.argv[2])))
        # send server to await update
        sock.send(b'upd')
        # send server id
        sock.send(myId)
        # send server to await renamed event
        sock.send(len('renamed').to_bytes(4, 'big'))
        sock.send('renamed'.encode())
        sock.send(mySubId)
        # get relative path of src and dst of move event
        updated_path = os.path.relpath(event.src_path, sys.argv[3])
        sock.send(len(updated_path).to_bytes(4, 'big'))
        sock.send(updated_path.encode())
        updated_path = os.path.relpath(event.dest_path, sys.argv[3])
        sock.send(len(updated_path).to_bytes(4, 'big'))
        sock.send(updated_path.encode())


# function name: receive_update
# function operation: check and receive new updates from server
def receive_update():
    # get socket and connect
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.connect((sys.argv[1], int(sys.argv[2])))
    # send server to await request to get updates
    soc.send(b'get')
    # send server id
    soc.send(myId)
    # send server sub id
    soc.send(mySubId)
    # receive amount of events from server
    events_amount = int.from_bytes(soc.recv(4), 'big')
    # receive each event, for amount of events
    for i in range(0, events_amount):
        # receive event
        event_type = soc.recv(4).decode()
        # check type of event, and call corresponding function
        # if event is move
        if event_type == 'move':
            # get the size of the event
            size = int.from_bytes(soc.recv(4), 'big')
            # get src path
            src = os.path.join(sys.argv[3], soc.recv(size).decode())
            size = int.from_bytes(soc.recv(4), 'big')
            # get dst path
            dst = os.path.join(sys.argv[3], soc.recv(size).decode())
            global updates
            # append to list of updates
            updates.append('moved' + src)
            if os.path.isdir(src):
                os.renames(src, dst)
        # if event is creation
        elif event_type == 'crea':
            # get the size of the event
            size = int.from_bytes(soc.recv(4), 'big')
            crea_type = soc.recv(size).decode()
            # get src path
            size = int.from_bytes(soc.recv(4), 'big')
            src = os.path.join(sys.argv[3], soc.recv(size).decode())
            # append to list of events
            updates.append('created' + src)
            # check if event is a directory, if yes create
            if crea_type == 'dir':
                os.mkdir(src)
            # else, must be file, create
            else:
                # get size and send in chunks
                size = int.from_bytes(soc.recv(4), 'big')
                f = open(src, 'wb')
                while size > 0:
                    info = soc.recv(min(1000000, size))
                    f.write(info)
                    size -= len(info)
                    # done
                f.close()
        # if event is deletion
        elif event_type == 'dele':
            # get the size of the event
            size = int.from_bytes(soc.recv(4), 'big')
            # get src path
            src = os.path.join(sys.argv[3], soc.recv(size).decode())
            # append to list of events, and delete
            updates.append('deleted' + src)
            utils.delete(src)


# function name: main
if __name__ == "__main__":
    # receive a socket, and connect
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((sys.argv[1], int(sys.argv[2])))
    # if there 6 arguments, must be old user
    if len(sys.argv) == 6:
        if not os.path.isdir(sys.argv[3]):
            os.mkdir(sys.argv[3])
        myId = sys.argv[5].encode()
        # prepare server for new user
        s.send(b'old')
        # send id
        s.send(myId)
        # receive sub id, and get folders
        mySubId = s.recv(4)
        utils.getFolder(s, sys.argv[3])
        # else, must be new user, get id and sub id, and upload folders
    else:
        # prepare server for old user
        s.send(b'new')
        # get new id
        myId = s.recv(128)
        # get new sub id
        mySubId = s.recv(4)
        # upload folders
        utils.sendFolder(s, sys.argv[3])
        # done
    s.close()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    # get path from argument
    path = sys.argv[3]
    # get an event handler
    event_handler = LoggingEventHandler()
    # get an observer
    observer = Observer()
    # set schedule for observer
    observer.schedule(event_handler, path, recursive=True)
    # override default event handler function
    event_handler.on_created = on_created
    event_handler.on_modified = on_modified
    event_handler.on_deleted = on_deleted
    event_handler.on_moved = on_moved
    # start observing
    observer.start()
    try:
        # loop to control flow
        while True:
            # sleep
            time.sleep(int(sys.argv[4]))
            # ask for updates
            receive_update()

    finally:
        # if failed, stop observing
        observer.stop()
        observer.join()
