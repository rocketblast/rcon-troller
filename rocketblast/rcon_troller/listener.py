import traceback
import logging

import threading
import time
import re

from rocketblast.rcon import FormatFrostbiteClient as Client
from .plugin import Plugin

import select
import pygeoip
import os


class Listener(threading.Thread):
    servers = dict()

    pattern_pb_connect = re.compile(r'PunkBuster Server\: (?P<command>New Connection) \(slot #(?P<slot>\d+)\) (?P<ip>(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\:(?P<port>\d+) \[(?P<guid>.+?)\] "(?P<name>.+?)" \(seq (?P<sequence>\d+)\)\n')
    pattern_pb_guid = re.compile(r'PunkBuster Server\: Player GUID Computed (?P<guid>.+?)\(.+?\) \(slot #(?P<slot>\d+)\) (?P<ip>(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\:(?P<port>\d+) (?P<name>.+?)\n')
    pattern_pb_disconnect = re.compile(r'PunkBuster Server\: (?P<command>Lost Connection) \(slot #(?P<slot>\d+)\) (?P<ip>(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\:(?P<port>\d+) (?P<guid>.+?)\(.+?\) (?P<name>.+?)\n')
    pattern_pb_plist = re.compile(r'PunkBuster Server\: (?P<slot>\d+)[ ]* (?P<guid>.+?)\(.+?\) (?P<ip>(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\:(?P<port>\d+) (?P<status>.+?)[ ]* (?P<power>[-+]?\d*\.\d+|\d+) (?P<auth_rate>[-+]?\d*\.\d+|\d+) (?P<recent_ss>[-+]?\d*\.\d+|\d+) \((?P<os>.+?)\) "(?P<name>.+?)"\n')

    gi = pygeoip.GeoIP(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'GeoIP.dat'))
    gic = pygeoip.GeoIP(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'GeoLiteCity.dat'))

    def __init__(self, handle, ip, port, password, plugins=[]):
        super(Listener, self).__init__()

        self.__handle = handle
        self.__ip = ip
        self.__port = port
        self.__password = password

        self.__plugins = []
        self.__addons = []

        self.__timers = {}

        self.__users = {}
        self.__players = {}

        self.__server = {}

        self.__client = Client()

        self.__terminate = False
        self.__lock = threading.RLock()

        Listener.servers.update({handle: self})

        for item in plugins:
            package, name = item['name'].rsplit('.', 1) if item['name'].rfind('.') != -1 else [__name__, item['name']]
            module = __import__(package, fromlist=[name])

            plugin = getattr(module, name)

            if issubclass(plugin, Plugin):
                self.__plugins.append(plugin(self, **item['args']))
            else:
                self.__addons.append(plugin(**item['args']))

    @property
    def handle(self):
        return self.__handle

    @handle.setter
    def handle(self, value):
        raise Exception('attribute \'handle\' is read only')

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, value):
        raise Exception('attribute \'ip\' is read only')

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, value):
        raise Exception('attribute \'port\' is read only')

    @property
    def timers(self):
        return self.__timers

    @timers.setter
    def timers(self, value):
        raise Exception('attribute \'timers\' is read only')

    @property
    def users(self):
        return {k: v['object'] for k, v in iter(self.__users.items())}

    @users.setter
    def users(self, value):
        raise Exception('attribute \'users\' is read only')

    @property
    def players(self):
        # return {k: v for k, v in self.__players.iteritems() if v[:2] != '__'}
        return self.__players

    @players.setter
    def players(self, value):
        raise Exception('attribute \'players\' is read only')

    @property
    def server(self):
        return self.__server

    @server.setter
    def server(self, value):
        raise Exception('attribute \'server\' is read only')

    @property
    def client(self):
        return self.__client

    @client.setter
    def client(self, value):
        raise Exception('attribute \'client\' is read only')

    @property
    def lock(self):
        return self.__lock

    @lock.setter
    def lock(self, value):
        raise Exception('attribute \'lock\' is read only')

    @property
    def thread(self):
        return threading.current_thread()

    @thread.setter
    def thread(self, value):
        raise Exception('attribute \'thread\' is read only')

    def run(self):
        listener = Client()

        while not self.__terminate:
            time.sleep(0.01)

            for name in iter({k: v for k, v in iter(self.__users.items()) if time.time() - v['time'] > 60 * 5}.keys()):
                logging.info('Connected player timed out ({}): no join event for 5 minutes.'.format(name))
                del self.__users[name]

            try:
                if not self.__client.connected():
                    self.__client = Client(self.__ip, self.__port, self.__password, self.__lock)

                if not listener.connected():
                    self.__timers = {}

                    self.__users = {}
                    self.__players = {}

                    self.__server = {}

                    listener = Client(self.__ip, self.__port, self.__password)

                    listener.send(['admin.eventsEnabled', 'true'])

                    listener.send(['punkBuster.pb_sv_command', 'PB_SV_PList'])

                    self.__server.update(self.__client.serverinfo(self.__client.send(['serverInfo'])).get('values', {}))
                    if int(self.__server.get('numPlayers', -1)) > 0:
                        for player in iter(self.__client.formatplayers(self.__client.send(['admin.listPlayers', 'all'])).get('players', {}).values()):
                            if str(player.get('guid', '')) == '':
                                logging.error('NO EA GUID DURING STARTUP'.format(player))

                            self.__players.update({str(player.get('name', '')): {
                                'name': str(player.get('name', '')),
                                'ea_guid': str(player.get('guid', '')),
                                'detected': time.time(),
                                'team': int(player.get('teamId', -1)),
                                'squad': int(player.get('squadId', -1))}})

                    self.__timers.update({
                        'player_consistency': {
                            'class': self.__class__.__name__,
                            'time': time.time() + 60 * 5,
                            'interval': 60 * 5}})

