from src.interfaces.IAgent import IAgent
from service_pb2 import *
from pyrusgeom.angle_deg import AngleDeg
class BhvStarterPrepareSetPlayKick:
    s_rest_wait_cycle = -1
    
    def __init__(self, ball_place_angle: float, wait_cycle: float):
        self.M_ball_place_angle = ball_place_angle
        self.M_wait_cycle = wait_cycle

    def execute(self, agent: IAgent) -> bool:
           
        from src.behaviors.starter.bhv_starter_go_to_placed_ball import BhvStarterGoToPlacedBall
        go_to_placed_ball = BhvStarterGoToPlacedBall(self.M_ball_place_angle)
        
        actions = []
        # Not reach the ball side
        actions += go_to_placed_ball.execute(agent)

        # Reach to ball side
        if self.s_rest_wait_cycle < 0:
            self.s_rest_wait_cycle = self.M_wait_cycle

        if self.s_rest_wait_cycle == 0:
            if (agent.wm.self.stamina < agent.server_params.stamina_max * 0.9 or agent.wm.self.seetime != agent.wm.cycle): #TODO
                self.s_rest_wait_cycle = 1

        if self.s_rest_wait_cycle > 0:
            if agent.wm.game_mode_type == GameModeType.KickOff_:
                moment = AngleDeg(agent.server_params.visible_angle)
                actions.append(PlayerAction(turn=Turn(relative_direction=moment)))
            else:
                actions.append(PlayerAction(body_turn_to_ball=Body_TurnToBall(cycle=1)))

            self.s_rest_wait_cycle -= 1

            return actions

        self.s_rest_wait_cycle = -1
        return []