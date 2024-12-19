from typing import TYPE_CHECKING
from src.interfaces.IBehavior import IBehavior
from pyrusgeom.soccer_math import *
from pyrusgeom.geom_2d import *
from service_pb2 import *
from src.behaviors.starter.bhv_starter_clearball import BhvStarterClearBall
from src.behaviors.starter.bhv_starter_pass import BhvStarterPass
from src.behaviors.starter.bhv_starter_dribble import BhvStarterDribble
from src.behaviors.starter.bhv_starter_shoot import BhvStarterShoot
from src.utils.tools import Tools


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent

class BhvStarterKickPlanner(IBehavior):
    def __init__(self):
        self.starter_shoot = BhvStarterShoot()
        self.starter_clear_ball = BhvStarterClearBall()
        self.starter_dribble = BhvStarterDribble()
        self.starter_pass = BhvStarterPass()

    def execute(self, agent: "SamplePlayerAgent"):
        '''
        Execute the kick planner behavior which decides whether to shoot, pass, dribble, hold the ball, or clear the ball.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        agent.logger.debug("BhvStarterKickPlanner.execute")
        
        # Checking if shoot is possible
        if self.starter_shoot.execute(agent):
            agent.logger.debug("Shooting")
        
        # Find nearest opponent distance
        opps = Tools.get_opponents_from_self(agent)
        nearest_opp_dist = min((opp.dist_from_self for opp in opps), default=1000.0)
        
        # If nearest opponent is close, pass
        if nearest_opp_dist < 10:
            if self.starter_pass.execute(agent):
                agent.logger.debug("Passing")

        # If nearest opponent is far, dribble
        if self.starter_dribble.execute(agent):
            agent.logger.debug("Dribbling")
        
        # If dribble is not possible, hold the ball
        if nearest_opp_dist > 2.5:
            agent.add_action(PlayerAction(body_hold_ball=Body_HoldBall()))
            agent.logger.debug("Holding ball")

        # If holding the ball is not possible, clear the ball
        if self.starter_clear_ball.execute(agent):
            agent.logger.debug("Clearing ball")
            
        return True
