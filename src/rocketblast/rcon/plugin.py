import abc
import time


class Plugin(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, listener):
        self.__listener = listener

#    def issubclassed(self, subclass):
#        return True if subclass in Plugin.__subclasses__() else False

    @property
    def handle(self):
        return self.__listener.handle

    @handle.setter
    def handle(self, value):
        self.__listener.handle = value

    @property
    def users(self):
        return self.__listener.users

    @users.setter
    def users(self, value):
        self.__listener.users = value

    @property
    def players(self):
        return self.__listener.players

    @players.setter
    def players(self, value):
        self.__listener.players = value

    @property
    def server(self):
        return self.__listener.server

    @server.setter
    def server(self, value):
        self.__listener.server = value

    @property
    def client(self):
        return self.__listener.client

    @client.setter
    def client(self, value):
        self.__listener.client = value

    @property
    def timers(self):
        return self.__listener.timers

    @timers.setter
    def timers(self, value):
        self.__listener.timers = value

    def add_timer(self, key, time, interval=None, player=None, arguments=None):
        owner = self.players[player].setdefault('__timers', {}) if player else self.timers

        owner.update({
            key: {
                'class': self.__class__.__name__,
                'time': time}})
        if interval:
            owner[key].update({
                'interval': interval})
        if arguments:
            owner[key].update({
                'arguments': arguments})

    def get_timers(self, key=None, player=None):
        return {k: v for k, v in self.players[player].get('__timers', {}).iteritems() if key == None or k == key} if player else {k: v for k, v in self.timers.iteritems() if key == None or k == key}

    def remove_timer(self, key, player=None):
        owner = self.players[player].get('__timers', {}) if player else self.timers

        try:
            del owner[key]
        except KeyError:
            pass

    @abc.abstractmethod
    def destroy(self):
        pass

    @abc.abstractmethod
    def connected(self):
        """
        Called when the listener successfully connected to the server.
        Will be called when reconnecting.
        :return None
        """
        pass

    @abc.abstractmethod
    def disconnected(self):
        """
        Called when the listener hitting an error (Timeout, most likely)
        or the :func: `~listener.Listener.stop()` method has been called.

        :return None
        """
        pass

    @abc.abstractmethod
    def on_timer(self, data):
        pass

    @abc.abstractmethod
    def on_players(self, data):
        """
        Called when the player count changes.
        :param data: eventType, player count, "up" or "down"
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_revive(self, data):
        pass

    @abc.abstractmethod
    def on_pb(self, data):
        """
        punkBuster.onMessage
        :param data: List with event data
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_load(self, data):
        """
        server.onLevelLoaded
        :param data: List with event data
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_over(self, data):
        """
        server.onRoundOverPlayers
        :param data: List with event data
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_connect(self, data):
        """
        player.onJoin
        :param data: event, player, EA GUID
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_join(self, data):
        """
        player.onAuthenticated
        :param data: event, player
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_part(self, data):
        """
        player.onLeave
        :param data: List with event data
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_team(self, data):
        """
        player.onTeamChange
        :param data: event, player, team, squad
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_squad(self, data):
        """
        player.onSquadChange
        :param data: event, player, team, squad
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_spawn(self, data):
        """
        player.onSpawn
        :param data: event, player, team
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_kill(self, data):
        """
        player.onKill
        :param data: event, player, victim, weapon, headshot
        :type data: list
        :return None
        """
        pass

    @abc.abstractmethod
    def on_chat(self, data):
        """
        player.onChat
        :param data: event, player, message, to
        :type data: list
        :return None
        """
        pass
