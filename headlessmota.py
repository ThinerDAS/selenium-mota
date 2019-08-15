#!/usr/bin/python -i

# docker pull joyzoursky/python-chromedriver:2.7-alpine3.7-selenium

'''

Tiny attempt of headless mota.

'''

import sys
import os
import time
from selenium import webdriver


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.implicitly_wait(10)
    return driver


def extremeness(x):
    # table = [0,1,9,2,8,7,6,5,4]
    # if(x>9)
    if x <= 2:
        return x
    return 100-x


def manh_dist(tup1, tup2):
    return abs(tup1[0]-tup2[0])+abs(tup1[1]-tup2[1])


def zigzag_key(tup):
    x, y = tup
    return x+y, (x-y if (x+y) & 1 else y-x)


class MotaInstance(object):
    preaction = '''
    events.prototype._action_text = function(){core.doAction()};
    var f = function(func){
        return function(){
            if (arguments[0].time) arguments[0].time = 0;
            return func.apply(this, Array.prototype.slice.call(arguments));
        };
    };
    events.prototype.doEvent = f(events.prototype.doEvent);
    var f = function(func){
        return function(x,y){
            return func(x,1);
        };
    };
    //window.setInterval=f(window.setInterval);
    window.setTimeout=f(window.setTimeout);
    maps.prototype.drawAnimate = function (name, x, y, callback) {
        if(callback)callback();
        return -1;
    }
    var f = function(func){
        return function(){
            arguments[1] = 0;
            return func.apply(this, Array.prototype.slice.call(arguments));
        };
    };
    utils.prototype.hideWithAnimate = f(utils.prototype.hideWithAnimate)
    utils.prototype.showWithAnimate = f(utils.prototype.showWithAnimate)
    var f = function(func){
        return function(){
            ret = func.apply(this, Array.prototype.slice.call(arguments));
            ret.time = 0;
            return ret;
        };
    };
    events.prototype._changeFloor_getInfo = f(events.prototype._changeFloor_getInfo)
    control.prototype.setHeroMoveInterval = function (callback) {
        if (core.status.heroMoving > 0) return;
        core.status.heroMoving = 0;
        core.moveOneStep(core.nextX(), core.nextY());
        if (callback) callback();
    }
    ui.prototype.drawImage = function(){};
    '''

    def preinit(self):
        '''
        Certain operation for accelerating mota events
        '''
        self.exec_js(self.preaction)

    def __init__(self, path, **kwargs):
        '''
        path: mota project path
        '''
        path = os.path.abspath(path)
        if not path.endswith('index.html'):
            path = os.path.join(path, 'index.html')
        self.kwargs = kwargs
        self.url = 'file://'+path
        self.driver = get_driver()
        self.driver.get(self.url)
        # time.sleep(1)
        print self.driver.title
        self.preinit()
        self.start_game()
        self.wait_until_free()

    def exec_js(self, s, *args):
        '''
        Execute javascript
        '''
        return self.driver.execute_script(s, *args)

    def eval_js(self, s, *args):
        '''
        Execute javascript as expression and get the return value
        '''
        assert ';' not in s and '\n' not in s, 'Warning: you probably should use exec_js for multiple line javascript command'
        return self.exec_js('return '+s, *args)

    def start_game(self, hard='Hard'):
        '''
        start the game. Currently only used internally
        '''
        self.exec_js('core.events.startGame(arguments[0])', hard)

    def wait_until_free(self, trial=100, sleep_interval=0.04):
        '''
        Wait until all things are finished
        '''
        # 10s should be maximum as we cut the time
        for t in xrange(trial):
            locked = self.eval_js(
                '!core.status.played||core.status.lockControl||core.isMoving()')
            if locked == True:  # or locked is None:
                print 'Wait attempt', t
                print 'event', self.eval_js('core.status.event')
                time.sleep(sleep_interval)
            else:
                break
        else:
            raise Exception('time out')

    def generic_click_coord(self, x, y):
        '''
        Emulate clicking on coordinate
        '''
        self.wait_until_free()
        self.exec_js(
            'core.setAutomaticRoute(arguments[0],arguments[1],[])', x, y)
        # self.wait_until_free()

    def move_only_directly(self, x, y):
        '''
        Emulate clicking on coordinate, except that if moving directly is not available, it returns false and does nothing
        '''
        self.wait_until_free()
        ret = self.eval_js(
            'core.tryMoveDirectly(arguments[0],arguments[1])', x, y)
        # if ret:
        #    self.wait_until_free()
        return ret

    dirs = [(-1, 0), (0, -1), (1, 0), (0, 1)]

    def dirty_get_available(self):
        '''
        Fast but not compatible way of getting all events reachable - quick hack
        '''
        # this_map, hero_loc = self.eval_js(
        #    '[core.status.thisMap,core.status.hero.loc]')
        good_blocks, hero_loc = self.eval_js(
            '[core.status.thisMap.blocks.filter(function(x){return !x.disable}),core.status.hero.loc]'
        )
        # block_map = {(i['x'], i['y']): i for i in this_map['blocks']}
        block_map = {(i['x'], i['y']): i for i in good_blocks}

        l = []
        q = [(hero_loc['x'], hero_loc['y'])]
        s = set(q)
        evl = []
        while q:
            x, y = q.pop()
            l.append((x, y))
            for dx, dy in self.dirs:
                nx, ny = x+dx, y+dy
                if (nx, ny) not in s:
                    s.add((nx, ny))
                    if (nx, ny) not in block_map:
                        q.append((nx, ny))
                    else:
                        evl.append(block_map[nx, ny])
        return evl
    eat_set = []

    def auto_event_priority(self, e):
        if e['event']['cls'] == 'items':
            return 1
        elif e['id'] in self.eat_set:
            return 2
        # TODO: stair is 3
        return 0

    def simple_grab_all(self):
        '''
        grab treasures automaticly
        make it faster!
        '''
        while True:
            d = [(i['x'], i['y'], self.auto_event_priority(i))
                 for i in self.dirty_get_available() if self.auto_event_priority(i) > 0]
            # for i in d:
            #    print i
            if not d:
                return
            brave_loc = self.eval_js('core.status.hero.loc')
            x, y, _ = min(d, key=lambda t: extremeness(
                manh_dist(t, (brave_loc['x'], brave_loc['y']))))
            # assert self.move_only_directly(x, y), 'move directly failed'
            print 'Got x,y', x, y
            # print time.time()
            self.generic_click_coord(x, y)
            # print time.time()
            self.wait_until_free()
            # print time.time()
            # time.sleep(1)

    def savedata(self):
        '''
        get savedata object. this object should be usable directly when using json.dump in python to dump the object into an .h5save file.
        '''
        return self.eval_js('core.saveData()')

    def loaddata(self, obj):
        '''
        get savedata object. this object should be usable directly when using json.dump in python to dump the object into an .h5save file.
        '''
        return self.eval_js('core.loadData(arguments[0])', obj)

    # don't use this method! this method on a normal map will lag for seconds
    generate_directly_movable_script = '''
    var result = [];
    var bls = core.status.thisMap.blocks;
    for(var i=0;i<bls.length;i++){
        var bl = bls[i];
        for(var dir in core.utils.scan){
            var diff = core.utils.scan[dir]
            if(core.canMoveDirectly(bl.x+diff.x,bl.y+diff.y)>=0){
                result.push(bl);
                break;
            }
        }
    }
    return result;
    '''

    def generate_directly_movable(self):
        '''
        pure js way of getting movable events. VERY SLOW
        '''
        return self.exec_js(self.generate_directly_movable_script)

    def __del__(self):
        '''
        to avoid spamming the user's computer with chrome process
        '''
        self.driver.close()
