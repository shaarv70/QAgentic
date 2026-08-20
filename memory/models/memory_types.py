from enum import Enum


class MemoryType(str, Enum):

    """
    Defines the type of knowledge represented by a memory.
    """

    # Semantic memory
    PROJECT_FACT = "project_fact"
    USER_PREFERENCE = "user_preference"
    DOMAIN_KNOWLEDGE = "domain_knowledge"

    # Episodic memory
    EXECUTION = "execution"
    FAILURE = "failure"
    CORRECTION = "correction"
    REVIEW = "review"

    # Procedural memory
    WORKFLOW_PATTERN = "workflow_pattern"
    DECISION = "decision"




class MemoryScope(str, Enum):
    """
    Defines the scope to which a memory belongs.
    """

    USER = "user"
    PROJECT = "project"
    CONVERSATION = "conversation"
    WORKFLOW = "workflow"




class MemorySource(str, Enum):
    """
    Defines where the memory originated.
    """

    USER_INPUT = "user_input"
    CONVERSATION = "conversation"
    WORKFLOW = "workflow"
    AGENT_OUTPUT = "agent_output"
    MANUAL = "manual"
    SYSTEM="system"




class MemoryImportance(str, Enum):
    """
    Defines the relative importance of a memory.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"