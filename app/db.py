from app.models import Item, ClaimOut, ItemStatus

items: dict[int, Item] = {
    12: Item(
        id=12, title="Blue water bottle", category="bottle",
        description="Metal bottle with a sticker on the side.",
        location_found="Building A, lecture hall 2",
        date_found="2026-10-01", status=ItemStatus.open,
        finder_contact="finder@example.com",
    )
}

claims: dict[int, ClaimOut] = {}

_claim_counter = 0
def next_claim_id() -> int:
    global _claim_counter
    _claim_counter += 1
    return _claim_counter