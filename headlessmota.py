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


def zigzag_key(tup):
    x, y = tup
    return x+y, (x-y if (x+y) & 1 else y-x)


class MotaInstance(object):
    preaction = '''
    core.events._action_text = function(data, x, y, prefix){data.time=0;return core.events._action_autoText(data, x, y, prefix);};
    var f = function(func){
        return function(x,y){
            return func(x,0);
        };
    };
    window.setInterval=f(window.setInterval);
    window.setTimeout=f(window.setTimeout);
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
        time.sleep(1)
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
        for _ in xrange(trial):
            locked = self.eval_js(
                '!core.status.played||core.status.lockControl||core.isMoving()')
            if locked == True:  # or locked is None:
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
        this_map, hero_loc = self.eval_js(
            '[core.status.thisMap,core.status.hero.loc]')
        block_map = {(i['x'], i['y']): i for i in this_map['blocks']
                     if not i.get('disable')}
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

    def simple_grab_all(self):
        '''
        grab treasures automaticly
        '''
        while True:
            d = [i for i in self.dirty_get_available() if i['event']['cls']
                 == 'items' or i['id'] in self.eat_set]
            d = [(i['x'], i['y'])for i in d]
            # for i in d:
            #    print i
            if not d:
                return
            x, y = min(d, key=zigzag_key)
            #assert self.move_only_directly(x, y), 'move directly failed'
            print 'Got x,y', x, y
            self.generic_click_coord(x, y)
            self.wait_until_free()
            #time.sleep(1)

    def savedata(self):
        '''
        get savedata object. this object should be usable directly when using json.dump in python to dump the object into an .h5save file.
        '''
        return self.eval_js('core.saveData()')

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
