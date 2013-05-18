import tornado.ioloop
import time
import tornado_dns
import Queue
import datetime
import sys
import threading

start_time = datetime.datetime.now()

success_cnt = 0
timeout_cnt = 0
nonexist_cnt = 0
crash_cnt = 0
other_cnt = 0

l = threading.Lock()

def main():
    io_loop = tornado.ioloop.IOLoop.instance()
    q = Queue.Queue()

    def do_next():
        try:
            url = q.get(block=False)
            tornado_dns.lookup(url, success, errback, timeout=5000)
        except Queue.Empty:
            io_loop.stop()
            print 'success', success_cnt
            print 'timeout', timeout_cnt
            print 'nonexist', nonexist_cnt
            print 'crash', crash_cnt
            print 'other', other_cnt
            end_time = datetime.datetime.now()
            print 'time', end_time - start_time
            pass

    def success(addresses):
        global success_cnt
        with l:
            print 'addresses: %s' % (addresses,)
            end_time = datetime.datetime.now()
            success_cnt += 1
            do_next()
            q.task_done()

    def errback(code):
        with l:
            if code == tornado_dns.errors.TIMEOUT:
                global timeout_cnt
                timeout_cnt += 1
                print 'time out'
            elif code == -1:
                global nonexist_cnt
                nonexist_cnt += 1
            elif code == -2:
                global crash_cnt
                crash_cnt += 1
            else:
                global other_cnt
                other_cnt += 1
            do_next()
            q.task_done()

    alpha = 'abcdefghijklmnopqrstuvwxyz'
    for a in alpha:
        for b in alpha:
            for c in alpha:
                for d in alpha:
                    q.put(a+b+c+d+'.com')

    for i in range(100):
        url = q.get()
        tornado_dns.lookup(url, success, errback, timeout=5000)
    io_loop.start()


if __name__ == '__main__':
    main()
