from order_sms.order_message_approval import ApprovalRequest, register_approved_assets
from order_sms.sms_registry_client import SmsRegistryClient


def main() -> None:
    request = ApprovalRequest.model_validate(
        {
            "store_namespace": "north-clinic-shop",
            "revision": "2026-08-contract",
            "signature_name": "North Clinic Shop",
            "signature_content": "North Clinic Shop",
            "templates": [
                {
                    "stage": "checkout",
                    "content": "Order {{order_id}} checkout: {{checkout_status}}.",
                    "template_vars": ["order_id", "checkout_status"],
                },
                {
                    "stage": "fulfillment",
                    "content": "Order {{order_id}} shipped. Track {{tracking_code}}.",
                    "template_vars": ["order_id", "tracking_code"],
                },
                {
                    "stage": "receipt",
                    "content": "Receipt for {{order_id}}: {{amount}}.",
                    "template_vars": ["order_id", "amount"],
                },
                {
                    "stage": "order_update",
                    "content": "Order {{order_id}} is {{order_status}}.",
                    "template_vars": ["order_id", "order_status"],
                },
            ],
        }
    )
    result = register_approved_assets(request, SmsRegistryClient.from_env())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
