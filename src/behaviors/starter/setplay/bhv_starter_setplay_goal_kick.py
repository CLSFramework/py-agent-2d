from typing import TYPE_CHECKING
from service_pb2 import *
from pyrusgeom.vector_2d import Vector2D
from src.behaviors.starter.bhv_starter_clearball import BhvStarterClearBall
from src.utils.tools import Tools
from src.behaviors.starter.bhv_starter_pass import BhvStarterPass
from src.behaviors.starter.bhv_starter_clearball import BhvStarterClearBall
from src.utils.tools import Tools


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent


class BhvStarterSetPlayGoalKick:
    def __init__(self):
        pass

    def execute(self, agent: "SamplePlayerAgent"):
        """
        Execute the set play move for the agent in goal kick game mode.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        """
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay

        setplay = BhvStarterSetPlay()
        if setplay.is_kicker(agent):
            return self.do_kick(agent)
        else:
            return self.do_move(agent)

    def do_kick(self, agent: "SamplePlayerAgent"):
        '''
        Execute the decision for the kicker agent in the goal kick set play.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        '''
        from src.behaviors.starter.bhv_starter_go_to_placed_ball import (
            BhvStarterGoToPlacedBall,
        )
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay

        go_to_placed_ball = BhvStarterGoToPlacedBall(0.0)

        self.do_second_kick(agent)

        # Go to the ball position and wait before kicking
        if go_to_placed_ball.execute(agent):
            return True

        set_play = BhvStarterSetPlay()
        if set_play.do_kick_wait(agent):
            return True

        # Pass the ball if its possible
        self.do_pass(agent)
        
        self.do_kick_to_far_side(agent)

        wm = agent.wm
        # Find the time left for the set play
        real_set_play_count = wm.cycle - agent.wm.last_set_play_start_time
        if real_set_play_count <= agent.server_params.drop_ball_time - 10:
            agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))
            return True
        clear_ball = BhvStarterClearBall()
        clear_ball.execute(agent)
        return True

    def do_second_kick(self, agent: "SamplePlayerAgent"):
        '''
        Perform the real kick action for the kicker agent in the goal kick set play.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        '''
        wm = agent.wm
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        ball_velocity = Vector2D(wm.ball.velocity.x, wm.ball.velocity.y)

        # Check if the ball is inside the goal area; if so, return False
        if (
            wm.ball.position.x
            < -agent.server_params.pitch_half_length
            + agent.server_params.goal_area_length
            + 1.0
            and abs(wm.ball.position.y) < agent.server_params.goal_width * 0.5 + 1.0
        ):
            return False

        # If the ball is kickable by the agent, perform a pass and clear ball action
        if wm.self.is_kickable:
            self.do_pass(agent)
            clear_ball = BhvStarterClearBall()
            clear_ball.execute(agent)

        self.do_intercept(agent)

        # Calculate the final position of the ball using inertia
        ball_final = Tools.calculate_ball_inertia_final_point(
            ball_position, ball_velocity, agent.server_params.ball_decay
        )

        agent.add_action(
            PlayerAction(
                body_go_to_point=Body_GoToPoint(
                    target_point=Tools.convert_vector2d_to_rpc_vector2d(ball_final),
                    distance_threshold=2.0,
                    max_dash_power=agent.server_params.max_dash_power,
                )
            )
        )

        agent.add_action(
            PlayerAction(
                body_turn_to_point=Body_TurnToPoint(
                    target_point=RpcVector2D(x=0, y=0), cycle=2
                )
            )
        )

        return True

    def do_pass(self, agent: "SamplePlayerAgent"):
        '''
        Perform a pass action for the kicker agent in the goal kick set play.
        Args:
            agent (SamplePlayerAgent): The agent that will execute
                the behavior.
        '''
        passer = BhvStarterPass()
        passer.execute(agent)
        return True

    def do_intercept(self, agent: "SamplePlayerAgent"):
        '''
        Perform the intercept action for the kicker agent in the goal kick set play.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        '''
        wm = agent.wm

        if (
            wm.ball.position.x
            < -agent.server_params.pitch_half_length
            + agent.server_params.goal_area_length
            + 1.0
            and abs(wm.ball.position.y)
            < agent.server_params.goal_area_width * 0.5 + 1.0
        ):
            return False

        if wm.self.is_kickable:
            return False

        self_min = wm.intercept_table.self_reach_steps
        mate_min = wm.intercept_table.first_teammate_reach_steps
        if self_min > mate_min:
            return False

        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        ball_velocity = Vector2D(wm.ball.velocity.x, wm.ball.velocity.y)
        trap_pos = Tools.inertia_point(
            ball_position, ball_velocity, self_min, agent.server_params.ball_decay
        )
        if (
            trap_pos.x() > agent.server_params.our_penalty_area_line_x - 8.0
            and abs(trap_pos.y()) > agent.server_params.penalty_area_half_width - 5.0
        ) or ball_velocity.r2() < 0.25:
            agent.add_action(PlayerAction(body_intercept=Body_Intercept()))
            return True

        return False

    def do_move(self, agent: "SamplePlayerAgent"):
        '''
        Execute the move action for the non-kicker agent in the kick-in set play.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        '''
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay

        setplay = BhvStarterSetPlay()
        self.do_intercept(agent)  

        wm = agent.wm  
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y) 
        dash_power = setplay.get_set_play_dash_power(agent)
        dist_thr = max(wm.ball.dist_from_self * 0.07, 1.0)

        # Get target position based on strategy and adjust the y-coordinate
        target_rpc = Tools.convert_vector2d_to_rpc_vector2d(
            agent.strategy.get_position(wm.self.uniform_number, agent)
        )
        target_point = Vector2D(target_rpc.x, target_rpc.y)
        target_point.set_y(target_point.y() + wm.ball.position.y * 0.5)

        # Ensure the target point is within pitch boundaries
        if abs(target_point.y()) > agent.server_params.pitch_half_width - 1.0:
            target_point.set_y(
                (target_point.y() / abs(target_point.y()))
                * (agent.server_params.pitch_half_width - 1.0)
            )

        # Check if the agent has sufficient stamina
        if wm.self.stamina > agent.server_params.stamina_max * 0.9:
            nearest_opp = Tools.get_opponent_nearest_to_self(agent) 
            if nearest_opp and nearest_opp.dist_from_self < 3.0:
                add_vec = ball_position - target_point
                add_vec.set_length(3.0)

                time_val = wm.cycle % 60
                if time_val < 20:
                    pass
                elif time_val < 40:
                    target_point += add_vec.rotated_vector(90.0)
                else:
                    target_point += add_vec.rotated_vector(-90.0)

                # Ensure target point is within pitch boundaries
                target_point.set_x(
                    min(
                        max(-agent.server_params.pitch_half_length, target_point.x()),
                        agent.server_params.pitch_half_length,
                    )
                )
                target_point.set_y(
                    min(
                        max(-agent.server_params.pitch_half_width, target_point.y()),
                        agent.server_params.pitch_half_width,
                    )
                )

        agent.add_action(
            PlayerAction(
                body_go_to_point=Body_GoToPoint(
                    target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point),
                    distance_threshold=dist_thr,
                    max_dash_power=dash_power,
                )
            )
        )

        # Add action to turn towards the ball
        agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))

        self_position = Vector2D(wm.self.position.x, wm.self.position.y)  # Get agent's current position
        if (
            self_position.dist(target_point)
            > ball_position.dist(target_point) * 0.2 + 6.0
            or wm.self.stamina < agent.server_params.stamina_max * 0.7
        ):
            if not wm.self.stamina_capacity == 0:  # TODO: Add wait request action
                pass

        return True

    def do_kick_to_far_side(self, agent: "SamplePlayerAgent"):
        '''
        Execute the kick action to the far side of the field.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list, False otherwise.
        '''
        wm = agent.wm  

        # Define the target point near the opponent's penalty area
        target_point = Vector2D(
            agent.server_params.our_penalty_area_line_x - 5.0,
            agent.server_params.penalty_area_half_width,
        )

        # Adjust the target point if the ball is above the center line
        if wm.ball.position.y > 0.0:
            target_point.set_y(target_point.y() * -1.0)

        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        ball_move_dist = ball_position.dist(target_point)

        ball_first_speed = Tools.calc_first_term_geom_series_last(
            0.7, ball_move_dist, agent.server_params.ball_decay
        )
        ball_first_speed = min(agent.server_params.ball_speed_max, ball_first_speed)
        ball_first_speed = min(
            wm.self.kick_rate * agent.server_params.max_power, ball_first_speed
        )

        accel = target_point - ball_position
        accel.set_length(ball_first_speed)

        # Calculate the kick power based on the acceleration and the agent's kick rate
        kick_power = min(agent.server_params.max_power, accel.r() / wm.self.kick_rate)
        kick_angle = accel.th()  
        
        agent.add_action(
            PlayerAction(
                kick=Kick(
                    power=kick_power,
                    relative_direction=kick_angle.degree() - wm.self.body_direction,
                )
            )
        )
        return True

