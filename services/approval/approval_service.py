from abc import ABC, abstractmethod

from models.approval_model import ApprovalRequest


class ApprovalService(ABC):

    @abstractmethod
    async def create_request(
        self,
        request: ApprovalRequest,
    ) -> ApprovalRequest:
        raise NotImplementedError

    @abstractmethod
    async def get_request(
        self,
        request_id: str,
    ) -> ApprovalRequest:
        raise NotImplementedError

    @abstractmethod
    async def approve(
        self,
        request_id: str,
    ) -> ApprovalRequest:
        raise NotImplementedError

    @abstractmethod
    async def reject(
        self,
        request_id: str,
    ) -> ApprovalRequest:
        raise NotImplementedError