#                    self.__timers.update({
#                        'heartbeat': {
#                            'class': self.__class__.__name__,
#                            'time': time.time() + 5,
#                            'interval': 5}})

                    logging.info('Successfully started event listener for {} ({})'.format(self.__handle, self.thread))
                    #print 'Successfully started listener for {} ({})'.format(self.__handle, self.thread)

                    for plugin in self.__plugins:
                        plugin.connected()

                for timerid, timer in iter({k: v for k, v in iter(self.__timers.items()) if time.time() - v.get('time', 0) > 0}.items()):

                    # Listener timers

                    if timer['class'] == self.__class__.__name__:

                        if timerid == 'player_consistency':
                            players = self.__client.formatplayers(self.__client.send(['admin.listPlayers', 'all'])).get('players', {})
                            difference = set(iter(self.__players.keys())).symmetric_difference(set(iter(players.keys())))
                            #logging.info('############## CHECK PLAYERS\n{}\n{}'.format(', '.join(str(key) for key in sorted(players.iterkeys())), ', '.join(str(key) for key in sorted(self.__players.iterkeys()))))
                            if len(difference):
                                logging.error('Players off {} {}\n{}\n{}'.format(len(difference), difference, ', '.join(str(key) for key in sorted(iter(players.keys()))), ', '.join(str(key) for key in sorted(iter(self.__players.keys())))))
                                for name in difference:
                                    if name in self.__users:
                                        print('{} is connecting, so he is OK'.format(name))
