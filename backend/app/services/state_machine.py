from app.models.escrow import EscrowState

ALLOWED_TRANSITIONS: dict[EscrowState, set[EscrowState]] = {
    EscrowState.INITIATED: {EscrowState.WAITING_FOR_PAYMENT},
    EscrowState.WAITING_FOR_PAYMENT: {EscrowState.PAID, EscrowState.REFUNDED},
    EscrowState.PAID: {EscrowState.SHIPPED, EscrowState.REFUNDED},
    EscrowState.SHIPPED: {EscrowState.DISPUTED, EscrowState.RELEASED},
    EscrowState.DISPUTED: {EscrowState.RELEASED, EscrowState.REFUNDED},
    EscrowState.RELEASED: set(),
    EscrowState.REFUNDED: set(),
}


def can_transition(from_state: EscrowState, to_state: EscrowState) -> bool:
    return to_state in ALLOWED_TRANSITIONS[from_state]
