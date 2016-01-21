#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2014 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import os
from resources.lib.publishers.log import LogPublisher
import resources.lib.publishers.loop as loop
import resources.lib.publishers.log as log
from resources.lib.publishers.loop import LoopPublisher
from resources.lib.publishers.watchdog import WatchdogPublisher
from resources.lib.pubsub import Dispatcher, Subscriber, Message, Topic
from resources.lib.tests.stubs import *
from flexmock import flexmock
from Queue import Queue
import threading
import time

def printlog(msg, loglevel=0):
    print msg

flexmock(xbmc, log=printlog)

def sleep(xtime):
    time.sleep(xtime/1000.0)


class testSubscriber(Subscriber):
    def __init__(self):
        super(testSubscriber, self).__init__()
        self.testq = Queue()

    def notify(self, message):
        self.testq.put(message)

class testWatchdog(object):
    def __init__(self):
        self.publisher=None
        self.dispatcher=None
        self.subscriber=None
        self.topic=None
        self.folder=None

    def setup(self):
        self.folder = 'C:\\Users\\Ken User\\AppData\\Roaming\\Kodi\\addons\\service.kodi.callbacks\\resources\\lib\\tests\\'
        watchdogSettings = [{'folder':self.folder, 'patterns':'*.txt', 'ignore_patterns':'', 'ignore_directories':'',
                            'recursive':False, 'key':'E1'}]
        self.dispatcher = Dispatcher()
        self.subscriber = testSubscriber()
        self.topic = Topic('onFileSystemChange','E1')
        self.subscriber.addTopic(self.topic)
        self.dispatcher.addSubscriber(self.subscriber)
        self.publisher = WatchdogPublisher(self.dispatcher, watchdogSettings)
        self.dispatcher.start()

    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testWatchdogPublisherCreate(self):
        fn = '%s%s' %(self.folder,'test.txt')
        if os.path.exists(fn):
            os.remove(fn)
        self.publisher.start()
        time.sleep(1)
        with open(fn, 'w') as f:
            f.writelines('test')
        time.sleep(0.5)
        self.publisher.abort()
        self.dispatcher.abort()
        os.remove(fn)
        try:
            message = self.subscriber.testq.get(timeout=0.5)
        except:
            message = None
        assert isinstance(message, Message)
        assert message.topic == self.topic
        assert message.kwargs['path'] == fn
        assert message.kwargs['event'] == 'created'

    def testWatchdogPublisherDelete(self):
        fn = '%s%s' %(self.folder,'test.txt')
        if os.path.exists(fn) is False:
            with open(fn, 'w') as f:
                f.writelines('test')
        self.publisher.start()
        time.sleep(1)
        os.remove(fn)
        time.sleep(0.5)
        self.publisher.abort()
        self.dispatcher.abort()
        try:
            message = self.subscriber.testq.get(timeout=0.5)
        except:
            message = None
        assert isinstance(message, Message)
        assert message.topic == self.topic
        assert message.kwargs['path'] == fn
        assert message.kwargs['event'] == 'deleted'

    def testWatchdogPublisherModify(self):
        fn = '%s%s' %(self.folder,'test.txt')
        if os.path.exists(fn) is False:
            with open(fn, 'w') as f:
                f.writelines('test')
        self.publisher.start()
        time.sleep(1)
        with open(fn, 'a') as f:
            f.writelines('test2')
        time.sleep(0.5)
        self.publisher.abort()
        self.dispatcher.abort()
        try:
            message =self. subscriber.testq.get(timeout=0.5)
        except:
            message = None
        finally:
            os.remove(fn)
        assert isinstance(message, Message)
        assert message.topic == self.topic
        assert message.kwargs['path'] == fn
        assert message.kwargs['event'] == 'modified'

