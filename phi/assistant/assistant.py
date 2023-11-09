from typing import List, Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, field_validator

from phi.assistant.file import File
from phi.assistant.tool import Tool
from phi.assistant.row import AssistantRow
from phi.assistant.storage import AssistantStorage
from phi.assistant.exceptions import AssistantIdNotSet
from phi.knowledge.base import KnowledgeBase

from phi.utils.log import logger, set_log_level_to_debug

try:
    from openai import OpenAI
    from openai.types.beta.assistant import Assistant as OpenAIAssistant
    from openai.types.beta.assistant_deleted import AssistantDeleted as OpenAIAssistantDeleted
except ImportError:
    logger.error("`openai` not installed")
    raise


class Assistant(BaseModel):
    # -*- LLM settings
    model: str = "gpt-4-1106-preview"
    openai: Optional[OpenAI] = None

    # -*- Assistant settings
    # Assistant id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always assistant.
    object: Optional[str] = None
    # The name of the assistant. The maximum length is 256 characters.
    name: Optional[str] = None
    # The description of the assistant. The maximum length is 512 characters.
    description: Optional[str] = None
    # The system instructions that the assistant uses. The maximum length is 32768 characters.
    instructions: Optional[str] = None

    # -*- Assistant Tools
    # A list of tool enabled on the assistant. There can be a maximum of 128 tools per assistant.
    # Tools can be of types code_interpreter, retrieval, or function.
    tools: Optional[List[Tool | Dict]] = None

    # -*- Assistant Files
    # A list of file IDs attached to this assistant.
    # There can be a maximum of 20 files attached to the assistant.
    # Files are ordered by their creation date in ascending order.
    file_ids: Optional[List[str]] = None
    # Files attached to this assistant.
    files: Optional[List[File]] = None

    # -*- Assistant Storage
    storage: Optional[AssistantStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = True
    # AssistantRow from the database: DO NOT SET THIS MANUALLY
    database_row: Optional[AssistantRow] = None

    # -*- Assistant Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # True if this assistant is active
    is_active: bool = True
    # The Unix timestamp (in seconds) for when the assistant was created.
    created_at: Optional[int] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    openai_assistant: Optional[OpenAIAssistant] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @property
    def client(self) -> OpenAI:
        return self.openai or OpenAI()

    def load_from_storage(self):
        pass

    def load_from_openai(self, openai_assistant: OpenAIAssistant):
        self.id = openai_assistant.id
        self.object = openai_assistant.object
        self.created_at = openai_assistant.created_at
        self.file_ids = openai_assistant.file_ids

    def create(self) -> "Assistant":
        request_body: Dict[str, Any] = {}
        if self.name is not None:
            request_body["name"] = self.name
        if self.description is not None:
            request_body["description"] = self.description
        if self.instructions is not None:
            request_body["instructions"] = self.instructions
        if self.tools is not None:
            _tools = []
            for _tool in self.tools:
                if isinstance(_tool, Tool):
                    _tools.append(_tool.to_dict())
                else:
                    _tools.append(_tool)
            request_body["tools"] = _tools
        if self.file_ids is not None or self.files is not None:
            _file_ids = self.file_ids or []
            if self.files is not None:
                for _file in self.files:
                    _file_ids.append(_file.get_id())
            request_body["file_ids"] = _file_ids
        if self.metadata is not None:
            request_body["metadata"] = self.metadata

        self.openai_assistant = self.client.beta.assistants.create(
            model=self.model,
            **request_body,
        )
        self.load_from_openai(self.openai_assistant)
        logger.debug(f"Assistant created: {self.id}")
        return self

    def get_id(self) -> Optional[str]:
        _id = self.id or self.openai_assistant.id if self.openai_assistant else None
        if _id is None:
            self.load_from_storage()
            _id = self.id
        return _id

    def get(self, use_cache: bool = True) -> "Assistant":
        if self.openai_assistant is not None and use_cache:
            return self

        _assistant_id = self.get_id()
        if _assistant_id is None:
            raise AssistantIdNotSet("Assistant.id not set")

        self.openai_assistant = self.client.beta.assistants.retrieve(
            assistant_id=_assistant_id,
        )
        self.load_from_openai(self.openai_assistant)
        return self

    def get_or_create(self, use_cache: bool = True) -> "Assistant":
        try:
            return self.get(use_cache=use_cache)
        except AssistantIdNotSet:
            return self.create()

    def update(self) -> "Assistant":
        try:
            assistant_to_update = self.get()
            if assistant_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.name is not None:
                    request_body["name"] = self.name
                if self.description is not None:
                    request_body["description"] = self.description
                if self.instructions is not None:
                    request_body["instructions"] = self.instructions
                if self.tools is not None:
                    _tools = []
                    for _tool in self.tools:
                        if isinstance(_tool, Tool):
                            _tools.append(_tool.to_dict())
                        else:
                            _tools.append(_tool)
                    request_body["tools"] = _tools
                if self.file_ids is not None or self.files is not None:
                    _file_ids = self.file_ids or []
                    if self.files is not None:
                        for _file in self.files:
                            _file_ids.append(_file.get_id())
                    request_body["file_ids"] = _file_ids
                if self.metadata:
                    request_body["metadata"] = self.metadata

                self.openai_assistant = self.client.beta.assistants.update(
                    assistant_id=assistant_to_update.id,
                    model=self.model,
                    **request_body,
                )
                self.load_from_openai(self.openai_assistant)
                logger.debug(f"Assistant updated: {self.id}")
                return self
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
            raise

    def delete(self) -> OpenAIAssistantDeleted:
        try:
            assistant_to_delete = self.get()
            if assistant_to_delete is not None:
                deletion_status = self.client.beta.assistants.delete(
                    assistant_id=assistant_to_delete.id,
                )
                logger.debug(f"Assistant deleted: {deletion_status.id}")
                return deletion_status
        except AssistantIdNotSet:
            logger.warning("Assistant not available")
            raise

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(
            exclude_none=True,
            include={
                "name",
                "model",
                "id",
                "object",
                "description",
                "instructions",
                "metadata",
                "tools",
                "file_ids",
                "files",
            },
        )

    def pprint(self):
        """Pretty print using rich"""
        from rich.pretty import pprint

        pprint(self.to_dict())

    def __str__(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=4)
