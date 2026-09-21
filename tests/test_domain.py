"""Checks the domain model and the policy."""

from __future__ import annotations

import pytest

from conftest import decision_with
from routing.domain import Mood, MoodLevel, Queue, RoutingPolicy, Urgency, UrgencyLevel


def test_every_queue_carries_a_description() -> None:
    for queue in Queue:
        assert queue.description.strip()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, UrgencyLevel.ROUTINE),
        (0.4, UrgencyLevel.ROUTINE),
        (1.6, UrgencyLevel.URGENT),
        (2.01, UrgencyLevel.URGENT),
        (3.0, UrgencyLevel.IMMEDIATE),
    ],
)
def test_urgency_rounds_to_the_nearest_level(
    value: float, expected: UrgencyLevel
) -> None:
    assert Urgency(value=value, confidence=0.9).level is expected


def test_levels_stay_inside_the_valid_range() -> None:
    assert UrgencyLevel.from_rank(-3) is UrgencyLevel.ROUTINE
    assert UrgencyLevel.from_rank(99) is UrgencyLevel.IMMEDIATE
    assert MoodLevel.from_rank(-1) is MoodLevel.FACTUAL
    assert MoodLevel.from_rank(42) is MoodLevel.OUTRAGED


def test_mood_rounds_like_urgency() -> None:
    assert Mood(value=0.4, confidence=0.8).level is MoodLevel.FACTUAL
    assert Mood(value=2.6, confidence=0.8).level is MoodLevel.OUTRAGED


def test_runner_up_names_the_strongest_alternative(ticket) -> None:
    decision = decision_with(ticket, queue=Queue.BILLING, confidence=0.70)
    runner_up = decision.runner_up
    assert runner_up is not None
    assert runner_up[0] is not Queue.BILLING


def test_a_sure_assignment_runs_automatically(ticket) -> None:
    policy = RoutingPolicy(min_confidence=0.80)
    sure = decision_with(ticket, confidence=0.95)
    unsure = decision_with(ticket, confidence=0.55)
    assert policy.runs_automatically(sure)
    assert not policy.runs_automatically(unsure)
    assert policy.next_step(unsure) == "Review desk"


def test_escalation_comes_before_urgency(ticket) -> None:
    policy = RoutingPolicy()
    decision = decision_with(ticket, urgency=3.0, escalation=0.88)
    assert policy.escalates(decision)
    assert policy.is_rush(decision)
    assert policy.next_step(decision) == "Escalation to the team lead"


def test_urgent_tickets_go_into_rush_handling(ticket) -> None:
    policy = RoutingPolicy()
    decision = decision_with(ticket, queue=Queue.TECHNICAL, urgency=2.4)
    assert policy.next_step(decision) == "Rush handling in technical"


def test_calm_tickets_run_as_usual(ticket) -> None:
    policy = RoutingPolicy()
    decision = decision_with(ticket, urgency=0.3)
    assert policy.next_step(decision) == "Standard handling in billing"


def test_full_text_carries_subject_and_body(ticket) -> None:
    assert ticket.subject in ticket.full_text
    assert ticket.body in ticket.full_text


def test_a_loud_tone_on_a_small_matter_stands_out(ticket) -> None:
    loud_and_small = decision_with(ticket, urgency=0.2, mood=3.0)
    assert loud_and_small.tone_above_substance == pytest.approx(2.8)


def test_a_calm_tone_on_a_large_matter_stands_out(ticket) -> None:
    quiet_emergency = decision_with(ticket, urgency=3.0, mood=0.5)
    assert quiet_emergency.tone_above_substance == pytest.approx(-2.5)


def test_tone_does_not_change_the_next_step(ticket) -> None:
    policy = RoutingPolicy()
    quiet = decision_with(ticket, urgency=0.2, mood=0.0)
    loud = decision_with(ticket, urgency=0.2, mood=3.0)
    assert policy.next_step(quiet) == policy.next_step(loud)


def test_the_expectation_scores_the_choice(ticket) -> None:
    assert decision_with(ticket, queue=Queue.BILLING).matches_expectation is True
    assert decision_with(ticket, queue=Queue.SALES).matches_expectation is False


def test_a_ticket_without_expectation_stays_unscored(ticket) -> None:
    from dataclasses import replace

    unscored = replace(ticket, expected_queue=None)
    assert decision_with(unscored).matches_expectation is None
