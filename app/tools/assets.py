"""Customer asset assistant tools."""

import logging
from time import perf_counter
from typing import Any

from pydantic import Field

from app.models.common import ApiModel
from app.models.session import RuntimeSession
from app.models.tools import (
    AssistantScope,
    ManufacturerScopeRequirement,
    ToolAuthorizationContext,
    ToolExecutionResponse,
)
from app.services.vam_client import VamClient
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CustomerAssetInput(ApiModel):
    """Input contract for listing customer assets."""

    page: int | None = None
    count: int | None = None
    search: str | None = None
    sort_field: str | None = Field(default=None, alias="sortField")
    order_by: str | None = Field(default=None, alias="orderBy")
    equipment_id: str | None = Field(default=None, alias="equipmentId")
    manufacturer_id: str | None = Field(default=None, alias="manufacturerId")
    non_onboarded_manufacturer_id: str | None = Field(default=None, alias="nonOnboardedManufacturerId")
    purchase_date: str | None = Field(default=None, alias="purchaseDate")
    dealer_name: str | None = Field(default=None, alias="dealerName")
    is_model_linked: bool | None = Field(default=None, alias="isModelLinked")
    manufacturer_type: str | None = Field(default=None, alias="manufacturerType")


class CustomerAssetTool(BaseTool):
    """List trusted customer assets."""

    name = "customer_asset"
    description = "List scoped customer assets through VAM backend APIs."
    required_scope = AssistantScope.CUSTOMER_ASSET_READ
    input_model = CustomerAssetInput
    input_schema = {
        "type": "object",
        "properties": {
            "page": {"type": "integer"},
            "count": {"type": "integer"},
            "search": {"type": "string"},
            "sortField": {"type": "string"},
            "orderBy": {"type": "string"},
            "equipmentId": {"type": "string"},
            "manufacturerId": {"type": "string"},
            "nonOnboardedManufacturerId": {"type": "string"},
            "purchaseDate": {"type": "string"},
            "dealerName": {"type": "string"},
            "isModelLinked": {"type": "boolean"},
            "manufacturerType": {"type": "string"},
        },
        "additionalProperties": False,
    }
    authorization_rules = {"customerContext": "token", "manufacturerScope": "validated"}
    manufacturer_scope = ManufacturerScopeRequirement.OPTIONAL

    def __init__(self, *, vam_client: VamClient | None = None) -> None:
        self._vam_client = vam_client or VamClient()

    async def execute(
        self,
        *,
        input_payload: dict[str, Any],
        auth_context: ToolAuthorizationContext,
        runtime_session: RuntimeSession,
    ) -> ToolExecutionResponse:
        started_at = perf_counter()
        logger.info(
            "tool.customer_asset.start",
            extra={
                "toolName": self.name,
                "runtimeSessionId": auth_context.runtime_session_id,
                "customerId": auth_context.customer_id,
            },
        )
        try:
            backend_payload = await self._vam_client.list_customer_assets(
                runtime_session,
                tool_name=self.name,
                page=input_payload.get("page"),
                count=input_payload.get("count"),
                search=input_payload.get("search"),
                sort_field=input_payload.get("sort_field"),
                order_by=input_payload.get("order_by"),
                equipment_id=input_payload.get("equipment_id"),
                manufacturer_id=input_payload.get("manufacturer_id"),
                non_onboarded_manufacturer_id=input_payload.get("non_onboarded_manufacturer_id"),
                purchase_date=input_payload.get("purchase_date"),
                dealer_name=input_payload.get("dealer_name"),
                is_model_linked=input_payload.get("is_model_linked"),
                manufacturer_type=input_payload.get("manufacturer_type"),
                correlation_id=auth_context.runtime_session_id,
            )
        except Exception:
            logger.exception(
                "tool.customer_asset.failed",
                extra={
                    "toolName": self.name,
                    "runtimeSessionId": auth_context.runtime_session_id,
                    "customerId": auth_context.customer_id,
                    "durationMs": self._elapsed_ms(started_at),
                },
            )
            raise

        result = self._asset_list_source(backend_payload)
        metadata = {"source": "vam_backend", "runtimeSessionId": auth_context.runtime_session_id}
        logger.info(
            "tool.customer_asset.completed",
            extra={
                "toolName": self.name,
                "runtimeSessionId": auth_context.runtime_session_id,
                "customerId": auth_context.customer_id,
                "durationMs": self._elapsed_ms(started_at),
            },
        )
        return self.format_output(result, metadata=metadata)

    @staticmethod
    def _asset_list_source(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "assets": payload.get("assets", []),
            "recordsTotal": payload.get("recordsTotal"),
            "recordsFiltered": payload.get("recordsFiltered"),
            "totalPages": payload.get("totalPages"),
            "number": payload.get("number"),
        }

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 2)
