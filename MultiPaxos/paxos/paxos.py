#!/usr/bin/env python3.6
#requires python3

import pickle
import sys
import socket
import struct
import time
import threading
from collections import defaultdict

BUFFER_SIZE = 512
#increase buffer for catchup
BUFFER_SIZE2 = 4096 * 30

def serialize(m):
    #wraps pickle
    return pickle.dumps(m)
def unserialize(m):
    #wrapper
    return pickle.loads(m)
def mcast_receiver(hostport):
    """create a multicast socket listening to the address"""
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind(hostport)
    mcast_group = struct.pack("4sl", socket.inet_aton(hostport[0]), socket.INADDR_ANY)
    recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mcast_group)
    return recv_sock
def mcast_sender():
    """create a udp socket"""
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    return send_sock
def parse_cfg(cfgpath):
    cfg = {}
    with open(cfgpath, 'r') as cfgfile:
        for line in cfgfile:
            (role, host, port) = line.split()
            cfg[role] = (host, int(port))
    return cfg

# ----------------------------------------------------

class Msg(object):
    #class for handling all msgs
    def __init__(self,phase,value=None,id=0,rnd=0,crnd=0,vrnd=0,vval=0,cval=0,instance=0,order=None,values=None):
        self.value = value
        self.phase = phase
        self.id = id
        self.rnd = rnd
        self.crnd = crnd
        self.vrnd = vrnd
        self.vval = vval
        self.cval = cval
        self.instance = instance
        self.Qa1 = {}
        self.Qa2 = {}
        self.Vals = {}
        ## for catch up
        self.order = order
        self.values = values

# ----------------------------------------------------

class acceptor(object):
    def __init__(self,config,id):
        self.config = config
        self.id = id
        self.aid = id
        print('-> acceptor', id)
        self.r = mcast_receiver(config['acceptors'])
        self.s = mcast_sender()
        self.listen()
    def handle_1B(self,msg):
        if msg.crnd > msg.rnd:
            msg.rnd = msg.crnd
            msg.phase = '1B'
            msg.id = self.id
            self.s.sendto(serialize(msg), self.config['proposers'])
    def handle_2B(self,msg):
        if msg.crnd >= msg.rnd:
            msg.vrnd = msg.crnd
            msg.vval = msg.cval
            msg.phase = '2B'
            msg.id = self.id
            self.s.sendto(serialize(msg), self.config['proposers'])
    def msg_handler(self,msg):
        msg = unserialize(msg)
        if msg.phase == '1A':
            self.handle_1B(msg)
        elif msg.phase == '2A':
            self.handle_2B(msg)
    def listen(self):
        while True:
            msg = self.r.recv(BUFFER_SIZE)
            self.msg_handler(msg)

class proposer(object):
    def __init__(self,config,id):
        self.config = config
        self.id = id
        self.decided = {}
        self.start_order = []
        self.decide_order = []
        #assume 1 failure, threshold to be 3-1= 2 acceptors
        self.failure_thresh = 3-1
        self.timeout_thresh = 3
        self.decide_order = defaultdict(int)
        self.alive = {}
        #leader starts off as 1
        self.leader_id = 1
        if self.id==self.leader_id:
            self.leader = True
        else:
            self.leader = False
        print('-> proposer', id)
        self.r = mcast_receiver(config['proposers'])
        self.s = mcast_sender()
        self.state = {}
        #for first quorum
        self.sent = {}
        #for second quorum
        self.decided = {}

        #listen for msg
        self.reciever = threading.Thread(target=self.listen)
        self.reciever.start()

        #send heartbeats
        self.heartbeats = threading.Thread(target=self.send_heartbeat,daemon=True)
        self.heartbeats.start()

        #listen to heartbeats to make sure leader is alive
        time.sleep(1)
        self.listen2leader = threading.Thread(target=self.listen_for_leader)
        self.listen2leader.start()

    def elect_leader(self):
        #reset dict to see who is dead
        self.alive ={}
        time.sleep(1.1)
        #we take the lowest id alive, to be the leader
        new_leader_id = min(self.alive.keys())
        if self.id==new_leader_id:
            self.leader=True
            print('Proposer{} I am new leader'.format(self.id))
        else:
            print("Proposer{} elect Proposer{} as leader".format(self.id,new_leader_id))
            self.leader_id = new_leader_id
            listen_leader = threading.Thread(target=self.listen_for_leader)
            listen_leader.start()

    def listen_for_leader(self):
        leader_not_dead =True
        if not self.leader:
            while leader_not_dead:
                time.sleep(1)
                delta_time = time.time() - self.alive[self.leader_id]
                if delta_time>=self.timeout_thresh:
                    print('Leader is dead!\nProposer{} timed out\nElect new leader'.format(self.leader_id))
                    leader_not_dead = False
                    elect_leader = threading.Thread(target=self.elect_leader)
                    elect_leader.start()

    def send_heartbeat(self):
        while True:
            m = Msg(phase='heartbeat',id=self.id,value=self.leader_id)
            time.sleep(.8)
            self.s.sendto(serialize(m), self.config['proposers'])

    def handle_heartbeat(self,msg):
        self.alive[msg.id] = time.time()
        self.last_beat = time.time()

    def handle_1A(self,msg):
        msg.phase = '1A'
        msg.crnd = int(str(self.id) + str(msg.crnd))
        self.state[msg.instance] = msg
        self.decided[msg.instance] = None
        self.sent[msg.instance] = None
        self.s.sendto(serialize(msg), self.config['acceptors'])

    def handle_2A(self,msg):
            if self.state[msg.instance].crnd == msg.rnd:
                self.state[msg.instance].Qa1[msg.id] = True
                self.state[msg.instance].Vals[msg.vrnd] = msg.vval
                # check quorum size is above 2
                if len(self.state[msg.instance].Qa1.keys()) >= self.failure_thresh:
                    #check if the first quorum has already been previously reach, send once!
                    if self.sent[msg.instance]==None:
                        self.sent[msg.instance] = True
                        # if there are no conflicting vrnds, just take own value
                        if len(set(self.state[msg.instance].Vals.keys()))==1:
                            msg.cval = msg.value
                        #if conflict then check for largest value
                        else:
                            k = max(self.state[msg.instance].Vals.keys())
                            v = self.state[msg.instance].Vals[k]
                            if k == 0:
                                msg.cval = msg.value
                            else:
                                msg.cval = v
                        msg.phase = '2A'
                        self.s.sendto(serialize(msg), self.config['acceptors'])

    def handle_decide(self,msg):
        if msg.vrnd == msg.crnd:
            self.state[msg.instance].Qa2[msg.id] = True
            #check quorum size is above 2
            if len(self.state[msg.instance].Qa2.keys()) >= self.failure_thresh:
                #if not decided, decide
                if self.decided[msg.instance] == None:
                    self.decided[msg.instance] = msg.cval
                    msg.phase='Decide'
                    msg.instance = (msg.id,self.decide_order[msg.id])
                    self.decide_order[msg.id]+=1
                    self.s.sendto(serialize(msg), self.config['learners'])

    def msg_handler(self,msg):
        msg = unserialize(msg)
        if msg.phase == "heartbeat":
            self.handle_heartbeat(msg)
        if self.leader:
            if msg.phase == "Client":
                self.handle_1A(msg)
            elif msg.phase == '1B':
                self.handle_2A(msg)
            elif msg.phase == '2B':
                self.handle_decide(msg)

    def listen(self):
        while True:
            msg = self.r.recv(BUFFER_SIZE)
            self.msg_handler(msg)

