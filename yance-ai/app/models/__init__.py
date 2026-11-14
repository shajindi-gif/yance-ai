from app.models.models import (  # noqa: F401
    AgentRun,
    AnalyticsEvent,
    Application,
    AuditLog,
    Company,
    Document,
    DocumentChunk,
    DocumentContent,
    DocumentFactCandidate,
    DocumentIngestionRun,
    Invoice,
    Opportunity,
    Order,
    Payment,
    PaymentEvent,
    Policy,
    PolicyRule,
    Tenant,
    User,
)

# Include park models when Alembic loads metadata without importing API routes.
from app.models.park_policy import (  # noqa: F401
    Park,
    ParkPolicyScope,
    PolicyCondition,
    PolicyEvalRun,
)

# Policy collection runtime tables (additive; imported for Alembic metadata).
from app.models.policy_collection import (  # noqa: F401
    PolicyApplicationWindow,
    PolicyAttachment,
    PolicyCollectionRun,
    PolicyDocumentKey,
    PolicyOrigin,
    PolicyRawEvidence,
    PolicySourceState,
)
