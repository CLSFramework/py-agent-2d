from typing import TYPE_CHECKING
from src.interfaces.IAgent import IAgent
#from src.setplay.BhvSetPlay import BhvSetPlay
from service_pb2 import *
from src.strategy.starter_strategy import StarterStrategy
from pyrusgeom.vector_2d import Vector2D
from src.utils.tools import Tools
from pyrusgeom.soccer_math import inertia_n_step_point
from pyrusgeom.ray_2d import Ray2D
from pyrusgeom.size_2d import Size2D
from pyrusgeom.rect_2d import Rect2D
from pyrusgeom.angle_deg import AngleDeg
from src.utils.tools import Tools

if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent
class BhvStarterTheirGoalKickMove:
    def __init__(self):
        pass
    
    def execute(self, agent: "SamplePlayerAgent"):
        '''
        Execute the set play move for the agent in goal kick game mode.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        '''
        # Define the expanded penalty area
        expand_their_penalty = Rect2D(
            Vector2D(agent.server_params.their_penalty_area_line_x - 0.75,
                    -agent.server_params.penalty_area_half_width - 0.75),
            Size2D(agent.server_params.penalty_area_length + 0.75,
                (agent.server_params.penalty_area_half_width * 2) + 1.5)
        )

        wm = agent.wm 

        # agent to chase the ball
        self.do_chase_ball(agent)  

        self_position = Vector2D(wm.self.position.x, wm.self.position.y)  
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)  
        ball_velocity = Vector2D(wm.ball.velocity.x, wm.ball.velocity.y)  

        # Determine intersection points of the ball's trajectory with the expanded penalty area
        intersection_list = expand_their_penalty.intersection(Ray2D(ball_position, ball_velocity.th()))
        intersection = intersection_list[0]

        # Check if the ball's velocity is significant do normal movement
        if ball_velocity.r() > 0.2:
            if not expand_their_penalty.contains(ball_position) or len(intersection_list) != 1:  # TODO Check
                return self.do_normal(agent)
        else:
            if (wm.ball.position.x > agent.server_params.their_penalty_area_line_x + 7.0 and
                abs(wm.ball.position.y) < (agent.server_params.goal_width / 2.0) + 2.0):
                return self.do_normal(agent)

            # Adjust intersection point if the ball's velocity is not significant
            intersection.set_x(agent.server_params.their_penalty_area_line_x - 0.76)
            intersection.set_y(wm.ball.position.y)

        min_dist = 100.0  
        nearest_tm = Tools.get_teammate_nearest_to(agent, intersection)  
        nearest_tm_pos = Vector2D(nearest_tm.position.x, nearest_tm.position.y)  
        min_dist = nearest_tm_pos.dist(intersection)

        # If the nearest teammate is closer to the intersection, perform a normal action
        if min_dist < self_position.dist(intersection):
            return self.do_normal(agent)

        dash_power = wm.self.get_safety_dash_power  # TODO: Determine safe dash power

        # Adjust intersection point based on agent's position and penalty area constraints
        if intersection.x() < agent.server_params.their_penalty_area_line_x and wm.self.position.x > agent.server_params.their_penalty_area_line_x - 0.5:
            intersection.set_y(agent.server_params.penalty_area_half_width - 0.5)
            if wm.self.position.y < 0.0:
                intersection.set_y(intersection.y() * -1.0)
        elif intersection.y() > agent.server_params.penalty_area_half_width and abs(wm.self.position.y) < agent.server_params.penalty_area_half_width + 0.5:
            intersection.set_y(agent.server_params.penalty_area_half_width + 0.5)
            if wm.self.position.y < 0.0:
                intersection.set_y(intersection.y() * -1.0)

        dist_thr = max(wm.ball.dist_from_self * 0.07, 1.0)  # Calculate distance threshold

        # Add actions to the agent: go to the intersection point and turn to the ball
        agent.add_action(PlayerAction(body_go_to_point=Body_GoToPoint(target_point=Tools.convert_vector2d_to_rpc_vector2d(intersection), distance_threshold=dist_thr, max_dash_power=dash_power)))
        agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=0)))

        return True


    def do_normal(self, agent: "SamplePlayerAgent"):
        '''
        Perform normal movement for the agen in goal kick game mode.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:    
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        wm = agent.wm
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        setplay = BhvStarterSetPlay()
        dash_power = setplay.get_set_play_dash_power(agent)
        targ = Tools.convert_vector2d_to_rpc_vector2d(agent.strategy.get_position(wm.self.uniform_number, agent))
        target_point = Vector2D(targ.x, targ.y)

        # Attract to ball
        if target_point.x() > 25.0 and (target_point.y() * wm.ball.position.y < 0.0 or target_point.abs_y() < 10.0):
            y_diff = wm.ball.position.y - target_point.y()
            target_point.set_y(target_point.y() + (y_diff * 0.4))

        # Check penalty area
        if wm.self.position.x > agent.server_params.their_penalty_area_line_x and target_point.abs_y() < agent.server_params.penalty_area_half_width:
            target_point.set_y(agent.server_params.penalty_area_half_width + 0.5)
            if wm.self.position.y < 0.0:
                target_point.set_y(target_point.y() * -1)

        dist_thr = max(wm.ball.dist_from_self * 0.07, 1.0)
        agent.add_action(PlayerAction(body_go_to_point=Body_GoToPoint(target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point), distance_threshold=dist_thr, max_dash_power=dash_power)))
        agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=0)))
        
        return True

    def do_chase_ball(self, agent: "SamplePlayerAgent"):
        '''
        Determine if the agent should chase the ball.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the agent should chase the ball, False otherwise.
        '''
        wm = agent.wm 

        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)  
        ball_velocity = Vector2D(wm.ball.velocity.x, wm.ball.velocity.y)  

        if ball_velocity.r() < 0.2:
            return False

        self_min = wm.intercept_table.self_reach_steps  

        # Check if the minimum steps required to reach the ball is too high
        if self_min > 10:
            return False

        # Calculate the predicted position of the ball using its inertia
        get_pos = Tools.inertia_point(ball_position, ball_velocity, self_min, agent.server_params.ball_decay)

        # Define the expanded penalty area
        pen_x = agent.server_params.their_penalty_area_line_x - 1.0
        pen_y = agent.server_params.penalty_area_half_width + 1.0
        their_penalty = Rect2D(
            Vector2D(pen_x, -pen_y),
            Size2D(agent.server_params.penalty_area_length + 1.0,
                (agent.server_params.penalty_area_half_width * 2) - 2.0)
        )

        # Check if the predicted ball position is within the penalty area
        if their_penalty.contains(get_pos):
            return False

        # Check if the agent's position relative to the penalty area allows chasing the ball
        if (get_pos.x() > pen_x and wm.self.position.x < pen_x and abs(wm.self.position.y) < pen_y - 0.5):
            return False

        # The agent can chase the ball
        agent.add_action(PlayerAction(body_intercept=Body_Intercept()))
        return True

