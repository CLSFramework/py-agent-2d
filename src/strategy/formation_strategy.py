from src.interfaces.IPositionStrategy import IPositionStrategy
from src.strategy.formation_file import *
from src.interfaces.IAgent import IAgent
from src.strategy.player_role import PlayerRole, RoleName, RoleType, RoleSide
from enum import Enum
from pyrusgeom.soccer_math import *
from service_pb2 import *
import logging



class Situation(Enum):
    """
    Enum class representing different game situations in a 2D soccer simulation.

    Attributes:
        OurSetPlay_Situation (int): Represents a situation where our team is executing a set play.
        OppSetPlay_Situation (int): Represents a situation where the opposing team is executing a set play.
        Defense_Situation (int): Represents a defensive situation for our team.
        Offense_Situation (int): Represents an offensive situation for our team.
        PenaltyKick_Situation (int): Represents a penalty kick situation.
    """
    OurSetPlay_Situation = 0,
    OppSetPlay_Situation = 1,
    Defense_Situation = 2,
    Offense_Situation = 3,
    PenaltyKick_Situation = 4

class Formation:
    """
    A class to manage different soccer formations for various game situations.

    Attributes:
        before_kick_off_formation (FormationFile): Formation used before the kick-off.
        defense_formation (FormationFile): Formation used during defense.
        offense_formation (FormationFile): Formation used during offense.
        goalie_kick_opp_formation (FormationFile): Formation used when the opponent's goalie kicks.
        goalie_kick_our_formation (FormationFile): Formation used when our goalie kicks.
        kickin_our_formation (FormationFile): Formation used during our team's kick-in.
        setplay_opp_formation (FormationFile): Formation used during the opponent's set play.
        setplay_our_formation (FormationFile): Formation used during our team's set play.

    Args:
        path (str): The path to the directory containing the formation configuration files.
        logger (logging.Logger): Logger instance for logging formation-related information.
    """
    def __init__(self, path, logger: logging.Logger):
        # Initialize formation files for different game situations
        # before_kick_off_formation: Formation used before the kick-off
        self.before_kick_off_formation: FormationFile = FormationFile(f'{path}/before-kick-off.conf', logger)
        # defense_formation: Formation used during defense
        self.defense_formation: FormationFile = FormationFile(f'{path}/defense-formation.conf', logger)
        # offense_formation: Formation used during offense
        self.offense_formation: FormationFile = FormationFile(f'{path}/offense-formation.conf', logger)
        # goalie_kick_opp_formation: Formation used when the opponent's goalie kicks
        self.goalie_kick_opp_formation: FormationFile = FormationFile(f'{path}/goalie-kick-opp-formation.conf', logger)
        # goalie_kick_our_formation: Formation used when our goalie kicks
        self.goalie_kick_our_formation: FormationFile = FormationFile(f'{path}/goalie-kick-our-formation.conf', logger)
        # kickin_our_formation: Formation used during our team's kick-in
        self.kickin_our_formation: FormationFile = FormationFile(f'{path}/kickin-our-formation.conf', logger)
        # setplay_opp_formation: Formation used during the opponent's set play
        self.setplay_opp_formation: FormationFile = FormationFile(f'{path}/setplay-opp-formation.conf', logger)
        # setplay_our_formation: Formation used during our team's set play
        self.setplay_our_formation: FormationFile = FormationFile(f'{path}/setplay-our-formation.conf', logger)
        
class FormationStrategy(IPositionStrategy):
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.formations: dict[str, Formation] = {}
        
        self._read_formations()
        self._set_formation(None)
        
        self._poses: dict[int, Vector2D] = {(i, Vector2D(0, 0)) for i in range(11)}
        self.current_situation = Situation.Offense_Situation
        self.current_formation_file: FormationFile = self._get_current_formation().offense_formation

    def _read_formations(self):
        self.formations['4-3-3'] = Formation('src/formations/4-3-3', self.logger)
        self.formations['4-3-3-cyrus-base'] = Formation('src/formations/4-3-3-cyrus-base', self.logger)
        self.formations['4-3-3-helios-base'] = Formation('src/formations/4-3-3-helios-base', self.logger)
        
    def _get_current_formation(self) -> Formation:
        return self.formations[self.selected_formation_name]
    
    def _set_formation(self, wm: WorldModel):
        self.selected_formation_name = '4-3-3-cyrus-base' # '4-3-3' '4-3-3-cyrus-base' '4-3-3-helios-base'
        
    def update(self, agent: IAgent):
        logger = agent.logger
        logger.debug(f'---- update strategy ----')
        
        wm: WorldModel = agent.wm
        
        self._set_formation(wm)
        
        tm_min = wm.intercept_table.first_teammate_reach_steps
        opp_min = wm.intercept_table.first_opponent_reach_steps
        self_min = wm.intercept_table.self_reach_steps
        all_min = min(tm_min, opp_min, self_min)
        current_ball_pos = Vector2D(wm.ball.position.x, wm.ball.position.y)
        current_ball_vel = Vector2D(wm.ball.velocity.x, wm.ball.velocity.y)
        ball_pos = inertia_n_step_point(current_ball_pos, current_ball_vel, all_min, 0.96) #todo use server param ball decay
        

        if wm.game_mode_type is GameModeType.PlayOn:
            thr = 0
            if ball_pos.x() > 0:
                thr += 1
            if wm.self.uniform_number > 6:
                thr += 1
            if min(tm_min, self_min) < opp_min + thr:
                self.current_situation = Situation.Offense_Situation
            else:
                self.current_situation = Situation.Defense_Situation
        elif wm.game_mode_type is GameModeType.PenaltyKick_:
            self.current_situation = Situation.PenaltyKick_Situation
        elif wm.game_mode_type is not GameModeType.PlayOn and wm.game_mode_side is wm.our_side:
            self.current_situation = Situation.OurSetPlay_Situation
        else:
            self.current_situation = Situation.OppSetPlay_Situation

        if self.current_situation is Situation.Offense_Situation:
            self.current_formation_file = self._get_current_formation().offense_formation
        elif self.current_situation is Situation.Defense_Situation:
            self.current_formation_file = self._get_current_formation().defense_formation
        elif wm.game_mode_type in [GameModeType.KickIn_, GameModeType.CornerKick_]:
            if wm.game_mode_side is wm.our_side:
                self.current_formation_file = self._get_current_formation().kickin_our_formation
            else:
                self.current_formation_file = self._get_current_formation().setplay_opp_formation
        elif wm.game_mode_type in [GameModeType.GoalKick_, GameModeType.GoalieCatch_]:
            if wm.game_mode_side is wm.our_side:
                self.current_formation_file = self._get_current_formation().goalie_kick_our_formation
            else:
                self.current_formation_file = self._get_current_formation().goalie_kick_opp_formation
        elif wm.game_mode_type in [GameModeType.BeforeKickOff, GameModeType.AfterGoal_]:
            self.current_formation_file = self._get_current_formation().before_kick_off_formation
        elif self.current_situation is Situation.OppSetPlay_Situation:
            self.current_formation_file = self._get_current_formation().setplay_opp_formation
        elif self.current_situation is Situation.OurSetPlay_Situation:
            self.current_formation_file = self._get_current_formation().setplay_our_formation

        self.current_formation_file.update(ball_pos)
        self._poses = self.current_formation_file.get_poses()

        if wm.game_mode_type in [GameModeType.BeforeKickOff, GameModeType.AfterGoal_]:
            for pos in self._poses.values():
                pos._x = min(pos.x(), -0.5)
        else:
            offside_line = wm.offside_line_x
            for pos in self._poses.values():
                pos._x = min(pos.x(), offside_line - 0.5)
                
        logger.debug(f'{self._poses=}')
        
    def get_position(self, uniform_number, agent: IAgent=None) -> Vector2D:
        return self._poses[uniform_number]
    
    def get_role_name(self, uniform_number) -> RoleName:
        return self.current_formation_file.get_role(uniform_number).name
    
    def get_role_type(self, uniform_number) -> RoleType:
        return self.current_formation_file.get_role(uniform_number).type
    
    def get_role_side(self, uniform_number) -> RoleSide:
        return self.current_formation_file.get_role(uniform_number).side
    
    def get_role_pair(self, uniform_number) -> int:
        return self.current_formation_file.get_role(uniform_number).pair
    
    def get_role(self, uniform_number) -> PlayerRole:
        return self.current_formation_file.get_role(uniform_number)
    
    def get_offside_line(self):
        home_poses_x = [pos.x() for pos in self._poses.values()]
        home_poses_x.sort()
        if len(home_poses_x) > 1:
            return home_poses_x[1]
        elif len(home_poses_x) == 1:
            return home_poses_x[0]
        else:
            return 0.0