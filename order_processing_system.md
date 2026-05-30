# Order Processing System

## Objective

Build a production-style asynchronous order processing system using:

- FastAPI
- PostgreSQL
- RabbitMQ
- SQLAlchemy
- Async workers
- Retry handling
- Dead Letter Queues (DLQ)
- Event-driven architecture
- Broker abstraction layer
- Observability

The project should be built incrementally in phases.

---

# Phase 1: Async Order Processing

## Goal
Implement basic producer → queue → worker flow.

### API
`POST /orders`

Request:
```json
{
  "customer_name": "Ankur",
  "amount": 2500
}
```

Response:
```json
{
  "order_id": 123,
  "status": "PENDING"
}
```

### Database
orders:
- id
- customer_name
- amount
- status
- created_at

Initial status: `PENDING`

### RabbitMQ
Queue: `orders`

Message:
```json
{
  "order_id": 123
}
```

### Worker Flow
Receive message → Sleep 5 seconds → Update order status to PROCESSED

---

# Phase 2: Order Lifecycle

Statuses:
- PENDING
- PROCESSING
- PROCESSED
- FAILED

New endpoint:
`GET /orders/{id}`

Worker flow:
PENDING → PROCESSING → PROCESSED

Failure:
PROCESSING → FAILED

---

# Phase 3: Retry Mechanism

Add column:
- retry_count

Simulate failures.

Rules:
- Increment retry_count on failure
- Republish message
- Maximum 3 retries

---

# Phase 4: Dead Letter Queue

Queue:
`orders.dlq`

Rules:
- After 3 retries, stop retrying
- Publish to DLQ
- Mark order FAILED

DLQ worker logs failed orders.

---

# Phase 5: Horizontal Scaling

Run multiple workers.

Configure:
```python
prefetch_count = 1
```

Verify work distribution among workers.

---

# Phase 6: Event-Driven Architecture

Exchange:
`order.events` (fanout)

Publish:
```json
{
  "event": "ORDER_PROCESSED",
  "order_id": 123
}
```

Subscribers:
- Email Worker
- Analytics Worker
- Audit Worker

---

# Phase 7: Broker Abstraction

```python
class MessageBroker:
    async def publish(...):
        ...
    async def consume(...):
        ...
```

Implement:
- RabbitMQBroker

Business logic should depend on the abstraction.

---

# Phase 8: Production Features

Add:

- Structured logging
- Correlation IDs
- Graceful shutdown
- Metrics

Metrics:
- orders_processed
- orders_failed
- retry_count
- messages_in_dlq

---

# Final Architecture

FastAPI
↓
Orders Queue
↓
Workers
↓
order.events
↓
Email / Analytics / Audit Workers

Failures:
↓
orders.dlq
↓
DLQ Worker

## Learning Outcomes

- RabbitMQ queues
- Exchanges
- Fanout routing
- Workers
- Competing consumers
- Retries
- Dead Letter Queues
- FastAPI
- Async SQLAlchemy
- Event-driven architecture
- Broker abstraction design
- Observability
