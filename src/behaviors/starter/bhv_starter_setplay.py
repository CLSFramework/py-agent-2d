from typing import TYPE_CHECKING
from src.interfaces.IBehavior import IBehavior
from src.interfaces.IAgent import IAgent
import math
from service_pb2 import *
from pyrusgeom.vector_2d import Vector2D
from pyrusgeom.segment_2d import Segment2D
from pyrusgeom.circle_2d import Circle2D
from pyrusgeom.angle_deg import AngleDeg
from src.utils.tools import Tools
from src.utils.tools import Tools
from src.behaviors.starter.setplay.bhv_starter_setplay_kickoff import (
    BhvStarterSetPlayKickOff,
)
from src.behaviors.starter.setplay.bhv_starter_their_goal_kick_move import (
    BhvStarterTheirGoalKickMove,
)
from src.behaviors.starter.setplay.bhv_starter_setplay_freekick import (
    BhvStarterSetPlayFreeKick,
)
from src.behaviors.starter.setplay.bhv_starter_setplay_goal_kick import (
    BhvStarterSetPlayGoalKick,
)
from src.behaviors.starter.setplay.bhv_starter_setplay_kickin import (
    BhvStarterSetPlayKickIn,
)
from src.behaviors.starter.setplay.bhv_starter_setplay_indirect_freekick import (
    BhvStarterSetPlayIndirectFreeKick,
)

if TYPE_CHECKING:
    from src.sample_player_agent import SamplePlayerAgent


