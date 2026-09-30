from models.approval_model import (
    ApprovalRequest,
    ApprovalStatus,
)

from services.approval.approval_service import ApprovalService


class InMemoryApprovalService(ApprovalService):

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    async def create_request(
        self,
        request: ApprovalRequest,
    ) -> ApprovalRequest:

        existing = self._requests.get(request.request_id)

        # A request is identified by its stable request_id.
        # If the workflow resumes, we must return the same request
        # instead of creating a second approval record.
        if existing is not None:
            return existing

        self._requests[request.request_id] = request

        return request

    async def get_request(
        self,
        request_id: str,
    ) -> ApprovalRequest:

        request = self._requests.get(request_id)

        if request is None:
            raise KeyError(
                f"Approval request not found: {request_id}"
            )

        return request

    async def approve(
        self,
        request_id: str,
    ) -> ApprovalRequest:

        request = await self.get_request(request_id)

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Approval request '{request_id}' is already "
                f"{request.status.value}."
            )

        updated_request = ApprovalRequest(
            request_id=request.request_id,
            action=request.action,
            description=request.description,
            details=request.details,
            status=ApprovalStatus.APPROVED,
        )

        self._requests[request_id] = updated_request

        return updated_request

    async def reject(
        self,
        request_id: str,
    ) -> ApprovalRequest:

        request = await self.get_request(request_id)

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Approval request '{request_id}' is already "
                f"{request.status.value}."
            )

        updated_request = ApprovalRequest(
            request_id=request.request_id,
            action=request.action,
            description=request.description,
            details=request.details,
            status=ApprovalStatus.REJECTED,
        )

        self._requests[request_id] = updated_request

        return updated_request