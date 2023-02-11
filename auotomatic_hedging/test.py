import threading

# Creating a lock object
lock = threading.Lock()

# Creating an rlock object
rlock = threading.RLock()


def func_one():
    # Acquire the lock
    lock.acquire()
    print('Fun one acquired the lock')
    # Release the lock
    lock.release()


def func_two():
    # Acquire the lock
    rlock.acquire()
    print('Fun two acquired the RLock')
    # Release the lock
    rlock.release()


# Create two threads as follows
thread1 = threading.Thread(target=func_one)
thread2 = threading.Thread(target=func_two)

# Start the threads
thread1.start()
thread2.start()

# join the threads to get them executed
thread1.join()
thread2.join()
