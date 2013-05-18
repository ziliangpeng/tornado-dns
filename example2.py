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
remain_item_cnt = 0

l = threading.Lock()

def main():
    io_loop = tornado.ioloop.IOLoop.instance()
    q = Queue.Queue()

    def do_next():
        try:
            url = q.get(block=False)
            tornado_dns.lookup(url, success, errback, timeout=5000)
        except Queue.Empty:
            if not remain_item_cnt:
                io_loop.stop()

    def success(addresses):
        global success_cnt, remain_item_cnt
        with l:
            print 'addresses: %s' % (addresses,)
            success_cnt += 1
            q.task_done()
            remain_item_cnt -= 1
            do_next()

    def errback(code):
        with l:
            if code == tornado_dns.errors.TIMEOUT:
                global timeout_cnt
                timeout_cnt += 1
            elif code == tornado_dns.errors.DOMAIN_NOT_EXIST:
                global nonexist_cnt
                nonexist_cnt += 1
            elif code == tornado_dns.errors.DNS_SERVER_FAILED:
                global crash_cnt
                crash_cnt += 1
            else:
                global other_cnt
                other_cnt += 1
            q.task_done()
            global remain_item_cnt
            remain_item_cnt -= 1
            do_next()

    alpha = 'abcdefghijklmnopqrstuvwxyz'
    for a in alpha:
        for b in alpha:
            for c in alpha:
                for d in alpha:
                    q.put(a+b+c+d+'.com')
                    global remain_item_cnt
                    remain_item_cnt += 1

    for i in range(1000):
        url = q.get()
        tornado_dns.lookup(url, success, errback, timeout=5000)
    io_loop.start()
    print 'success', success_cnt
    print 'timeout', timeout_cnt
    print 'nonexist', nonexist_cnt
    print 'crash', crash_cnt
    print 'other', other_cnt
    print 'all', success_cnt + timeout_cnt + nonexist_cnt + crash_cnt + other_cnt
    end_time = datetime.datetime.now()
    print 'time', end_time - start_time


if __name__ == '__main__':
    main()