class BhvStarterSetPlay(IBehavior):
    def __init__(self):
        self.setplay_kickoff = BhvStarterSetPlayKickOff()
        self.their_goal_kick_move = BhvStarterTheirGoalKickMove()
        self.setplay_freekick = BhvStarterSetPlayFreeKick()
        self.setplay_goal_kick = BhvStarterSetPlayGoalKick()
        self.setplay_kickin = BhvStarterSetPlayKickIn()
        self.setplay_indirect_freekick = BhvStarterSetPlayIndirectFreeKick()

    def execute(self, agent: "SamplePlayerAgent"):
        '''
            Executes the set play behavior for the agent based on different type of set plays.
            Args:
                agent (SamplePlayerAgent): The agent that will execute the behavior.
            Returns:
                bool: True if any action was added to the agent action list, False otherwise.
        '''
        agent.logger.debug("BhvStarterSetPlay.execute")
        wm = agent.wm

        # Execute goalie set play behavior
        if wm.self.is_goalie:
            if (
                wm.game_mode_type != GameModeType.BackPass_
                and wm.game_mode_type != GameModeType.IndFreeKick_
            ):
                agent.add_action(
                    PlayerAction(bhv_goalie_free_kick=bhv_goalieFreeKick())
                )  # TODO
                return True
            else:
                self.setplay_indirect_freekick.execute(agent)
                return True

        # Execute agent if game mode is kickoff
        if wm.game_mode_type == GameModeType.KickOff_:
            if wm.game_mode_side == wm.our_side:
                return self.setplay_kickoff.execute(agent)
            else:
                return self.do_basic_their_set_play_move(agent)

        # Execute agent if game mode is corner kick or kick in
        if wm.game_mode_type in [GameModeType.KickIn_, GameModeType.CornerKick_]:
            if wm.game_mode_side == wm.our_side:
                return self.setplay_kickin.execute(agent)
            else:
                return self.do_basic_their_set_play_move(agent)

        if wm.game_mode_type == GameModeType.GoalKick_:
            if wm.game_mode_side == wm.our_side:
                return self.setplay_goal_kick.execute(agent)
            else:
                return self.their_goal_kick_move.execute(agent)
            
        # Execute agent if game mode is indirect free kick 
        if wm.game_mode_type in [GameModeType.BackPass_, GameModeType.IndFreeKick_]:
            return self.setplay_indirect_freekick.execute(agent)
        
        # Execute agent if game mode is foul charge or foul push
        if wm.game_mode_type in [GameModeType.FoulCharge_, GameModeType.FoulPush_]:
            if (
                abs(wm.ball.position.x - agent.server_params.our_penalty_area_line_x) < 1.0
                and abs(wm.ball.position.y)
                < agent.server_params.penalty_area_half_width + 1.0
            ):
                return self.setplay_indirect_freekick.execute(agent)

        # Execute agent is any other mode
        if wm.is_our_set_play:
            return self.setplay_freekick.execute(agent)
        else:
            return self.do_basic_their_set_play_move(agent)
        
    #Find the best dash power in setplay mode
    def get_set_play_dash_power(self, agent: "SamplePlayerAgent"):
        wm = agent.wm
        if not wm.is_our_set_play:
            target_point = agent.strategy.get_position(wm.self.uniform_number, agent)
            if target_point.x() > wm.self.position.x:
                if wm.ball.position.x < -30.0 and target_point.x() < wm.ball.position.x:
                    return wm.self.get_safety_dash_power
                rate = 0.0
                if wm.self.stamina > agent.server_params.stamina_max * 0.8:
                    rate = 1.5 * wm.self.stamina / agent.server_params.stamina_max
                else:
                    rate = (
                        0.9
                        * (wm.self.stamina - agent.server_params.recover_dec_thr)
                        / agent.server_params.stamina_max
                    )
                    rate = max(0.0, rate)
                return (
                    agent.player_types[wm.self.id].stamina_inc_max
                    * wm.self.recovery
                    * rate
                )
        return wm.self.get_safety_dash_power

    def can_go_to(
        self, agent: IAgent, wm, ball_circle: Circle2D, target_point: Vector2D
    ) -> bool:
        '''
        Check if the agent can go to the target point based on the restricted circle in setplay mode.
        Args:
            agent (IAgent): The agent object containing server parameters and player information.
            wm: The world model object containing the current state of the game.
            ball_circle: The restricted circle around the ball.
            target_point: The target point to be evaluated.
        Returns:
            bool: True if the agent can go to the target point, False otherwise.
        '''
        wm = agent.wm
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)

        move_line = Segment2D(self_position, target_point)
        n_intersection = ball_circle.intersection(move_line)


        if n_intersection == 0:
            return True

        if n_intersection == 1:
            angle = Vector2D(target_point - self_position).th()
            if abs(angle - wm.ball.angle_from_self) > 80.0:
                return True
        return False

    def get_avoid_circle_point(self, wm, target_point, agent: IAgent):
        '''
        Find the best target point based on the restricted circle in setplay mode.
        Args:
            wm: The world model object containing the current state of the game.
            target_point: The initial target point to be evaluated.
            agent (IAgent): The agent object containing server parameters and player information.
        Returns:
            Vector2D: The best target point that avoids the restricted circle.
        '''
        SP = agent.server_params
        wm = agent.wm
        avoid_radius = SP.center_circle_r + agent.player_types[wm.self.id].player_size
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        restricted_circle = Circle2D(ball_position, avoid_radius)
        #check if the agent can go to the target_point base on the restricted_circle 
        if self.can_go_to(agent, wm, restricted_circle, target_point):
            return target_point
        
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)
        target_angle = Vector2D(target_point - self_position).th()
        ball_target_angle = Vector2D(target_point - ball_position).th()
        ball_ang = AngleDeg(wm.ball.angle_from_self)
        ball_is_left = ball_ang.is_left_of(target_angle)
        
        #angle_step base on position of the ball if the ball is left of the target it tries find the new target counter clock wise of the restricted circle
        angle_step = 1 if ball_is_left else -1
        
        for angle in range(30*angle_step , 180* angle_step , 30*angle_step):
            new_target = ball_position + Vector2D.polar2vector(avoid_radius + 1.0 , angle)
            if (
                abs(new_target.x()) > SP.pitch_half_length + SP.pitch_margin - 1.0
                or abs(new_target.y()) > SP.pitch_half_width + SP.pitch_margin - 1.0
            ):  # TODO pith_margin
                break
            if self.can_go_to(agent, wm, restricted_circle, new_target):
                return new_target


        return target_point

    def is_kicker(self, agent: "SamplePlayerAgent"):
        '''
        Check if the agent is the kicker in setplay mode.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        Returns:
            bool: True if the agent is the kicker, False otherwise.
        '''
        wm = agent.wm
        min_dist = 10000.0
        unum = 0
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)
        #find minimum distance between the our team agents and the ball
        for i in range(1,12):
            if i == wm.our_goalie_uniform_number and not wm.game_mode_type == GameModeType.GoalieCatch_:
                continue

            if i == wm.our_goalie_uniform_number:
                home_pos: Vector2D = Tools.convert_rpc_vector2d_to_vector2d(wm.teammates[wm.our_goalie_uniform_number - 1].position)
                
            else :
                home_pos: Vector2D = agent.strategy.get_position(i, agent)

            if home_pos.dist(ball_position) < min_dist:
                min_dist = home_pos.dist(ball_position)
                unum = i

                
        if wm.self.uniform_number == unum:
            return True
        return False

    
    def is_delaying_tactics_situation(self, agent: IAgent): 
        ''' 
        Check if the situation involves delaying tactics. 
        Args: 
            agent (IAgent): The agent that will execute the behavior. 
        Returns: 
            bool: True if it is a delaying tactics situation, False otherwise. 
        '''
        wm = agent.wm
        # Calculate the number of cycles since the last set play started
        real_set_play_count = wm.cycle - wm.last_set_play_start_time

        wait_buf = 15 if wm.game_mode_type == GameModeType.GoalKick_ else 2

        if real_set_play_count >= agent.server_params.drop_ball_time - wait_buf:
            return False
        our_score = (
            wm.left_team_score if wm.our_side == Side.LEFT else wm.right_team_score
        )
        opp_score = (
            wm.right_team_score if wm.our_side == Side.LEFT else wm.left_team_score
        )
        """if wm.audioMemory().recoveryTime().cycle >= wm.cycle - 10:
            if our_score > opp_score:
                return True"""  # TODO audio memory
        cycle_thr = max(0, agent.server_params.nr_normal_halfs * (agent.server_params.half_time * 10)- 500)
        if wm.cycle < cycle_thr:
            return False
        if our_score > opp_score and our_score - opp_score <= 1:
            return True
        return False

    def do_basic_their_set_play_move(self, agent: "SamplePlayerAgent"):
        '''
        Perform the basic move during the opponent's set play.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
        '''
        wm = agent.wm  # Access the agent's world model

        target_point = agent.strategy.get_position(wm.self.uniform_number, agent)  # Determine the target position based on strategy
        ball_position = Vector2D(wm.ball.position.x, wm.ball.position.y)  # Get the ball's current position
        dash_power = self.get_set_play_dash_power(agent)  # Calculate the dash power for the set play
        ball_to_target = Vector2D(target_point - ball_position)  # Vector from the ball to the target

        # Adjust the target point if it is too close to the ball
        if ball_to_target.r() < 11.0:
            xdiff = math.sqrt(math.pow(11.0, 2) - math.pow(ball_to_target.y(), 2))
            target_point.set_x(wm.ball.position.x - xdiff)
            if target_point.x() < -45.0:
                target_point = ball_position
                target_point += ball_to_target.set_length_vector(11.0)

        # Adjust target point for kickoff offside rule
        if wm.game_mode_type == GameModeType.KickOff_ and agent.server_params.kickoff_offside:
            target_point.set_x(min(-1.0e-5, target_point.x()))

        adjusted_point = self.get_avoid_circle_point(wm, target_point, agent)  # Adjust the target to avoid obstacles
        dist_thr = wm.ball.dist_from_self * 0.1  # Calculate distance threshold based on ball distance

        if dist_thr < 0.7:
            dist_thr = 0.7

        self_velocity = Vector2D(wm.self.velocity.x, wm.self.velocity.y)  # Agent's current velocity
        self_position = Vector2D(wm.self.position.x, wm.self.position.y)  # Agent's current position

        # Adjust target point if necessary based on distance and inertia
        if (
            adjusted_point != target_point
            and ball_position.dist(target_point) > 10.0
            and Tools.inertia_final_point(
                agent.player_types[wm.self.id], self_position, self_velocity
            ).dist(adjusted_point)
            < dist_thr
        ):
            adjusted_point = target_point

        # Add the action to move to the target point
        agent.add_action(
            PlayerAction(
                body_go_to_point=Body_GoToPoint(
                    target_point=Tools.convert_vector2d_to_rpc_vector2d(adjusted_point),
                    distance_threshold=dist_thr,
                    max_dash_power=dash_power,
                )
            )
        )

        # Calculate the angle to turn the body based on ball position
        body_angle = wm.ball.angle_from_self
        body_angle += 90.0 if ball_position.y() < 0.0 else -90.0

        # Add the action to turn to the calculated angle
        agent.add_action(
            PlayerAction(body_turn_to_angle=Body_TurnToAngle(angle=body_angle))
        )

        return True

    def do_kick_wait(self, agent: "SamplePlayerAgent", action: PlayerAction = None):
        '''
        Perform the kick wait behavior for the agent.
        Args:
            agent (SamplePlayerAgent): The agent that will execute the behavior.
            action (PlayerAction): The action to be executed
        Returns:
            bool: True if any action was added to the agent action list, False otherwise.
        '''
        wm = agent.wm
        
        if action is None:
            action = PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1))

        real_set_play_count = wm.cycle - wm.last_set_play_start_time
        if real_set_play_count >= agent.server_params.drop_ball_time - 5:
            return False
        
        if self.is_delaying_tactics_situation(agent):
            agent.add_action(action)
            return True

        if len(Tools.get_teammates_from_ball(agent)) < 9:
            agent.add_action(action)
            return True

        if wm.set_play_count <= 3:
            agent.add_action(action)
            return True

        if (
            wm.set_play_count >= 15
            and wm.see_time == wm.cycle
            and wm.self.stamina > agent.server_params.stamina_max * 0.6
        ):
            return False

        if (
            wm.see_time != wm.cycle
            or wm.self.stamina < agent.server_params.stamina_max * 0.9
        ):
            agent.add_action(action)
            return True

        return False
    