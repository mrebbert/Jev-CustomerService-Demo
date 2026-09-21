"""Checks the translation between the Jev API and the domain."""

from __future__ import annotations

import pytest
from typesafe_sdk import SystemOneResponse

from routing.domain import MoodLevel, Queue, UrgencyLevel
from routing.jev_client import (
    QUESTION_ESCALATION,
    QUESTION_MOOD,
    QUESTION_QUEUE,
    QUESTION_URGENCY,
    build_questions,
    to_decision,
)


def test_the_questions_cover_every_queue() -> None:
    questions = build_questions()
    assert set(questions) == {
        QUESTION_QUEUE,
        QUESTION_URGENCY,
        QUESTION_MOOD,
        QUESTION_ESCALATION,
    }
    assert set(questions[QUESTION_QUEUE].criteria) == {queue.value for queue in Queue}


def test_the_scales_carry_as_many_steps_as_the_domain() -> None:
    questions = build_questions()
    assert len(questions[QUESTION_URGENCY].criteria) == len(list(UrgencyLevel))
    assert len(questions[QUESTION_MOOD].criteria) == len(list(MoodLevel))


def test_an_answer_becomes_a_decision(ticket, jev_response) -> None:
    decision = to_decision(ticket, jev_response)

    assert decision.ticket is ticket
    assert decision.queue is Queue.BILLING
    assert decision.queue_confidence == pytest.approx(1.0)
    assert decision.urgency.value == pytest.approx(1.24)
    assert decision.urgency.confidence == pytest.approx(0.75)
    assert decision.urgency.level is UrgencyLevel.SOON
    assert decision.escalation_probability == pytest.approx(0.39)


def test_the_distribution_uses_the_queues_of_the_domain(ticket, jev_response) -> None:
    decision = to_decision(ticket, jev_response)
    assert set(decision.queue_distribution) == set(Queue)
    assert sum(decision.queue_distribution.values()) == pytest.approx(1.0)


def test_mood_arrives_with_score_and_confidence(ticket, jev_response) -> None:
    decision = to_decision(ticket, jev_response)
    assert decision.mood.value == pytest.approx(1.92)
    assert decision.mood.confidence == pytest.approx(0.92)
    assert decision.mood.level is MoodLevel.ANNOYED


def test_mood_and_urgency_stay_apart(ticket, jev_response) -> None:
    decision = to_decision(ticket, jev_response)
    assert decision.urgency.value != decision.mood.value
    assert decision.tone_above_substance == pytest.approx(1.92 - 1.24)


def test_a_wrong_answer_type_is_reported(ticket, jev_response) -> None:
    twisted = jev_response.model_dump()
    twisted["answers"][QUESTION_QUEUE] = {"type": "noul", "noul": 0.5}
    response = SystemOneResponse.model_validate(twisted)

    with pytest.raises(TypeError, match=QUESTION_QUEUE):
        to_decision(ticket, response)
