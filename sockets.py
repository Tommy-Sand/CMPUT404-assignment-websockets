#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle, Tommy Sandanasamy
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

#CITATION: https://github.com/uofa-cmput404/cmput404-slides/tree/master/examples/WebSocketsExamples
#The help of this repo was used but code was not directly taken.

import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os
import sys
import logging

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()

clients = list()

def set_listener( entity, data ):
    ''' do something with the update ! '''
    for client in clients:
        #app.logger.debug(json.dumps({entity: entity, data: data}))
        client.put(json.dumps({entity: data}))

	
myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    index = open('./static/index.html', 'r')
    content = index.read()
    index.close()
    return content

def read_ws(ws, client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    while True:
        try:
            content = ws.receive() #Check websocket is open
            if(not content):
               continue
            content = json.loads(content)
            app.logger.debug(list(content.keys())[0])
            key = list(content.keys())[0]
            myWorld.set(key, content[key])
        except Exception as e:
            app.logger.debug(content)
            app.logger.debug(e)
            break

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    
    client_queue = queue.Queue()
    g = gevent.Greenlet.spawn(read_ws, ws, client_queue)
    clients.append(client_queue)
    init_world = myWorld.world()
    
    for i in init_world.keys():
        ws.send(json.dumps({i: init_world[i]}))
    while True:
        try:
            content = client_queue.get()
            if(content):
                if(content == "Closed"):
                    app.logger.debug("pre closing")
                    break
                app.logger.debug("sending content")
                ws.send(content)
        except:
            break
    app.logger.debug("Closing connection")
    g.kill()
    clients.remove(client_queue)


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    if(request.method == 'PUT'):
        data = flask_post_json()
        if(data['X'] == None or data['y'] == None):
            return 400
        if(data['X'] < 0 or data['y'] < 0):
            return 400
        myWorld.set(entity, data)
        return myWorld.get(entity)
    elif(request.method == "POST"):
        data = flask_post_json()
        for key in data.keys():
            myWorld.update(entity, key, data[key])
        return myWorld.get(entity)

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    if(request.method == 'GET'):
        return myWorld.world()
    elif(request.method == "POST"):
        json = flask_post_json()
        if(flask_post_json() != None):
            for key in json.keys():
                myWorld.set(key, json(key))
        return myWorld.world()

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return myWorld.get(entity) 


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    return myWorld.world()



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
