from typing import TYPE_CHECKING
import math
from src.interfaces.IAgent import IAgent
from service_pb2 import *
from pyrusgeom.vector_2d import Vector2D
from pyrusgeom.segment_2d import Segment2D
from pyrusgeom.circle_2d import Circle2D
from src.behaviors.starter.bhv_starter_pass import BhvStarterPass
from src.utils.tools import Tools
import pyrusgeom.soccer_math as smath
from pyrusgeom.soccer_math import *
from pyrusgeom.geom_2d import *
import math
from src.utils.tools import Tools


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent
    
class BhvStarterSetPlayIndirectFreeKick:
    def __init__(self):
        pass
        

    def execute(self, agent: "SamplePlayerAgent") -> bool:
        '''
        Executes the indirect free kick behavior for the agent if the free kick is on the agent's side.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        setplay = BhvStarterSetPlay()
        wm = agent.wm
        our_kick = (wm.game_mode_type == GameModeType.BackPass_ and wm.game_mode_side != wm.our_side) or (wm.game_mode_type == GameModeType.IndFreeKick_ and wm.game_mode_side == wm.our_side) or (wm.game_mode_type == GameModeType.FoulCharge_ and wm.game_mode_side != wm.our_side) or (wm.game_mode_type == GameModeType.FoulPush_ and  wm.game_mode_side != wm.our_side ) 
        our_kick = True
        
        if our_kick:
            if setplay.is_kicker(agent):
                return self.do_kicker(agent)
            else:
                return self.do_offense_move(agent)
        else:
            return self.do_defense_move(agent)

    def do_kicker(self, agent: "SamplePlayerAgent"):
        '''
        Executes the kick behavior for the agent in an indirect free kick situation.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        from src.behaviors.starter.bhv_starter_go_to_placed_ball import BhvStarterGoToPlacedBall
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        go_to_placed_ball = BhvStarterGoToPlacedBall(0.0)
        # go to ball
        go_to_placed_ball.execute(agent)

        # wait
        setplay = BhvStarterSetPlay()
        setplay.do_kick_wait(agent)

        # kick to the teammate exist at the front of their goal
        self.do_kick_to_shooter(agent)

        wm = agent.wm
        max_kick_speed = wm.self.kick_rate * agent.server_params.max_power

        # pass
        passer = BhvStarterPass()
        passer.execute(agent)
        # wait(2)
        if wm.set_play_count <= 3:
            agent.add_action(PlayerAction(body_turn_to_point=Body_TurnToPoint(target_point=RpcVector2D(x=50, y=0), cycle=2)))

        # no teammate
        if not Tools.get_teammates_from_ball(agent) or Tools.get_teammates_from_ball(agent)[0].dist_from_self > 35.0 or Tools.get_teammates_from_ball(agent)[0].position.x < -30.0:
            real_set_play_count = int(wm.cycle - wm.last_set_play_start_time)
            if real_set_play_count <= agent.server_params.drop_ball_time - 3:
                agent.add_action(PlayerAction(body_turn_to_point=Body_TurnToPoint(target_point=RpcVector2D(x=50, y=0), cycle=2)))


            target_point = Vector2D(agent.server_params.pitch_half_length,
                                   (-1 + 2 * wm.cycle % 2) * (agent.server_params.goal_width / 2 - 0.8))
            ball_speed = max_kick_speed
            agent.add_action(PlayerAction(body_kick_one_step=Body_KickOneStep(target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point), first_speed=ball_speed, force_mode=False)))
            
            return True

        # kick to the teammate nearest to opponent goal
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)
        goal = Vector2D(agent.server_params.pitch_half_length, self_position.y() * 0.8)

        min_dist = 100000.0
        receiver = None

        for t in Tools.get_teammates_from_ball(agent):
            if t.dist_from_ball < 1.5:
                continue
            if t.dist_from_ball > 20.0:
                continue
            if t.position.x > wm.offside_line_x:
                continue
            t_position = Vector2D(t.position.x, t.position.y)
            dist = t_position.dist(goal) + t.dist_from_ball
            if dist < min_dist:
                min_dist = dist
                receiver = t

        target_point = goal
        target_dist = 10.0
        if not receiver:
            target_dist = Tools.get_teammates_from_self(agent)[0].dist_from_self
            target_point = Tools.get_teammates_from_self(agent)[0].position
        else:
            target_dist = receiver.dist_from_self
            target_point = receiver.position
            target_point.x += 0.6

        ball_speed = Tools.calc_first_term_geom_series_last(1.8, target_dist, agent.server_params.ball_decay)
        ball_speed = min(ball_speed, max_kick_speed)

        agent.add_action(PlayerAction(body_kick_one_step=Body_KickOneStep(target_point=target_point, first_speed=ball_speed, force_mode=False)))
        return True
        #agent.add_say_message(BallMessage(agent.effector().queued_next_ball_pos(), agent.effector().queued_next_ball_vel())) #TODO

    def do_kick_to_shooter(self, agent: "SamplePlayerAgent"):
        '''
        Executes Kick action to the teammate nearest to the opponent goal.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        wm = agent.wm
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)
        goal = Vector2D(agent.server_params.pitch_half_length, self_position.y() * 0.8)

        min_dist = 100000.0
        receiver = None

        # find the nearest teammate to the opponent goal
        for t in Tools.get_teammates_from_ball(agent):
            if t.dist_from_ball < 1.5:
                continue
            if t.dist_from_ball > 20.0:
                continue
            if t.position.x > wm.offside_line_x:
                continue
            if t.position.x < wm.ball.position.x - 3.0:
                continue
            if abs(t.position.y) > agent.server_params.goal_width / 2 * 0.5:
                continue
            t_position = Vector2D(t.position.x, t.position.y)
            goal_dist = t_position.dist(goal)
            if goal_dist > 16.0:
                continue

            dist = goal_dist * 0.4 + t.dist_from_ball * 0.6

            if dist < min_dist:
                min_dist = dist
                receiver = t

        if not receiver:
            return False
        
        max_ball_speed = wm.self.kick_rate * agent.server_params.max_power
        receiver_pos = Vector2D(receiver.position.x, receiver.position.y)
        receiver_vel = Vector2D(receiver.velocity.x, receiver.velocity.y)
        target_point = receiver_pos + receiver_vel
        target_point.set_x(target_point.x() + 0.6)
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        target_dist = ball_position.dist(target_point)

        # Calculate the number of steps required for the ball to reach the target
        ball_reach_step = math.ceil(calc_length_geom_series(max_ball_speed, target_dist, agent.server_params.ball_decay))
        ball_speed = calc_first_term_geom_series(target_dist, agent.server_params.ball_decay, ball_reach_step)

        ball_speed = min(ball_speed, max_ball_speed)

        agent.add_action(PlayerAction(body_kick_one_step=Body_KickOneStep(target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point), first_speed=ball_speed, force_mode=False)))
        return True

    def get_avoid_circle_point(self, agent: IAgent, point: Vector2D):
        '''
        Calculate a point to avoid a circle area around a specific location (goal area or center circle).
        Args:
            agent (IAgent): The agent that will execute the behavior.
            point (Vector2D): The target point to potentially adjust.
        Returns:
            Vector2D: The adjusted point if restricted is necessary, otherwise the original point.
        '''
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        setplay = BhvStarterSetPlay()
        SP = agent.server_params  # Access the server parameters
        wm = agent.wm  
        
        # Determine the radius of the restricted circle based on game mode
        circle_r = SP.goal_area_length + 0.5 if wm.game_mode_type == GameModeType.BackPass_ else SP.center_circle_r + 0.5
        circle_r2 = circle_r ** 2  

        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y) 

        # Adjust the point if it is near the goal area
        if point.x() < -SP.pitch_half_length + 3.0 and abs(point.y()) < SP.goal_width / 2:
            while point.x() < wm.ball.position.x and point.x() > -SP.pitch_half_length and ball_position.dist2(point) < circle_r2:
                point.x = (point.x() - SP.pitch_half_length) * 0.5 - 0.01

        # Check if the agent is inside the goal area and adjust the point if necessary
        if point.x() < -SP.pitch_half_length + 0.5 and abs(point.y()) < SP.goal_width / 2 + 0.5 and wm.self.position.x < -SP.pitch_half_length and abs(wm.self.position.y) < SP.goal_width / 2:
            return point

        # Adjust the point to avoid the circle area around the ball
        if ball_position.dist2(point) < circle_r2:
            rel = point - ball_position
            rel.set_length(circle_r)
            point = ball_position + rel

        # Use the set play behavior to get the final adjusted point
        return setplay.get_avoid_circle_point(wm, point)


    def do_offense_move(self, agent: "SamplePlayerAgent"):
        ''' 
        Execute the offensive move for the agent in an indirect free kick situation. 
        Args: 
            agent (SamplePlayerAgent): The agent that will execute the behavior. 
        Returns: 
            bool: True if the action was added to the agent's action list, False otherwise. 
        '''
        wm = agent.wm
        target_point = Tools.convert_vector2d_to_rpc_vector2d(agent.strategy.get_position(wm.self.uniform_number, agent))
        target_point.x = min(wm.offside_line_x - 1.0, target_point.x)
        target_point_vector2d = Vector2D(target_point.x, target_point.y)

        nearest_dist = 1000.0
       
        # Find the nearest teammate to the target point
        teammate = Tools.get_teammate_nearest_to(agent, Vector2D(target_point.x, target_point.y))
        teammate_pos = Vector2D(teammate.position.x, teammate.position.y)
        if nearest_dist < 2.5:
            target_point_vector2d += (target_point_vector2d - teammate_pos).set_length_vector(2.5)
            target_point_vector2d.set_x( min(wm.offside_line_x - 1.0, target_point_vector2d.x()))

        dash_power = 50
        dash_power = wm.self.get_safety_dash_power


        dist_thr = wm.ball.dist_from_self * 0.07
        if dist_thr < 0.5:
            dist_thr = 0.5
        
        agent.add_action(PlayerAction(body_go_to_point=Body_GoToPoint(target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point_vector2d), distance_threshold=dist_thr, max_dash_power=dash_power)))
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        turn_point = (Vector2D(agent.server_params.pitch_half_length, 0) + ball_position) * 0.5
        agent.add_action(PlayerAction(body_turn_to_point=Body_TurnToPoint(target_point=Tools.convert_vector2d_to_rpc_vector2d(turn_point), cycle=2)))
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)
        if target_point.x > 36.0 and (self_position.dist(Tools.convert_rpc_vector2d_to_vector2d(target_point)) > max(ball_position.dist(Tools.convert_rpc_vector2d_to_vector2d(target_point)) * 0.2, dist_thr) + 6.0 or wm.self.stamina < agent.server_params.stamina_max * 0.7):
            if not wm.self.stamina_capacity == 0:
                #TODO actions.append(Say(wait_request_message=WaitRequestMessage()))
                pass
        agent.add_action(PlayerAction(neck_turn_to_ball_or_scan=Neck_TurnToBallOrScan(count_threshold=0)))
        
        return True

    def do_defense_move(self, agent: "SamplePlayerAgent"):
        ''' 
        Execute the defensive move for the agent in an indirect free kick situation. 
        Args: 
            agent (SamplePlayerAgent): The agent that will execute the behavior. 
        Returns: 
            bool: True if the action was added to the agent's action list, False otherwise. 
        '''
        SP = agent.server_params
        wm = agent.wm
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)
        self_velocity = Vector2D(wm.self.velocity.x, wm.self.velocity.y)
        target = Tools.convert_vector2d_to_rpc_vector2d(agent.strategy.get_position(wm.self.uniform_number, agent))
        target_point = Vector2D(target.x, target.y)
        adjusted_point = self.get_avoid_circle_point(agent, target_point)

        dash_power = wm.self.get_safety_dash_power

        dist_thr = wm.ball.dist_from_self * 0.07
        if dist_thr < 0.5:
            dist_thr = 0.5
        # Adjust the point if necessary based on distance and inertia
        if adjusted_point != target_point and ball_position.dist(target_point) > 10.0 and Tools.inertia_final_point(agent.player_types[agent.wm.self.id], self_position, self_velocity).dist(adjusted_point) < dist_thr:
            adjusted_point = target_point

        collision_dist = agent.player_types[agent.wm.self.id].player_size + SP.goal_post_radius + 0.2

        goal_post_l = Vector2D(-SP.pitch_half_length + SP.goal_post_radius, -SP.goal_width / 2 - SP.goal_post_radius)
        goal_post_r = Vector2D(-SP.pitch_half_length + SP.goal_post_radius, +SP.goal_width / 2 + SP.goal_post_radius)
        dist_post_l = self_position.dist(goal_post_l)
        dist_post_r = self_position.dist(goal_post_r)

        nearest_post = goal_post_l if dist_post_l < dist_post_r else goal_post_r
        dist_post = min(dist_post_l, dist_post_r)

        # Check if distance to the nearest post is within collision range
        if dist_post < collision_dist + agent.player_types[agent.wm.self.id].real_speed_max  + 0.5:
            post_circle = Circle2D(nearest_post, collision_dist)
            move_line = Segment2D(self_position, adjusted_point)
            # Adjust the point if there is an intersection with the goal post
            if post_circle.intersection(move_line, None, None) > 0:
                post_angle = (nearest_post - self_position).th()
                if nearest_post.y() < self_position.y():
                    adjusted_point = nearest_post
                    adjusted_point += Vector2D.from_polar(collision_dist + 0.1, post_angle - 90.0)
                else:
                    adjusted_point = nearest_post
                    adjusted_point += Vector2D.from_polar(collision_dist + 0.1, post_angle + 90.0)

                dist_thr = 0.05
                
        agent.add_action(PlayerAction(body_go_to_point=Body_GoToPoint(target_point=Tools.convert_vector2d_to_rpc_vector2d(adjusted_point), distance_threshold=dist_thr, max_dash_power=dash_power)))
        agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))

        return True