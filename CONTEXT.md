# Ticket Booking Context

This context describes the language for a Korean-localized ticket booking demo focused on browsing performances, selecting seats, and paying with internal points.

## Language

**Performance**:
A public cultural event shown to users for ticket booking, sourced from KOPIS metadata.
_Avoid_: Event, concert

**Performance Metadata**:
The descriptive information about a Performance, such as title, venue, dates, poster, and category.
_Avoid_: KOPIS data, event info

**KOPIS-Shaped Data**:
Local Performance Metadata seeded from or modeled after KOPIS for demo reliability.
_Avoid_: Live KOPIS feed, production ETL

**Venue**:
The place where a Performance is held, sourced from KOPIS facility metadata.
_Avoid_: Stage, concert hall

**Saved Performance**:
A Performance that a user keeps in My Page for later viewing.
_Avoid_: Cart item, wishlist item, favorite

**Seat**:
A selectable place for attending a Performance, represented by a mock seat map in this demo.
_Avoid_: Slot, chair

**Mock Seat Map**:
A demo-owned seat layout for a Performance, independent of raw KOPIS seat text.
_Avoid_: KOPIS seat data, parsed seat map

**Seat Grade**:
A pricing tier assigned to seats for a Performance.
_Avoid_: Seat class, price type

**Seat Availability**:
Whether a Seat can still become part of a Booking for a Performance.
_Avoid_: Seat hold, seat inventory

**Booking**:
The user's confirmed claim to attend a Performance in a selected Seat after point payment succeeds.
_Avoid_: Reservation, order

**Booking Snapshot**:
The Performance and Seat details copied into a Booking when it is confirmed so history remains readable.
_Avoid_: Denormalized event data, cached booking info

**Booking Request**:
The user's attempt to book a selected Seat for a Performance before the Booking is confirmed.
_Avoid_: Payment request, reservation request

**Booking Request Status**:
The current outcome stage of a Booking Request: pending, processing, confirmed, or failed.
_Avoid_: Queue state, payment status

**Booking Failure Reason**:
The reason a Booking Request could not become a Booking.
_Avoid_: Error code, payment error

**Booking Queue**:
A first-in-first-out flow that limits how many Booking Requests are processed at once.
_Avoid_: Waiting room, traffic queue

**Point Payment**:
A payment made by deducting the user's internal point balance.
_Avoid_: Real payment, settlement

**Payment History**:
A user's chronological record of Point Payments.
_Avoid_: Transaction history, ledger

**Point Balance**:
The amount of internal currency currently available to a user for Point Payments.
_Avoid_: Wallet, cash balance

**Login Identity**:
The authenticated user identity trusted by backend services after login.
_Avoid_: OAuth account, member session

**My Page**:
The user's personal page for viewing recent Booking and Point Payment history.
_Avoid_: Account page, profile
