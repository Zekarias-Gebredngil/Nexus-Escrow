from app.models.escrow import EscrowState
from app.services.state_machine import can_transition


def test_expected_happy_path_transitions_are_allowed() -> None:
    assert can_transition(EscrowState.INITIATED, EscrowState.WAITING_FOR_PAYMENT)
    assert can_transition(EscrowState.WAITING_FOR_PAYMENT, EscrowState.PAID)
    assert can_transition(EscrowState.PAID, EscrowState.SHIPPED)
    assert can_transition(EscrowState.SHIPPED, EscrowState.RELEASED)


def test_dispute_path_transitions_are_allowed() -> None:
    assert can_transition(EscrowState.SHIPPED, EscrowState.DISPUTED)
    assert can_transition(EscrowState.DISPUTED, EscrowState.RELEASED)
    assert can_transition(EscrowState.DISPUTED, EscrowState.REFUNDED)


def test_terminal_states_do_not_transition() -> None:
    assert not can_transition(EscrowState.RELEASED, EscrowState.REFUNDED)
    assert not can_transition(EscrowState.REFUNDED, EscrowState.RELEASED)
