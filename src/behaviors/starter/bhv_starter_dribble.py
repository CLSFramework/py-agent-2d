from typing import TYPE_CHECKING
from src.interfaces.IBehavior import IBehavior
from src.utils.tools import Tools
from pyrusgeom.vector_2d import Vector2D
from pyrusgeom.sector_2d import Sector2D
from service_pb2 import *


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent


class BhvStarterDribble(IBehavior):
    # Initialize the behavior
    def __init__(self):
        pass

    # Execute the dribbling behavior
    def execute(self, agent: "SamplePlayerAgent") -> bool:
        '''
        Execute the dribbling behavior.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        
        agent.logger.debug("BhvStarterDribble.execute")
        wm = agent.wm
        ball_pos = Vector2D(wm.ball.position.x, wm.ball.position.y)  # Get ball position
        dribble_angle = (Vector2D(52.5, 0) - ball_pos).th().degree()  # Calculate dribble angle
        dribble_speed = 0.8  # Set dribble speed
        dribble_threshold = 0.7  # Set dribble speed threshold
        dribble_radius = 3  # Set dribble radius
        dribble_sector = Sector2D(
            ball_pos, 0, dribble_radius, dribble_angle - 15, dribble_angle + 15  # Define dribble sector
        )
        # Define dribble angles
        dribble_angles = [dribble_angle , dribble_angle - 30, dribble_angle + 30]
        # Calculate dribble targets base on the dribble angles
        targets = list(map(lambda angle: Vector2D.polar2vector(dribble_radius, angle) + ball_pos, dribble_angles))
        for target in targets:
            # Check if there are no opponents in the dribble sector
            if Tools.exist_opponent_in(agent, dribble_sector):
                targets.remove(target)
                continue
        
        if len(targets) > 0:
            # Get the best target to dribble based on the nearest target to the opponent's goal
            best_target = min(targets, key=lambda target: target.dist(Vector2D(52.5, 0)))
            agent.add_log_message(
                LoggerLevel.DRIBBLE,
                f": Dribbling to {best_target}",
                agent.wm.self.position.x,
                agent.wm.self.position.y - 2,
                "\033[31m",
            )
            agent.add_log_text(LoggerLevel.DRIBBLE, f": Dribbling to {best_target}")
            agent.logger.debug(f"Dribbling to {best_target}")
            agent.add_action(
                PlayerAction(
                    body_smart_kick=Body_SmartKick(
                        target_point=Tools.convert_vector2d_to_rpc_vector2d(best_target),
                        first_speed=dribble_speed,
                        first_speed_threshold=dribble_threshold,
                        max_steps=2,
                    )
                )
            )
            return True
        return False
