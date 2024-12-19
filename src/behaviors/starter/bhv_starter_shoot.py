from typing import TYPE_CHECKING
from src.interfaces.IBehavior import IBehavior
from pyrusgeom.vector_2d import Vector2D
from service_pb2 import *
from src.utils.tools import Tools


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent


class BhvStarterShoot(IBehavior):
    def __init__(self):
        pass

    def execute(self, agent: "SamplePlayerAgent") -> bool:
        """Executes the shooting behavior for the agent.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        """
        
        agent.logger.debug("BhvStarterShoot.execute")
        wm = agent.wm
        ball_pos = Vector2D(wm.ball.position.x, wm.ball.position.y)
        ball_max_velocity = agent.server_params.ball_speed_max

        # Define goal positions
        center_goal = Vector2D(agent.server_params.pitch_half_length, 0.0)
        right_goal = Vector2D(
            agent.server_params.pitch_half_length, agent.server_params.goal_width / 2.0 - 1.0
        )  # Lower Pole
        left_goal = Vector2D(
            agent.server_params.pitch_half_length, -agent.server_params.goal_width / 2.0 + 1.0
        )  # Upper Pole

        # Determine which goal post to shoot at
        target = left_goal if ball_pos.dist(right_goal) < ball_pos.dist(left_goal) else right_goal
        
        # Check if the ball is within shooting range
        if ball_pos.dist(center_goal) <= 25.0:
            
            # Log and perform the action to shoot at the left goal
            agent.add_log_message(
                LoggerLevel.SHOOT,
                f": Shooting to {target}",
                agent.wm.self.position.x,
                agent.wm.self.position.y - 2,
                "\033[31m",
            )
            agent.add_log_text(LoggerLevel.SHOOT, f": Shooting to {target}")
            agent.logger.debug(f"Shooting to {target}")
            agent.add_action(
                PlayerAction(
                    body_smart_kick=Body_SmartKick(
                        target_point=Tools.convert_vector2d_to_rpc_vector2d(target),
                        first_speed=ball_max_velocity,
                        first_speed_threshold=0.1,
                        max_steps=3,
                    )
                )
            )
            return True
        return False