#                        if timerid == 'heartbeat':
#                            print timerid
#                            listener.send(['ping'])

                        if 'interval' in timer:
                            timer.update({'time': timer['time'] + timer['interval']})#? - time.time() - timer.get('time', 0)
                        else:
                            plugin.remove_timer(timerid)

                    # Plugin timers

                    for plugin in [v for v in self.__plugins if v.__class__.__name__ == timer['class']]:
                        plugin.on_timer(['rocketblast.on_timer', timerid, timer.get('interval', None), timer.get('arguments', None)])

                        if 'interval' in timer:
                            timer.update({'time': timer['time'] + timer['interval']})#? - time.time() - timer.get('time', 0)
                        else:
                            plugin.remove_timer(timerid)

                for player in iter(self.__players.values()):

                    # Plugin.player timers

                    for timerid, timer in iter({k: v for k, v in iter(player.get('__timers', {}).items()) if time.time() - v.get('time', 0) > 0}.items()):
                        for plugin in [v for v in self.__plugins if v.__class__.__name__ == timer['class']]:
                            plugin.on_timer(['rocketblast.on_player_timer', player['name'], timerid, timer.get('interval', None), timer.get('arguments', None)])

                        if 'interval' in timer:
                            timer.update({'time': timer['time'] + timer['interval']})#? - time.time() - timer.get('time', 0)
                        else:
                            plugin.remove_timer(timerid, player['name'])

                if select.select([listener.socket], [], [], 0.01)[0]:

                    # Force exception if the socket has died. Otherwise, the socket.recv() will wait indefinatelly since it is blocking.
                    # There must be other solutions to this.
                    self.__client.send(['ping'])

                    data = listener.listen()

                    #logging.info(data)

                    # Events

                    try:
                        if data[0] == "punkBuster.onMessage":# <message: string>
                            match_pb_connect = Listener.pattern_pb_connect.match(data[1])
                            match_pb_guid = Listener.pattern_pb_guid.match(data[1])
                            match_pb_disconnect = Listener.pattern_pb_disconnect.match(data[1])
                            match_pb_plist = Listener.pattern_pb_plist.match(data[1])

                            if match_pb_connect and match_pb_connect.group('name') in self.__players:
                                #print Listener.gic.record_by_addr(match_pb_connect.group('ip'))

                                self.__players.get(str(match_pb_connect.group('name')), {}).update({
                                    'ip': match_pb_connect.group('ip'),
                                    #'country': Listener.gi.country_code_by_addr(match_pb_connect.group('ip')),
                                    'geo': Listener.gic.record_by_addr(match_pb_connect.group('ip')),
                                    #'city': Listener.gic.record_by_addr(match_pb_connect.group('ip'))
                                    })
                                #self.__players.get(str(match_pb_connect.group('name')), {}).get('join_data', {}).update({
                                #    'authenticated': datetime.now(),
                                #    'slot': int(match_pb_connect.group('slot'))})
                                #self.__players.get(str(match_pb_connect.group('name')), {}).setdefault('source', []).append('Authenticated')
                                if match_pb_connect.group('guid') != '?':
                                    self.__players.get(str(match_pb_connect.group('name')), {}).update({
                                        'pb_guid': match_pb_connect.group('guid')})

                                for plugin in self.__plugins:
                                    plugin.on_pb(['rocketblast.on_pb_connect', match_pb_connect.group('name'), match_pb_connect.group('guid'), match_pb_connect.group('ip')])

                            elif match_pb_guid and match_pb_guid.group('name') in self.__players:
                                self.__players.get(str(match_pb_guid.group('name')), {}).update({
                                    'pb_guid': match_pb_guid.group('guid')})

                                for plugin in self.__plugins:
                                    plugin.on_pb(['rocketblast.on_pb_guid', match_pb_guid.group('name'), match_pb_guid.group('guid'), match_pb_guid.group('ip')])

                            elif match_pb_disconnect and match_pb_disconnect.group('name') in self.__players:
                                #for plugin in self.__plugins:
                                #    plugin.on_part(data)

                                try:
                                    del self.__players[match_pb_disconnect.group('name')]

                                    for plugin in self.__plugins:
                                        plugin.on_players(['rocketblast.on_player_change', len(self.__players), 'down'])

                                except KeyError:
                                    logging.error('Player does not exist 1 {}'.format(str(data[1])))
                                    print('Player does not exist 1 {}'.format(str(data[1])))

                            elif match_pb_plist and match_pb_plist.group('name') in self.__players:

                                self.__players.get(str(match_pb_plist.group('name')), {}).update({
                                    'ip': match_pb_plist.group('ip'),
                                    'pb_guid': match_pb_plist.group('guid'),
                                    #'country': Listener.gi.country_code_by_addr(match_pb_plist.group('ip')),
                                    'geo': Listener.gic.record_by_addr(match_pb_plist.group('ip')),
                                    #'city': Listener.gic.record_by_addr(match_pb_plist.group('ip'))
                                    })
                                #self.__players.get(str(match_pb_plist.group('name')), {}).get('join_data', {}).update({
                                #    'authenticated': datetime.now(),
                                #    'slot': int(match_pb_plist.group('slot'))})
                                if self.__players.get(str(match_pb_plist.group('name')), {})['pb_guid'] == '?':
                                    #Can this happen?
                                    logging.info('PBList returned a match without a valid PB GUID {}'.format(data))
                                    print( 'PBList returned a match without a valid PB GUID {}'.format(data))
                            else:
                                pass#print data

                                for plugin in self.__plugins:
                                    plugin.on_pb(data)

                        elif data[0] == "server.onLevelLoaded":# <level name: string> <gamemode: string> <roundsPlayed: int> <roundsTotal: int>
                            self.__server.update(self.__client.serverinfo(self.__client.send(['serverInfo'])).get('values', {}))

                            for plugin in self.__plugins:
                                plugin.on_load(data)

                        elif data[0] == "server.onRoundOver":# <winning team: Team ID>
                            continue

                        elif data[0] == "server.onRoundOverTeamScores":# <end-of-round scores: team scores>
                            continue

                        elif data[0] == "server.onRoundOverPlayers":# <end-of-round soldier info: player info block>
                            for plugin in self.__plugins:
                                plugin.on_over(data)

                        elif data[0] == "player.onJoin":# <soldier name: string> <id: GUID>
                            event, name, ea_guid = map(str, data)

                            if name in self.__users:
                                logging.error('Multiple join events {}'.format(name))
                                print( 'Multiple join events {}'.format(name))

                            if ea_guid in [None, '']:
                                logging.error('NO EA GUID&&&&& {}'.format(data))

                            self.__users.update({name: {
                                'object': {
                                    'name': name,
                                    'ea_guid': ea_guid,
                                    'joined': time.time()},
                                'time': time.time()}})

                            for plugin in self.__plugins:
                                plugin.on_connect(data)

                        elif data[0] == "player.onAuthenticated":# <soldier name: string>
                            event, name = map(str, data)
                            blarg = None
                            # Fix for reference before assignment

                            try:
                                self.__players.update({name: self.__users.pop(name)['object']})
                            except KeyError:
                                logging.error('Joined without connecting first {}, attempting to look up EA GUID'.format(name))
                                print( 'Joined without connecting first {}, attempting to look up EA GUID'.format(name))

                                blarg = self.__client.send(['admin.listPlayers', 'player', name])
                                ea_guid = self.__client.formatplayers(blarg).get('players', {}).get(name, {})['guid']

                                self.__players.update({name: {
                                    'name': name,
                                    'ea_guid': ea_guid,
                                    'joined': time.time()}})

                            if ea_guid in [None, '']:
                                logging.error('NO EA GUID%%%%%%% {}'.format(data + [ea_guid] + blarg))

                            for plugin in self.__plugins:
                                plugin.on_join(data)

                            for plugin in self.__plugins:
                                plugin.on_players(['rocketblast.on_player_change', len(self.__players), 'up'])

                        elif data[0] == "player.onLeave":# <soldier name: string> <soldier info: player info block>
                            if str(data[1]) not in self.__players:
                                logging.error('PLAYER NOT EXISTS but removed {}, {}'.format(str(data[1]), self.__players))
                            for plugin in self.__plugins:
                                plugin.on_part(data)

                            try:
                                del self.__players[str(data[1])]

                                for plugin in self.__plugins:
                                    plugin.on_players(['rocketblast.on_player_change', len(self.__players), 'down'])

                            except KeyError:
                                logging.error('Player does not exist 2 {}'.format(str(data[1])))
                                print( 'Player does not exist 2 {}'.format(str(data[1])))

                        elif data[0] == "player.onTeamChange":# <soldier name: player name> <team: Team ID> <squad: Squad ID>
                            event, name, team, squad = str(data[0]), str(data[1]), int(data[2]), int(data[3])

                            try:
                                self.__players[name].update({
                                    'team': team,
                                    'squad': squad})
                            except KeyError:
                                logging.error('Player does not exist 3 {}'.format(name))

                            for plugin in self.__plugins:
                                plugin.on_team(data)

                        elif data[0] == "player.onSquadChange":# <soldier name: player name> <team: Team ID> <squad: Squad ID>
                            event, name, team, squad = str(data[0]), str(data[1]), int(data[2]), int(data[3])

                            try:
                                self.__players[name].update({
                                    'team': team,
                                    'squad': squad})
                            except KeyError:
                                logging.error('Player does not exist 4 {}'.format(name))

                            for plugin in self.__plugins:
                                plugin.on_squad(data)

                        elif data[0] == "player.onSpawn":# <soldier name: string> <team: Team ID>
                            event, name, team = str(data[0]), str(data[1]), int(data[2])

                            try:
                                self.__players[name].update({
                                    'team': team})
                            except KeyError:
                                logging.error('Player does not exist 5 {}'.format(name))

                            for plugin in self.__plugins:
                                plugin.on_spawn(data)

                        elif data[0] == "player.onKill":# <killing soldier name: string> <killed soldier name: string> <weapon: string> <headshot: boolean>
                            event, name, victim, weapon, headshot = str(data[0]), str(data[1]), str(data[2]), str(data[3]), True if str(data[4]) == 'true' else False

                            try:
                                if self.__players[name].get('__injured', False) or self.__players[victim].get('__injured', False):
                                    for plugin in self.__plugins:
                                        plugin.on_revive(['rocketblast.on_revive', name])

                            except KeyError:
                                pass

                            try:
                                self.__players[victim].update({'__injured': True})
                            except KeyError:
                                pass

                            #if len(self.__players) > 64 or len(self.__players) < 0:
                            if len(self.__players) > 66 or len(self.__players) < 0:
                                logging.error('Player off {}'.format(len(self.__players)))
                                print('Player off {} {}'.format(len(self.__players), self.__server['serverName']))
                                real = set(self.__client.formatplayers(self.__client.send(['admin.listPlayers', 'all'])).get('players', {}))
                                print(real)
                                server = set(self.__players)
                                print(server)
                                print( server - real)
                                #print 'Player off {}'.format(self.__players, self.__client.formatplayers(self.__client.send(['admin.listPlayers', 'all'])).get('players', {}))

                            for plugin in self.__plugins:
                                plugin.on_kill(data)

                        elif data[0] == "player.onChat":# <source soldier name: string> <text: string>
                            #try:
                            #    print self.__players[str(data[1])]
                            #except KeyError:
                            #    if str(data[1]) == 'Server':
                            #        pass

                            for plugin in self.__plugins:
                                plugin.on_chat(data)
                            #command_match = CommandValidator.validate(data[2])
                            #if command_match.is_command:
                            #    plugin.on_command({'system': 'in-game', 'user': data[1], 'target': data[1] if command_match.visibility == 'private' else 'all'}, command_match.command, command_match.arguments.values())

                        elif data[0] == "server.onMaxPlayerCountChange": # <count: int>
                            continue

                        elif data[0] in ['admin.say', 'admin.listPlayers', 'serverInfo']:
                            continue

                        elif data[0] == "OK":
                            continue

                        else:
                            logging.warn('Unrecognized event {0} ({1})'.format(data[0], data))

                    except Exception as x:
                        print(traceback.format_exc())
                        logging.error('Error in plugin {1} ({0})'.format(x, plugin.__class__.__name__))
                        logging.error(traceback.format_exc())
                else:
                    pass

            except Client.ClientException as x:
                print( traceback.format_exc())
                logging.error(traceback.format_exc())
                with self.__lock:
                    if self.__client.connected():
                        self.__client.disconnect()

                    if listener.connected():
                        listener.disconnect()

                for plugin in self.__plugins:
                    plugin.disconnected()

                #if x[0] in ['Timeout', 'Lost connection', 'Refused']:
                if x.args[0] in ['Login failed']:
                    self.stop()

                else:#if x[0] in ['Timeout', 'Lost connection']:
                    print('Trying to reconnect {}:{} {} {}'.format(self.__ip, self.__port, threading.current_thread(), x.args[0]))
                    logging.info('Trying to reconnect {}:{} {} {}'.format(self.__ip, self.__port, threading.current_thread(), x.args[0]))
                    time.sleep(10)
                    # retry, higher interval sleep - or build this into frostbite3?
                    #pass
                #else:
                #    print x[0]
                #    #print 'Client.ClientException {} in {}:{} {}\n{}'.format(x, self.__ip, self.__port, threading.current_thread(), traceback.format_exc())
                #    print 'Threads {}'.format(threading.active_count())
                #    if x[0] in ['Login failed']:
                #        print 'LOGIN FAILED'#
#
                #    self.stop()
                #    #raise x

            except Exception as x:
                print('Exception {}'.format(x))
                traceback.print_exc()
                logging.error(traceback.format_exc())

        else:
            with self.__lock:
                if self.__client.connected():
                    self.__client.disconnect()

                if listener.connected():
                    listener.disconnect()

            for plugin in self.__plugins:
                plugin.disconnected()

            print('Removing monitor from {}:{} {}'.format(self.__ip, self.__port, self.thread))
            if Listener.servers[self.__handle] == self.thread:
                del Listener.servers[self.__handle]
            self = None
            print('Threads {}'.format(threading.active_count()))
            logging.error(traceback.format_exc())

    def stop(self):
        """
        Terminating the thread.
        :return: None
        """
        print('STOP')
        self.__terminate = True

    def send_command(self, data):
        print('send_command {}'.format(data))
        try:
            for plugin in self.__plugins:
                plugin.on_command(data)
        except Exception as x:
            print(x)
            traceback.print_exc()
            logging.error(traceback.format_exc())
