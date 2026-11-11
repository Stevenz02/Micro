from .context import ScenarioState


def before_scenario(context, scenario):
    context.state = ScenarioState()


def after_scenario(context, scenario):
    context.state.close()
