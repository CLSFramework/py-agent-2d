from typing import TYPE_CHECKING
from service_pb2 import *
from pyrusgeom.vector_2d import Vector2D
from src.utils.tools import Tools


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent

class BhvStarterSetPlayKickOff:
    def __init__(self):
        pass

    def execute(self, agent: "SamplePlayerAgent"):
        """
        Execute the kickoff behavior.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        """
        agent.logger.debug("BhvStarterSetPlayKickOff.execute")
        wm = agent.wm
        teammates = Tools.get_teammates_from_ball(agent)

        # Decide whether to kick or move based on teammates' positions
        if not teammates or teammates[0].dist_from_self > wm.self.dist_from_ball:
            return self.do_kick(agent)
        else:
            return self.do_move(agent)

    def do_kick(self, agent: "SamplePlayerAgent"):
        """
        Perform the kick action.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        """
        from src.behaviors.starter.bhv_starter_go_to_placed_ball import (
            BhvStarterGoToPlacedBall,
        )
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        agent.logger.debug("BhvStarterSetPlayKickOff.do_kick")

        go_to_placed_ball = BhvStarterGoToPlacedBall(0.0)

        # Go to the ball position
        if go_to_placed_ball.execute(agent):
            agent.logger.debug("BhvStarterSetPlayKickOff.do_kick: go_to_placed_ball")

        # Wait before kicking
        setplay = BhvStarterSetPlay()
        if setplay.do_kick_wait(agent):
            agent.logger.debug("BhvStarterSetPlayKickOff.do_kick: wait")
            return True

        # Perform the kick
        from src.behaviors.starter.bhv_starter_pass import BhvStarterPass
        bhv_starter_pass = BhvStarterPass()
        if bhv_starter_pass.execute(agent):
            agent.logger.debug("BhvStarterSetPlayKickOff.do_kick: pass")
            return True
        
        wm = agent.wm

        # Define target point and ball speed for the kick
        target_point = Vector2D(-20.0, 0.0)
        ball_speed = agent.server_params.max_power * wm.self.kick_rate

        # Enforce one step kick
        agent.add_action(
            PlayerAction(
                body_smart_kick=Body_SmartKick(
                    target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point),
                    first_speed=ball_speed,
                    first_speed_threshold=ball_speed * 0.96,
                    max_steps=1,
                )
            )
        )
        agent.logger.debug(f"BhvStarterSetPlayKickOff.do_kick: kick to {target_point}")
        
        return True

    def do_move(self, agent: "SamplePlayerAgent"):
        """
        Perform the move action in the kickoff gamemode.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise
        """
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay

        setplay = BhvStarterSetPlay()
        wm = agent.wm

        # Get target position and dash power
        target_point = agent.strategy.get_position(wm.self.uniform_number, agent)
        target_point.set_x(min(-0.5, target_point.x()))
        dash_power = setplay.get_set_play_dash_power(agent)
        dist_thr = wm.ball.dist_from_self * 0.07
        if dist_thr < 1.0:
            dist_thr = 1.0

        # Move to the target point
        agent.add_action(
            PlayerAction(
                body_go_to_point=Body_GoToPoint(
                    target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point),
                    distance_threshold=dist_thr,
                    max_dash_power=dash_power,
                )
            )
        )
        agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))

        return True