class learner(object):
    def __init__(self,config,id):
        self.config = config
        self.id = id
        self.r = mcast_receiver(config['learners'])
        self.s = mcast_sender()
        self.learned = {}
        self.written = {}
        self.order = []
        self.values = []
        self.IO = defaultdict(dict)
        self.total_order = defaultdict(dict)
        self.last = defaultdict(int)
        catchup = threading.Thread(target=self.request_catchup)
        catchup.start()
        self.listen()

    def request_catchup(self):
        time.sleep(.001)
        m = Msg(phase='Request_catchup')
        self.s.sendto(serialize(m), self.config['learners'])

    def handle_catchup(self,msg):
        #if you are not caught up
        if len(self.total_order.keys())==0:
            self.total_order = msg.order
            # deliver msgs in the order
            for id in self.total_order.keys():
                for instance in range(len(self.total_order[id].keys())):
                    val = self.total_order[id][instance]
                    self.last[id]+=1
                    print(val,flush=True)

    def msg_replay(self):
        #only send catch up if you have been caught up
        if len(self.total_order.keys())>0:
            #send all msgs that have been decided, and their order
            m = Msg(phase="Catch_up", values=self.values,order=self.total_order)
            self.s.sendto(serialize(m), self.config['learners'])

    def process_in_total_order(self,msg):
        # process msg in total order
        delivered=False
        while not delivered:
            (id, instance)=msg.instance
            self.total_order[id][instance] =val= msg.vval
            #check to see if it is the msg we expect
            if instance == self.last[id]:
                # increase counter of last msg
                self.last[id] += 1
                #if not delivered yet
                if instance not in self.IO[id].keys():
                    # deliver msg
                    self.IO[id][instance]= val
                    delivered=True
                    print(val, flush=True)
            else:
                time.sleep(.0001)


    def msg_handler(self,msg):
        msg = unserialize(msg)
        if msg.phase=='Decide':
            self.process_in_total_order(msg)
            # self.write(msg)
        elif msg.phase=='Catch_up':
            self.handle_catchup(msg)
        elif msg.phase=='Request_catchup':
            self.msg_replay()

    def listen(self):
        while True:
            msg = self.r.recv(BUFFER_SIZE2)
            self.msg_handler(msg)

class client(object):
    def __init__(self,config,id):
        self.config = config
        self.id = id
        self.s = mcast_sender()
        self.instance = 0
        time.sleep(.8)
        self.request()

    def handle_request(self,value):
        phase = "Client"
        #create unique instance, for each client
        unique_instance = (self.id,self.instance)
        m = Msg(phase, value=value, instance=unique_instance)
        self.instance += 1
        self.s.sendto(serialize(m), config['proposers'])

    def request(self):
        for value in sys.stdin:
            value = value.strip()
            self.handle_request(value)
            time.sleep(.0008)

if __name__ == '__main__':
        cfgpath = sys.argv[1]
        config = parse_cfg(cfgpath)
        role = sys.argv[2]
        id = int(sys.argv[3])
        if role == 'acceptor':
            rolefunc = acceptor
        elif role == 'proposer':
            rolefunc = proposer
        elif role == 'learner':
            rolefunc = learner
        elif role == 'client':
            rolefunc = client
        rolefunc(config, id)
