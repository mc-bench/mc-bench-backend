import enum


# Any values added here must also be added to the DB via a migration
# see d618a24f0bed_add_generation_state_and_run_state_.py for an example
class RUN_STATE(enum.Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IN_RETRY = "IN_RETRY"


class RUN_STAGE_STATE(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IN_RETRY = "IN_RETRY"


# Any values added here must also be added to the DB via a migration
# see d618a24f0bed_add_generation_state_and_run_state_.py for an example
class GENERATION_STATE(enum.Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    IN_RETRY = "IN_RETRY"
    FAILED = "FAILED"


class STAGE(enum.Enum):
    PROMPT_EXECUTION = "PROMPT_EXECUTION"
    RESPONSE_PARSING = "RESPONSE_PARSING"
    CODE_VALIDATION = "CODE_VALIDATION"
    BUILDING = "BUILDING"
    RENDERING_SAMPLE = "RENDERING_SAMPLE"
    EXPORTING_CONTENT = "EXPORTING_CONTENT"
    POST_PROCESSING = "POST_PROCESSING"
    PREPARING_SAMPLE = "PREPARING_SAMPLE"


class EXPERIMENTAL_STATE(enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    RELEASED = "RELEASED"
    DEPRECATED = "DEPRECATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    REJECTED = "REJECTED"
