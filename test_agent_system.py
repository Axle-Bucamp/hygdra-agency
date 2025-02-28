import pytest
from agent import Agent, Environment, Action

def test_agent_learning():
    agent = Agent()
    initial_state = agent.get_state()
    agent.learn({"state": "A", "action": "move", "reward": 1})
    assert agent.get_state() != initial_state, "Agent should update its state after learning"

def test_agent_decision_making():
    agent = Agent()
    environment = Environment()
    action = agent.make_decision(environment)
    assert isinstance(action, Action), "Agent should return an Action object"

def test_agent_memory():
    agent = Agent()
    agent.remember("important_info")
    assert "important_info" in agent.get_memory(), "Agent should store information in memory"

def test_environment_complexity():
    environment = Environment()
    initial_state = environment.get_state()
    environment.update()
    assert environment.get_state() != initial_state, "Environment should change over time"

def test_action_consequences():
    environment = Environment()
    action = Action("move", {"direction": "north"})
    initial_state = environment.get_state()
    environment.apply_action(action)
    assert environment.get_state() != initial_state, "Action should have consequences on the environment"

def test_agent_environment_interaction():
    agent = Agent()
    environment = Environment()
    initial_env_state = environment.get_state()
    initial_agent_state = agent.get_state()
    
    action = agent.make_decision(environment)
    environment.apply_action(action)
    agent.learn(environment.get_feedback())
    
    assert environment.get_state() != initial_env_state, "Environment should change after agent's action"
    assert agent.get_state() != initial_agent_state, "Agent should update its state after interaction"

if __name__ == "__main__":
    pytest.main()