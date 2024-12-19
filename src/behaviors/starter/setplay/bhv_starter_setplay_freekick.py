from typing import TYPE_CHECKING
import math
from service_pb2 import *
from pyrusgeom.soccer_math import calc_length_geom_series
from src.behaviors.starter.bhv_starter_pass import BhvStarterPass
from src.utils.tools import Tools
import math
from src.behaviors.starter.bhv_starter_clearball import BhvStarterClearBall


if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent

class BhvStarterSetPlayFreeKick:
    def __init__(self):
        pass
    
    def execute(self, agent: "SamplePlayerAgent"):
        '''
        Executes the free kick behavior for the agent if the free kick is on the agent's side.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        selfplay = BhvStarterSetPlay()
        if selfplay.is_kicker(agent):
            #Kicker action
            return self.doKick(agent)
        else:
            #Non-kicker action
            return self.do_move(agent)

    def doKick(self, agent: "SamplePlayerAgent"):
        '''
        Executes the kick behavior for the agent in a free kick situation.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        from src.behaviors.starter.bhv_starter_go_to_placed_ball import BhvStarterGoToPlacedBall
        from src.behaviors.starter.bhv_starter_setplay import BhvStarterSetPlay
        go_to_placed_ball = BhvStarterGoToPlacedBall(0.0)
        
        # go to the ball position
        go_to_placed_ball.execute(agent)
        
        # wait before kicking
        setplay = BhvStarterSetPlay()
        if setplay.do_kick_wait(agent):
            return True
        
        # kick
        wm = agent.wm
        max_ball_speed = wm.self.kick_rate * agent.server_params.max_power

        # pass
        passer = BhvStarterPass()
        passer.execute(agent)

        # kick to the nearest teammate

        nearest_teammate: Player = Tools.get_teammate_nearest_to_self(agent, False)
        if nearest_teammate and nearest_teammate.dist_from_self < 20.0 and (nearest_teammate.position.x > -30.0 or nearest_teammate.dist_from_self < 10.0):
            nearest_teammate_pos = Tools.convert_rpc_vector2d_to_vector2d(nearest_teammate.position)
            nearest_teammate_vel = Tools.convert_rpc_vector2d_to_vector2d(nearest_teammate.velocity)
            target_point = Tools.convert_rpc_vector2d_to_vector2d(nearest_teammate.inertia_final_point)
            target_point.set_x(target_point.x() + 0.5)
            ball_position = Tools.convert_rpc_vector2d_to_vector2d(wm.ball.position)
            
            ball_move_dist = ball_position.dist(target_point)
            ball_reach_step = math.ceil(calc_length_geom_series(max_ball_speed, ball_move_dist, agent.server_params.ball_decay))
            ball_speed = 2.3
            '''if ball_reach_step > 3:
                ball_speed = calc_first_term_geom_series(ball_move_dist, agent.server_params.ball_decay, ball_reach_step)
            else:
                ball_speed = Tools.calc_first_term_geom_series_last(1.4, ball_move_dist, agent.server_params.ball_decay)
                ball_reach_step = math.ceil(calc_length_geom_series(ball_speed, ball_move_dist, agent.server_params.ball_decay))'''

            ball_speed = min(ball_speed, max_ball_speed)
            agent.add_action(PlayerAction(body_kick_one_step=Body_KickOneStep(target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point), first_speed=ball_speed, force_mode=False)))

        # clear
        if abs(wm.ball.angle_from_self - wm.self.body_direction) > 1.5:
            agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))
            return True
        clear_ball = BhvStarterClearBall()
        clear_ball.execute(agent)
        return True

    def do_move(self, agent: "SamplePlayerAgent"):
        '''
        Executes the move behavior for the agent in a free kick situation.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the
                behavior.
        Returns:
            bool: True if the action was added to the agent's action list,False otherwise.
        '''
        wm = agent.wm
        target_point_rpc = Tools.convert_vector2d_to_rpc_vector2d(agent.strategy.get_position(wm.self.uniform_number, agent))
        target_point = Tools.convert_rpc_vector2d_to_vector2d(target_point_rpc)
        ball_positions = Tools.convert_rpc_vector2d_to_vector2d(wm.ball.position)
        self_positions = Tools.convert_rpc_vector2d_to_vector2d(wm.self.position)

        #Try to find the base position base on the nearest opponent's position
        if wm.set_play_count > 0 and wm.self.stamina > agent.server_params.stamina_max * 0.9:
            nearest_opp = Tools.get_opponents_from_self(agent)[0]

            if nearest_opp and nearest_opp.dist_from_self < 3.0:
                add_vec = ball_positions - target_point
                add_vec.set_length(3.0)

                time_val = wm.cycle % 60
                if time_val < 20:
                    pass
                elif time_val < 40:
                    target_point += add_vec.rotated_vector(90.0)
                else:
                    target_point += add_vec.rotated_vector(-90.0)

                target_point.set_x(min(max(-agent.server_params.pitch_half_length, target_point.x()), agent.server_params.pitch_half_length))
                target_point.set_y(min(max(-agent.server_params.pitch_half_width, target_point.y()), agent.server_params.pitch_half_width))

        target_point.set_x(min(target_point.x(), wm.offside_line_x - 0.5))
        
        dash_power = 50 # you can choose to be  selfplay.get_set_play_dash_power(agent)

        dist_thr = wm.ball.dist_from_self * 0.07
        if dist_thr < 1.0:
            dist_thr = 1.0

        agent.add_action(PlayerAction(body_go_to_point=Body_GoToPoint(target_point=Tools.convert_vector2d_to_rpc_vector2d(target_point), distance_threshold=dist_thr, max_dash_power=dash_power)))
        agent.add_action(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))

        if self_positions.dist(target_point) > max(ball_positions.dist(target_point) * 0.2, dist_thr) + 6.0 or wm.self.stamina < agent.server_params.stamina_max * 0.7:
            if not wm.self.stamina_capacity == 0: #TODO stamina model
                #TODO actions.append(Say(wait_request_message=WaitRequestMessage()))
                pass

        return True