from typing import Any

import pytest

from domain.entities import Job, WorkflowSpec, WorkflowStep
from domain.services import StateMachine, WorkflowExecutionService
from domain.value_objects import JobStatus


class FakeAction:
    def __init__(self, should_fail: bool = False, output_val: Any = None):
        self.should_fail = should_fail
        self.output_val = output_val
        self.called_params: list[dict[str, Any]] = []
        self.called_context: list[dict[str, Any]] = []

    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> Any:
        self.called_params.append(params)
        self.called_context.append(context)
        if self.should_fail:
            raise ValueError("Simulated action failure")
        return self.output_val


def test_resolve_variables():
    step = WorkflowStep(
        action="type",
        params={"text": "Username: {username}", "count": 1, "nested": "{empty}"}
    )
    variables = {
        "username": "admin_user",
        "empty": None
    }

    resolved = WorkflowExecutionService._resolve_variables(step, variables)

    assert resolved.action == "type"
    assert resolved.params["text"] == "Username: admin_user"
    assert resolved.params["count"] == 1
    assert resolved.params["nested"] == ""


def test_workflow_execution_success():
    sm = StateMachine()
    login_action = FakeAction(output_val={"user_logged_in": "admin"})
    click_action = FakeAction(output_val="clicked")
    finish_action = FakeAction()

    action_registry = {
        "login": login_action,
        "click": click_action,
        "finish": finish_action,
    }

    service = WorkflowExecutionService(action_registry, sm)

    job = Job(id="job-1", workflow_id="flow-1", variables={"user": "gabriela"})
    spec = WorkflowSpec(
        id="flow-1",
        timeout=60,
        retries=1,
        variables={"btn_name": "Confirmar"},
        steps=[
            WorkflowStep(action="login", params={"username": "{user}"}),
            WorkflowStep(action="click", params={"target": "{btn_name}"}),
            WorkflowStep(action="finish")
        ]
    )

    outputs = service.execute(job, spec)

    # Validações
    assert len(job.steps) == 3
    assert job.steps[0].status == "success"
    assert job.steps[0].step == "login"
    assert job.steps[0].output == {"user_logged_in": "admin"}

    assert job.steps[1].status == "success"
    assert job.steps[1].step == "click"
    assert job.steps[1].output == "clicked"

    assert job.steps[2].status == "success"
    assert job.steps[2].step == "finish"

    # Outputs coletados
    assert outputs == {
        "login": {"user_logged_in": "admin"},
        "click": "clicked"
    }

    # Verifica se os parâmetros foram resolvidos corretamente
    assert login_action.called_params[0] == {"username": "gabriela"}
    assert click_action.called_params[0] == {"target": "Confirmar"}


def test_workflow_execution_stops_at_finish():
    sm = StateMachine()
    finish_action = FakeAction()
    post_finish_action = FakeAction()

    action_registry = {
        "finish": finish_action,
        "post_finish": post_finish_action
    }

    service = WorkflowExecutionService(action_registry, sm)
    job = Job(id="job-1", workflow_id="flow-1", variables={})
    spec = WorkflowSpec(
        id="flow-1",
        timeout=60,
        retries=1,
        variables={},
        steps=[
            WorkflowStep(action="finish"),
            WorkflowStep(action="post_finish")
        ]
    )

    service.execute(job, spec)

    assert len(job.steps) == 1
    assert job.steps[0].step == "finish"
    assert len(post_finish_action.called_params) == 0


def test_workflow_execution_action_failure():
    sm = StateMachine()
    login_action = FakeAction(should_fail=True)

    action_registry = {
        "login": login_action
    }

    service = WorkflowExecutionService(action_registry, sm)
    job = Job(id="job-1", workflow_id="flow-1", variables={})
    spec = WorkflowSpec(
        id="flow-1",
        timeout=60,
        retries=1,
        variables={},
        steps=[
            WorkflowStep(action="login")
        ]
    )

    with pytest.raises(RuntimeError) as excinfo:
        service.execute(job, spec)

    assert "Step 'login' falhou: Simulated action failure" in str(excinfo.value)
    assert len(job.steps) == 1
    assert job.steps[0].status == "error"
    assert job.steps[0].detail == "Simulated action failure"


def test_workflow_execution_unregistered_action():
    sm = StateMachine()
    service = WorkflowExecutionService(action_registry={}, state_machine=sm)

    job = Job(id="job-1", workflow_id="flow-1", variables={})
    spec = WorkflowSpec(
        id="flow-1",
        timeout=60,
        retries=1,
        variables={},
        steps=[
            WorkflowStep(action="login")
        ]
    )

    with pytest.raises(RuntimeError) as excinfo:
        service.execute(job, spec)

    assert "Step 'login' falhou: Acao 'login' nao registrada." in str(excinfo.value)
    assert len(job.steps) == 1
    assert job.steps[0].status == "error"
    assert job.steps[0].detail == "Acao 'login' nao registrada."
