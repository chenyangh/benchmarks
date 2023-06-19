import numpy as np
import jax
import haiku as hk
import jax.numpy as jnp
import sys
from multiprocessing import Process, Queue, Value

# import file from outside directory
sys.path.append('/Users/bigyankarki/Desktop/bigyan/cc/chinese-checkers/python2/')
from wrappers import pywrapper as pw
from wrappers import ccwrapper as cw
from mcts import mcts
from helpers import log_helper

# import players
from players import nn_player as nnp, random_player as rp, uct_player as uct
# from players import async_nn_player as async_nnp


# define board size
BOARD_DIM = 4
cc = cw.CCheckers()

# init logger
logger = log_helper.setup_logger('eval_players', 'eval_players.log')


class Play:
    def __init__(self, limit=True, max_turns=1000):
        self.max_turns = max_turns
        self.limit = limit

    def play(self, players):
        visited = []
        outcome = 0

        state = cw.CCState()
        cc.Reset(state)
        repeat = False

        if not self.limit:
            self.max_turns = float('inf')

        turn_count = 1

        while not cc.Done(state) and not repeat and turn_count < 101:
            player = state.getToMove()
            board = state.getBoard()

            # print("-"*100)
            # print("Current board postion: ", board)
            # print("Player turn: {}".format(player+1))

            visited.append(state.getBoard())
            current_player = players[player]
            
            
            next_action, stats = current_player.runMCTS(state, 0)
            


            cc.ApplyMove(state, next_action)
            cc.freeMove(next_action)
            # print("Player {} moved from {} to {}".format(player+ 1, next_action.getFrom(), next_action.getTo()))
            # print("-"*100)

            turn_count += 1
            repeat_count = 0

            for s in visited:
                if np.equal(np.array(state.getBoard()), np.array(s)).all():
                    repeat_count +=1
                if repeat_count > 6:
                    repeat = True

        # print(state.getBoard())
        visited.append(state.getBoard())

        # if draw
        if repeat or (not cc.Done(state) and turn_count > 100):
            outcome = 0
            # print("Draw by repetition")
        elif cc.Winner(state) == 0: # if nn_player wins. outcome = 1.
            # print("player {} won. ".format(cc.Winner(state)+1))
            outcome = 1
        elif cc.Winner(state) == 1: # if other player wins, outcome = -1
            # print("player {} won. ".format(cc.Winner(state)+1))
            outcome = -1

        return outcome


# nn vs random player and uct player
def play_regular_games(nn_instance):
    game_play_instance = Play()

    # define uctp player and random player
    nnpl = nnp.NNPlayer(nn_instance)
    uctp = uct.UCTPlayer()
    rpl = rp.RandomPlayer()
    nn_player = mcts.MCTS(cc, nnpl)
    uct_player = mcts.MCTS(cc, uctp) # uct player
    random_player = mcts.MCTS(cc, rpl)  # random player

    # define games to play
    games = [[nn_player, uct_player], [uct_player, nn_player], [nn_player, random_player], [random_player, nn_player]]
    games_names = ['nn_{}_vs_uct'.format(nn_instance-1), 'uct_vs_nn_{}'.format(nn_instance-1), 'nn_{}_vs_random'.format(nn_instance-1), 'random_vs_nn_{}'.format(nn_instance-1)]

    for idx, game in enumerate(games):
        res = [0, 0, 0] # [p1 wins, p2 wins, draws]
        for j in range(100):
            outcome = game_play_instance.play(game)
            if outcome == 1: 
                res[0] += 1
            elif outcome == -1: 
                res[1] += 1
            elif outcome == 0: 
                res[2] += 1
        logger.info("Game: {}: {}".format(games_names[idx], res))


# nn_vs_nn game play worker
def play_nn_vs_nn(nn_instance1, nn_instance2):
    game_play_instance = Play()

    # define uctp player and random player
    nnpl1 = nnp.NNPlayer(nn_instance1)
    nnpl2 = nnp.NNPlayer(nn_instance2)
    nn_player1 = mcts.MCTS(cc, nnpl1)
    nn_player2 = mcts.MCTS(cc, nnpl2)

    # define games to play
    games = [[nn_player1, nn_player2], [nn_player2, nn_player1]]
    games_names = ['nn_{}_vs_nn_{}'.format(nn_instance1-1, nn_instance2-1), 'nn_{}_vs_nn_{}'.format(nn_instance2-1, nn_instance1-1)]

    for idx, game in enumerate(games):
        res = [0, 0, 0] # [p1 wins, p2 wins, draws]
        for j in range(100):
            outcome = game_play_instance.play(game)
            if outcome == 1: 
                res[0] += 1
            elif outcome == -1: 
                res[1] += 1
            elif outcome == 0: 
                res[2] += 1
        logger.info("Game: {} : {}".format(games_names[idx], res))


def main():
    nn_instances = [0, 1, 5, 10]

    # define process for regular games
    regular_games_processes = []
    for i in range(len(nn_instances)):
        p = Process(target=play_regular_games, args=(nn_instances[i], ))
        regular_games_processes.append(p)
        p.start()

    # define process for nn vs nn games
    nn_vs_nn_games_processes = []
    for i in range(len(nn_instances)-1):
        p = Process(target=play_nn_vs_nn, args=(nn_instances[0], nn_instances[1]))
        nn_vs_nn_games_processes.append(p)
        p.start()

    # join processes
    for p in regular_games_processes:
        p.join()

    for p in nn_vs_nn_games_processes:
        p.join()

    



if __name__ == "__main__":
    main()




    