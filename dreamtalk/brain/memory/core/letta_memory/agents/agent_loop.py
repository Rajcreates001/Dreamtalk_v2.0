# Adapted from Letta (MemGPT) - Apache 2.0 License
from typing import TYPE_CHECKING

from dreamtalk.brain.memory.core.letta_memory.agents.base_agent_v2 import BaseAgentV2
from dreamtalk.brain.memory.core.letta_memory.agents.letta_agent_v2 import LettaAgentV2
from dreamtalk.brain.memory.core.letta_memory.agents.letta_agent_v3 import LettaAgentV3
from dreamtalk.brain.memory.core.letta_memory.groups.sleeptime_multi_agent_v3 import SleeptimeMultiAgentV3
from dreamtalk.brain.memory.core.letta_memory.groups.sleeptime_multi_agent_v4 import SleeptimeMultiAgentV4
from dreamtalk.brain.memory.core.letta_memory.schemas.agent import AgentState
from dreamtalk.brain.memory.core.letta_memory.schemas.enums import AgentType

if TYPE_CHECKING:
    from dreamtalk.brain.memory.core.letta_memory.orm import User


class AgentLoop:
    """Factory class for instantiating the agent execution loop based on agent type"""

    @staticmethod
    def load(agent_state: AgentState, actor: "User") -> BaseAgentV2:
        if agent_state.agent_type in [AgentType.letta_v1_agent, AgentType.sleeptime_agent]:
            if agent_state.enable_sleeptime:
                if agent_state.multi_agent_group is None:
                    # Agent has sleeptime enabled but no group - fall back to non-sleeptime agent
                    from dreamtalk.brain.memory.core.letta_memory.log import get_logger

                    logger = get_logger(__name__)
                    logger.warning(
                        f"Agent {agent_state.id} has enable_sleeptime=True but multi_agent_group is None. "
                        f"Falling back to standard LettaAgentV3."
                    )
                    return LettaAgentV3(
                        agent_state=agent_state,
                        actor=actor,
                    )
                return SleeptimeMultiAgentV4(
                    agent_state=agent_state,
                    actor=actor,
                    group=agent_state.multi_agent_group,
                )
            return LettaAgentV3(
                agent_state=agent_state,
                actor=actor,
            )
        elif agent_state.enable_sleeptime and agent_state.agent_type != AgentType.voice_convo_agent:
            if agent_state.multi_agent_group is None:
                # Agent has sleeptime enabled but no group - fall back to non-sleeptime agent
                from dreamtalk.brain.memory.core.letta_memory.log import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    f"Agent {agent_state.id} has enable_sleeptime=True but multi_agent_group is None. "
                    f"Falling back to standard LettaAgentV2."
                )
                return LettaAgentV2(
                    agent_state=agent_state,
                    actor=actor,
                )
            return SleeptimeMultiAgentV3(agent_state=agent_state, actor=actor, group=agent_state.multi_agent_group)
        else:
            return LettaAgentV2(
                agent_state=agent_state,
                actor=actor,
            )