class testLoop(object):
    def __init__(self):
        self.publisher=None
        self.dispatcher=None
        self.subscriber=None
        self.globalidletime=None
        self.starttime = None
        self.topics = None


    def getGlobalIdleTime(self):
        if self.globalidletime is None:
            self.starttime = time.time()
            self.globalidletime = 0
            return 0
        else:
            self.globalidletime = int(time.time()-self.starttime)
            return self.globalidletime

    def getStereoMode(self):
        if self.getGlobalIdleTime() < 2:
            return 'off'
        else:
            return 'split_vertical'

    def getCurrentWindowId(self):
        git = self.getGlobalIdleTime()
        if git <2:
            return 10000
        elif git >=2 and git<4:
            return 10001
        else:
            return 10002

    def getProfileString(self):
        if self.getGlobalIdleTime() < 2:
            return 'Bob'
        else:
            return 'Mary'

    def setup(self):
        flexmock(loop.xbmc, getGlobalIdleTime=self.getGlobalIdleTime)
        flexmock(loop.xbmc, sleep=sleep)
        flexmock(loop, getStereoscopicMode=self.getStereoMode)
        flexmock(loop, getProfileString=self.getProfileString)
        flexmock(loop.xbmc.Player, isPlaying=False)
        flexmock(loop.xbmcgui, getCurrentWindowId=self.getCurrentWindowId)
        self.dispatcher = Dispatcher()
        self.subscriber = testSubscriber()


    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testLoopIdle(self):
        self.topics = [Topic('onIdle','E1'), Topic('onIdle', 'E2')]
        for topic in self.topics:
            self.subscriber.addTopic(topic)
        self.dispatcher.addSubscriber(self.subscriber)
        idleSettings = {'E1':3, 'E2':5}
        self.publisher = LoopPublisher(self.dispatcher, idleT=idleSettings)
        self.dispatcher.start()
        self.publisher.start()
        time.sleep(7)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics


    def testStereoModeChange(self):
        self.topics = [Topic('onStereoModeChange')]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.publisher = LoopPublisher(self.dispatcher)
        self.dispatcher.start()
        self.publisher.start()
        time.sleep(5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testOnWindowOpen(self):
        self.topics = [Topic('onWindowOpen','E1' )]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.publisher = LoopPublisher(self.dispatcher, owids={10001:'E1'})
        self.dispatcher.start()
        self.publisher.start()
        time.sleep(5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testOnWindowClose(self):
        self.topics = [Topic('onWindowClose','E1' )]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.publisher = LoopPublisher(self.dispatcher, cwids={10001:'E1'})
        self.dispatcher.start()
        self.publisher.start()
        time.sleep(5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testProfileChange(self):
        self.topics = [Topic('onProfileChange')]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.publisher = LoopPublisher(self.dispatcher)
        self.dispatcher.start()
        self.publisher.start()
        time.sleep(5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

def logSimulate():
    import random, string
    fn = 'C:\\Users\\Ken User\\AppData\\Roaming\\Kodi\\addons\\service.kodi.callbacks\\resources\\lib\\tests\\kodi.log'
    randomstring = ''.join(random.choice(string.lowercase) for i in range(30))
    targetstring = '%s%s%s' %(randomstring[:12],'kodi_callbacks',randomstring[20:])
    for i in xrange(0,10):
        with open(fn, 'a') as f:
            if i == 5:
                f.writelines(targetstring)
            else:
                f.writelines(randomstring)
        time.sleep(0.25)

class testLog(object):
    fn = 'C:\\Users\\Ken User\\AppData\\Roaming\\Kodi\\addons\\service.kodi.callbacks\\resources\\lib\\tests\\kodi.log'

    def __init__(self):
        self.publisher=None
        self.dispatcher=None
        self.subscriber=None
        self.globalidletime=None
        self.starttime = None
        self.topics = None

    @staticmethod
    def logSimulate():
        import random, string
        randomstring = ''.join(random.choice(string.lowercase) for i in range(30)) + '\n'
        targetstring = '%s%s%s' %(randomstring[:12],'kodi_callbacks',randomstring[20:])
        for i in xrange(0,10):
            with open(testLog.fn, 'a') as f:
                if i == 5:
                    f.writelines(targetstring)
                else:
                    f.writelines(randomstring)
            time.sleep(0.25)

    def setup(self):
        flexmock(log, logfn=testLog.fn)
        flexmock(log.xbmc, log=printlog)
        flexmock(log.xbmc, sleep=sleep)
        self.dispatcher = Dispatcher()
        self.subscriber = testSubscriber()

    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testLogSimple(self):
        self.topics = [Topic('onLogSimple','E1')]
        settings = [{'matchIf':'kodi_callbacks', 'rejectIf':'', 'eventId':'E1'}]
        self.publisher = LogPublisher(self.dispatcher)
        self.publisher.add_simple_checks(settings)
        try:
            os.remove(testLog.fn)
        except:
            pass
        finally:
            with open(testLog.fn, 'w') as f:
                f.writelines('')
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.dispatcher.start()
        self.publisher.start()
        t = threading.Thread(target=testLog.logSimulate)
        t.start()
        t.join()
        self.publisher.abort()
        self.dispatcher.abort()
        time.sleep(2)
        try:
            os.remove(testLog.fn)
        except:
            pass
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testLogRegex(self):
        self.topics = [Topic('onLogRegex','E1')]
        settings = [{'matchIf':'kodi_callbacks', 'rejectIf':'', 'eventId':'E1'}]
        self.publisher = LogPublisher(self.dispatcher)
        self.publisher.add_regex_checks(settings)
        try:
            os.remove(testLog.fn)
        except:
            pass
        finally:
            with open(testLog.fn, 'w') as f:
                f.writelines('')
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.dispatcher.start()
        self.publisher.start()
        t = threading.Thread(target=testLog.logSimulate)
        t.start()
        t.join()
        self.publisher.abort()
        self.dispatcher.abort()
        time.sleep(2)
        try:
            os.remove(testLog.fn)
        except Exception as e:
            pass
        messages = []
        try:
            while self.subscriber.testq.empty() is False:
                message = self.subscriber.testq.get(timeout=0.5)
                messages.append(message)
        except Exception as e:
            messages = []
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics
