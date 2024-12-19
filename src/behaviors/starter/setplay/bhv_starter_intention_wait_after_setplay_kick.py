from src.interfaces.IAgent import IAgent
from service_pb2 import *

class BhvStarterIntentionWaitAfterSetPlayKick:

    def __init__(self):
        pass

    def finished(self, agent: IAgent) -> bool:
        wm = agent.wm

        if wm.kickable_opponent_existance:
            return True

        if not wm.self.is_kickable:
            return True

        return False

    def execute(self, agent: IAgent) -> bool:
        return [PlayerAction(bhv_body_neck_to_ball=Bhv_BodyNeckToBall())]
